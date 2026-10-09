export const STRATEGIES = { current: 'Hypothetical portfolio', equal_weight: 'Equal weight reference', minimum_variance: 'Minimum variance', maximum_sharpe: 'Maximum Sharpe', risk_parity: 'Equal risk contribution' };
export const emptyConstructionDraft = () => ({ valuation_date: '', currency: '', valuation_calendar: '', as_of: '', known_at: '', risk_free_rate: '', covariance_estimator: 'ledoit_wolf', min_position_weight: '0', max_position_weight: '1', history: '' });

export function buildConstructionRequest(draft, assets) {
  let history;
  try { history = JSON.parse(draft.history); } catch { throw new Error('Supply a valid joint history JSON object.'); }
  if (!history || !Array.isArray(history.security_ids) || history.security_ids.length !== assets.length || history.security_ids.some((id, index) => id !== assets[index].security_id)) throw new Error('History security_ids must exactly match the ordered selected security IDs. Returns are never silently reordered.');
  if (!assets.length) throw new Error('Select at least one registered security.');
  const selected = assets.map(asset => {
    if (!asset.current_weight.trim()) throw new Error('Supply each current weight as a decimal fraction.');
    if (asset.adopt_view && (!asset.annualized_return.trim() || !asset.rationale.trim())) throw new Error('Each adopted investor view requires an annual return and rationale.');
    return {
      security_id: asset.security_id, current_weight: asset.current_weight,
      investor_view: asset.adopt_view ? { model: 'user_specified', context: { security_id: asset.security_id, valuation_date: draft.valuation_date, horizon_years: 1, return_basis: 'total', money_basis: 'nominal', currency_basis: 'local', local_currency: draft.currency, valuation_currency: draft.currency, valuation_calendar: draft.valuation_calendar, as_of: draft.as_of, known_at: draft.known_at }, annualized_return: asset.annualized_return, rationale: asset.rationale } : null,
    };
  });
  return { assets: selected, history, valuation_date: draft.valuation_date, currency: draft.currency, valuation_calendar: draft.valuation_calendar, as_of: draft.as_of, known_at: draft.known_at, risk_free_rate: draft.risk_free_rate, risk_free_convention: 'annual_effective', covariance_estimator: draft.covariance_estimator, annualization_assumption: 'iid_period_covariance', constraints: { min_position_weight: draft.min_position_weight, max_position_weight: draft.max_position_weight, long_only: true }, strategies: Object.keys(STRATEGIES) };
}

const ERRORS = { 401: 'Private workspace key was not accepted. Lock the workspace and unlock it with the correct key.', 404: 'A selected security or linked evidence is unavailable.', 422: 'Check weights (sum to one), feasible bounds, ordered history IDs, aligned total returns, currency, dates and explicit one-year views.', 503: 'The private research service is unavailable or not configured.' };
export async function constructionRequest(base, key, path, options = {}, fetcher = fetch) {
  let response;
  try { response = await fetcher(`${base.replace(/\/$/, '')}/api/research${path}`, { ...options, cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, ...(options.body ? { body: JSON.stringify(options.body) } : {}) }); }
  catch { throw new Error('The private research service could not be reached.'); }
  if (!response.ok) throw new Error(ERRORS[response.status] || 'The private research request failed.');
  try { return await response.json(); } catch { throw new Error('The private research response could not be read.'); }
}

const initial = () => ({ connected: false, busy: false, error: '', securities: [], securitiesMore: false, assets: [], draft: emptyConstructionDraft(), output: null });
export function createConstructionWorkspace(request) {
  let state = initial();
  let key = '';
  let generation = 0;
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const invalidate = patch => { generation++; update({ output: null, error: '', busy: false, ...patch }); };
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
    disconnect() { generation++; key = ''; state = initial(); listeners.forEach(listener => listener()); },
    connect(ownerKey) { workspace.disconnect(); key = ownerKey; return perform(async (call, apply) => { const securities = await call('/securities?limit=100&offset=0'); apply({ connected: true, securities, securitiesMore: securities.length === 100 }); }); },
    loadMore() { const prior = state.securities; return perform(async (call, apply) => { const page = await call(`/securities?limit=100&offset=${prior.length}`); const seen = new Set(prior.map(item => item.id)); apply({ securities: [...prior, ...page.filter(item => !seen.has(item.id))], securitiesMore: page.length === 100 }); }); },
    toggleSecurity(id) {
      if (!state.securities.some(item => item.id === id)) return;
      const included = state.assets.some(asset => asset.security_id === id);
      if (!included && state.assets.length >= 30) return;
      const assets = included ? state.assets.filter(asset => asset.security_id !== id) : [...state.assets, { security_id: id, current_weight: '', adopt_view: false, annualized_return: '', rationale: '' }].sort((a, b) => a.security_id.localeCompare(b.security_id));
      invalidate({ assets });
    },
    edit(field, value) { invalidate({ draft: { ...state.draft, [field]: value }, ...(field === 'currency' && value !== state.draft.currency ? { assets: state.assets.map(asset => ({ ...asset, adopt_view: false })) } : {}) }); },
    editAsset(id, field, value) { invalidate({ assets: state.assets.map(asset => asset.security_id === id ? { ...asset, [field]: value } : asset) }); },
    evaluate() { update({ output: null }); const bodyDraft = state.draft; const assets = state.assets; return perform(async (call, apply) => { const body = buildConstructionRequest(bodyDraft, assets); const output = await call('/construction/evaluate', { method: 'POST', body }); apply({ output }); }); },
  };
  return workspace;
}
