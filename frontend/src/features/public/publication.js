import { DEMO_LABEL } from './demo.js';

export async function publicationRequest(base, key, path, body, fetcher = fetch) {
  const response = await fetcher(`${base.replace(/\/$/, '')}/api/publication/${path}`, {
    method: body ? 'POST' : 'GET', cache: 'no-store',
    headers: { 'X-Research-Key': key, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) throw Object.assign(new Error(response.status === 409 ? 'Source or publication history changed. Reload and review a fresh preview.' : 'Publication request rejected. Check the demo and public reason before retrying.'), { status: response.status });
  return response.json();
}

export async function readPublished(base, version, signal, fetcher = fetch) {
  const path = version ? `/versions/${encodeURIComponent(version)}` : '';
  const response = await fetcher(`${base.replace(/\/$/, '')}/api/public/demo${path}`, { cache: 'no-store', signal });
  if (!response.ok) throw Object.assign(new Error(response.status === 410 ? 'This demonstration has been withdrawn from public availability.' : 'No published demonstration is available at this address.'), { status: response.status });
  const data = await response.json();
  if (data?.status !== 'published' || data?.snapshot?.mode !== 'demo' || data?.snapshot?.label !== DEMO_LABEL || data?.snapshot?.schema_version !== 'demo_snapshot_v1' || !data.published_at) throw new Error('Published demonstration identity could not be verified.');
  return data;
}

export async function readHistory(base, signal, fetcher = fetch) {
  const response = await fetcher(`${base.replace(/\/$/, '')}/api/public/demo/history`, { cache: 'no-store', signal });
  if (!response.ok) throw new Error('Publication history is unavailable.');
  return response.json();
}

export function createPublicationWorkspace(request, portfolioId, uuid = () => crypto.randomUUID()) {
  let key = '', generation = 0, captured = null;
  const listeners = new Set();
  let state = { connected: false, busy: false, error: '', preview: null, history: null, result: null, uncertain: false, selection: ['harbor', 'orchard'], reason: '' };
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(fn => fn()); };
  async function refresh(token) {
    const history = await request('history', null, key);
    if (token === generation) update({ history });
  }
  async function run(action) {
    if (!key || state.busy) return;
    const token = generation;
    if (!captured) {
      if (action === 'previews') captured = { action, body: { id: uuid(), portfolio_id: portfolioId, selected_research: [...state.selection] } };
      else if (action === 'publish' && state.preview && state.history) {
        const previous = [...state.history.events].reverse().find(event => event.action === 'publish');
        if (previous && !state.reason.trim()) { update({ error: 'A public reason is required for a new version.' }); return; }
        captured = { action, body: { id: uuid(), preview_id: state.preview.id, ...(previous ? { correction_of: previous.version, public_reason: state.reason.trim() } : {}) } };
      } else if (action === 'withdraw' && state.history && state.reason.trim()) captured = { action, body: { id: uuid(), expected_sequence: state.history.sequence, public_reason: state.reason.trim() } };
      else { update({ error: 'Review a preview or supply the required public reason first.' }); return; }
    }
    const intent = captured;
    update({ busy: true, error: '', uncertain: false });
    try {
      const result = await request(intent.action, intent.body, key);
      if (token !== generation) return;
      captured = null;
      update({ busy: false, result: intent.action === 'publish' ? result : null,
        preview: intent.action === 'previews' ? result : null, reason: '', uncertain: false });
      try { await refresh(token); } catch { if (token === generation) update({ error: 'Action accepted. Publication history reload failed; reload before the next action.' }); }
    } catch (error) {
      if (token !== generation) return;
      const uncertain = !error.status;
      if (!uncertain) captured = null;
      update({ busy: false, uncertain, error: uncertain ? 'Outcome uncertain. Retry sends the same captured action and identity.' : error.message,
        ...(error.status === 409 ? { preview: null } : {}) });
    }
  }
  const workspace = {
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }, getSnapshot: () => state,
    async connect(candidate) { workspace.disconnect(); key = candidate; const token = generation; update({ connected: true, busy: true }); try { await refresh(token); if (token === generation) update({ busy: false }); } catch { if (token === generation) update({ busy: false, error: 'Publication history is unavailable.' }); } },
    disconnect() { ++generation; key = ''; captured = null; update({ connected: false, busy: false, preview: null, history: null, result: null, uncertain: false, error: '', reason: '', selection: ['harbor', 'orchard'] }); },
    editSelection(selection) { if (state.busy || captured) return; update({ selection, preview: null, result: null }); },
    editReason(reason) { if (!state.busy && !captured) update({ reason }); },
    preview: () => run('previews'), publish: () => run('publish'), withdraw: () => run('withdraw'), retry: () => captured && run(captured.action),
    async reload() { if (!key || state.busy || captured) return; const token = generation; update({ preview: null, result: null, busy: true, error: '' }); try { await refresh(token); if (token === generation) update({ busy: false }); } catch { if (token === generation) update({ busy: false, error: 'Publication history is unavailable.' }); } },
  };
  return workspace;
}
