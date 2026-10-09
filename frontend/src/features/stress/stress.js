// Request serialization only: portfolio calculations and validations belong to the backend.
export const emptyStress = () => ({ method: 'historical_replay', scenario_name: '', rationale: '', assets: [], currency: '', valuation_date: '', valuation_calendar: '', as_of: '', known_at: '', initial_value: '', rebalance: 'buy_and_hold', risk_free_rate: '', history: '', horizon_periods: '', path_count: '', block_length: '', seed: '', confidence: '', acceptEmpirical: false, shock_horizon_label: '' });
const integer = (value, name) => {
  if (!/^\d+$/.test(String(value))) throw new Error(`Enter an explicit whole number for ${name}.`);
  const result = Number(value);
  if (!Number.isSafeInteger(result)) throw new Error(`Enter a bounded whole number for ${name}.`);
  return result;
};
export function buildStress(draft) {
  const body = Object.fromEntries(['method', 'scenario_name', 'rationale', 'currency', 'valuation_date', 'valuation_calendar', 'as_of', 'known_at', 'initial_value'].map(name => [name, draft[name]]));
  body.assets = draft.assets.map(({ security_id, weight }) => ({ security_id, weight }));
  if (draft.method === 'deterministic_shock') return { ...body, shocks: draft.assets.map(asset => asset.shock), shock_horizon_label: draft.shock_horizon_label };
  let history;
  try { history = JSON.parse(draft.history); } catch { throw new Error('Enter the supplied joint history as a JSON object.'); }
  if (!history || Array.isArray(history) || typeof history !== 'object') throw new Error('Enter the supplied joint history as a JSON object.');
  Object.assign(body, { history, rebalance: draft.rebalance, risk_free_rate: draft.risk_free_rate });
  if (draft.method === 'block_bootstrap') {
    if (!draft.acceptEmpirical) throw new Error('Explicitly accept resampling the empirical returns without adopting their mean as expected return.');
    Object.assign(body, Object.fromEntries(['horizon_periods', 'path_count', 'block_length', 'seed'].map(name => [name, integer(draft[name], name)])), { confidence: draft.confidence, mean_policy: 'resample_observed_returns_not_expected_return' });
  }
  return body;
}
const initial = () => ({ connected: false, busy: false, error: '', securities: [], more: false, draft: emptyStress(), output: null });
export function createStressWorkspace(request) {
  let state = initial();
  let key = '';
  let generation = 0;
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const invalidate = patch => { ++generation; update({ output: null, busy: false, error: '', ...patch }); };
  async function perform(action) {
    const token = ++generation;
    const sessionKey = key;
    update({ busy: true, error: '' });
    try { await action((path, options) => request(path, options, sessionKey), patch => { if (token === generation) update(patch); }); }
    catch (error) { if (token === generation) update({ error: error.message }); }
    finally { if (token === generation) update({ busy: false }); }
  }
  const workspace = {
    subscribe: listener => { listeners.add(listener); return () => listeners.delete(listener); },
    getSnapshot: () => state,
    disconnect() { ++generation; key = ''; state = initial(); listeners.forEach(listener => listener()); },
    connect(ownerKey) { workspace.disconnect(); key = ownerKey; return perform(async (call, apply) => { const securities = await call('/securities?limit=100&offset=0'); apply({ connected: true, securities, more: securities.length === 100 }); }); },
    loadMore() { const rows = state.securities; return perform(async (call, apply) => { const page = await call(`/securities?limit=100&offset=${rows.length}`); const seen = new Set(rows.map(row => row.id)); apply({ securities: [...rows, ...page.filter(row => !seen.has(row.id))], more: page.length === 100 }); }); },
    edit(name, value) { invalidate({ draft: { ...state.draft, [name]: value } }); },
    editAsset(id, name, value) { invalidate({ draft: { ...state.draft, assets: state.draft.assets.map(asset => asset.security_id === id ? { ...asset, [name]: value } : asset) } }); },
    toggleSecurity(id) {
      const assets = state.draft.assets;
      const selected = assets.some(asset => asset.security_id === id);
      const currency = state.securities.find(security => security.id === id)?.currency || '';
      invalidate({ draft: { ...state.draft, currency: assets.length === 0 ? currency : state.draft.currency, assets: selected ? assets.filter(asset => asset.security_id !== id) : [...assets, { security_id: id, weight: '', shock: '' }] } });
    },
    evaluate() { update({ output: null }); const draft = state.draft; return perform(async (call, apply) => { const body = buildStress(draft); apply({ output: await call('/stress/evaluate', { method: 'POST', body }) }); }); },
  };
  return workspace;
}
