// Decimal form values deliberately remain strings. Financial conversions belong to the API.
const optional = value => value === '' || value == null ? null : value;
export const SCENARIOS = ['bear', 'base', 'bull'];
const scenario = () => ({ annual_per_share_growth: '', terminal_multiple: '', annual_cash_dividend: '', terminal_fx_base_per_local: '1', rationale: '', probability: '' });
export function emptyDraft(currency = '') {
  return {
    model: 'user_specified', context: { valuation_date: '', horizon_years: '', return_basis: '', money_basis: 'nominal', currency_basis: 'local', valuation_currency: currency, local_currency: currency, valuation_calendar: '', as_of: '', known_at: '', observation_ids: [], thesis_revision_id: null },
    annualized_return: '', cumulative_return: '', rationale: '', reference: '', lower_annualized: '', upper_annualized: '', confidence_statement: '',
    assumptions: { metric: 'eps', current_price: '', current_fundamental_per_share: '', annual_per_share_growth: '', terminal_multiple: '', annual_cash_dividend: '', spot_fx_base_per_local: '1', terminal_fx_base_per_local: '1', rationale: '', price_source: '', price_observed_at: '', buyback_treatment: 'included_in_per_share_growth', dividend_treatment: 'cash_held_without_reinvestment_terminal_fx' },
    scenarios: Object.fromEntries(SCENARIOS.map(name => [name, scenario()])), useProbabilities: false, probability_source: '', probability_type: 'user_assumption',
    required_annualized_return: '', benchmark: '', risk_free_rate: '', equity_risk_premium: '', assumption_source: '', sample: '',
  };
}
export function buildEvaluation(draft, securityId) {
  const context = { ...draft.context, security_id: securityId };
  const base = { model: draft.model, context };
  if (draft.model === 'user_specified') return { ...base, annualized_return: optional(draft.annualized_return), cumulative_return: optional(draft.cumulative_return), rationale: draft.rationale, reference: optional(draft.reference), uncertainty: { lower_annualized: optional(draft.lower_annualized), upper_annualized: optional(draft.upper_annualized), confidence_statement: optional(draft.confidence_statement) } };
  if (draft.model === 'scenario_set') return { ...base, scenarios: SCENARIOS.map(name => {
    const { probability, ...assumptions } = draft.scenarios[name];
    return { name, assumptions: { ...draft.assumptions, ...assumptions }, probability: draft.useProbabilities ? probability : null };
  }), probability_source: draft.useProbabilities ? draft.probability_source : null, probability_type: draft.useProbabilities ? draft.probability_type : null };
  if (draft.model === 'fundamental') return { ...base, assumptions: { ...draft.assumptions } };
  if (draft.model === 'reverse') return { ...base, assumptions: { ...draft.assumptions }, required_annualized_return: draft.required_annualized_return, solve_for: 'terminal_multiple' };
  let sample;
  try { sample = JSON.parse(draft.sample); } catch { throw new Error('Enter a valid return sample JSON object.'); }
  if (!sample || typeof sample !== 'object' || Array.isArray(sample)) throw new Error('Enter a valid return sample JSON object.');
  return draft.model === 'historical' ? { ...base, sample } : { ...base, sample, benchmark: draft.benchmark, risk_free_rate: draft.risk_free_rate, equity_risk_premium: draft.equity_risk_premium, assumption_source: draft.assumption_source, risk_free_convention: 'annual_effective', horizon_assumption: 'iid_annual_gross_mean' };
}

const ERRORS = { 401: 'Private workspace key was not accepted. Lock the workspace and unlock it with the correct key.', 404: 'The security or linked evidence is unavailable. Reload the selection.', 422: 'Check assumptions, positive horizon, return and currency conventions, evidence cutoffs, and sample alignment. Explicit probabilities must all be supplied and sum to one.', 503: 'The private research service is unavailable or not configured.' };
export async function valuationRequest(base, key, path, options = {}, fetcher = fetch) {
  let response;
  try { response = await fetcher(`${base.replace(/\/$/, '')}/api/research${path}`, { ...options, cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, ...(options.body ? { body: JSON.stringify(options.body) } : {}) }); }
  catch { throw new Error('The private research service could not be reached.'); }
  if (!response.ok) throw new Error(ERRORS[response.status] || 'The private research request failed.');
  try { return await response.json(); } catch { throw new Error('The private research response could not be read.'); }
}
const initial = () => ({ connected: false, busy: false, error: '', securities: [], securitiesMore: false, securityId: '', theses: [], thesesMore: false, thesisId: '', revisions: [], revisionsMore: false, evidence: [], evidenceMore: false, evidenceLoaded: false, draft: emptyDraft(), output: null });
export function createValuationWorkspace(request) {
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
    try { await action((path, options) => request(path, options, sessionKey), patch => { if (generation === token) update(patch); }); }
    catch (error) { if (generation === token) update({ error: error.message }); }
    finally { if (generation === token) update({ busy: false }); }
  }
  const workspace = {
    subscribe: listener => { listeners.add(listener); return () => listeners.delete(listener); },
    getSnapshot: () => state,
    disconnect() { ++generation; key = ''; state = initial(); listeners.forEach(listener => listener()); },
    connect(ownerKey) { workspace.disconnect(); key = ownerKey; return perform(async (call, apply) => { const securities = await call('/securities?limit=100&offset=0'); apply({ connected: true, securities, securitiesMore: securities.length === 100 }); }); },
    selectSecurity(securityId) {
      const currency = state.securities.find(item => item.id === securityId)?.currency || '';
      invalidate({ securityId, theses: [], thesesMore: false, thesisId: '', revisions: [], revisionsMore: false, evidence: [], evidenceMore: false, evidenceLoaded: false, draft: emptyDraft(currency) });
      return perform(async (call, apply) => { const theses = securityId ? await call(`/theses?security_id=${encodeURIComponent(securityId)}&limit=100&offset=0`) : []; apply({ theses, thesesMore: theses.length === 100 }); });
    },
    selectThesis(thesisId) {
      invalidate({ thesisId, revisions: [], revisionsMore: false, draft: { ...state.draft, context: { ...state.draft.context, thesis_revision_id: null } } });
      return perform(async (call, apply) => { const revisions = thesisId ? await call(`/theses/${encodeURIComponent(thesisId)}/revisions?limit=100&offset=0`) : []; apply({ revisions, revisionsMore: revisions.length === 100 }); });
    },
    edit(field, value) { invalidate({ draft: { ...state.draft, [field]: value } }); },
    editContext(field, value) {
      const clearEvidence = ['as_of', 'known_at'].includes(field);
      const context = { ...state.draft.context, ...(clearEvidence ? { observation_ids: [] } : {}), [field]: value };
      const changedCurrency = ['valuation_currency', 'local_currency'].includes(field) && value !== state.draft.context[field];
      const resetFx = changedCurrency && context.valuation_currency !== context.local_currency;
      invalidate({ draft: { ...state.draft, context, ...(resetFx ? { assumptions: { ...state.draft.assumptions, spot_fx_base_per_local: '', terminal_fx_base_per_local: '' }, scenarios: Object.fromEntries(SCENARIOS.map(name => [name, { ...state.draft.scenarios[name], terminal_fx_base_per_local: '' }])) } : {}) }, ...(clearEvidence ? { evidence: [], evidenceLoaded: false, evidenceMore: false } : {}) });
    },
    editAssumption(field, value) { invalidate({ draft: { ...state.draft, assumptions: { ...state.draft.assumptions, [field]: value } } }); },
    editScenario(name, field, value) { invalidate({ draft: { ...state.draft, scenarios: { ...state.draft.scenarios, [name]: { ...state.draft.scenarios[name], [field]: value } } } }); },
    toggleEvidence(id) { const ids = state.draft.context.observation_ids; workspace.editContext('observation_ids', ids.includes(id) ? ids.filter(item => item !== id) : [...ids, id]); },
    loadEvidence() {
      const { securityId, draft } = state;
      invalidate({ evidence: [], evidenceLoaded: false, evidenceMore: false, draft: { ...draft, context: { ...draft.context, observation_ids: [] } } });
      return perform(async (call, apply) => { const page = await call(`/securities/${encodeURIComponent(securityId)}/fundamentals?as_of=${encodeURIComponent(draft.context.as_of)}&known_at=${encodeURIComponent(draft.context.known_at)}&limit=100&offset=0`); apply({ evidence: page.items, evidenceLoaded: true, evidenceMore: page.items.length === 100 }); });
    },
    loadMore(kind) {
      const items = state[kind];
      const path = kind === 'securities' ? '/securities?' : kind === 'theses' ? `/theses?security_id=${encodeURIComponent(state.securityId)}&` : kind === 'revisions' ? `/theses/${encodeURIComponent(state.thesisId)}/revisions?` : `/securities/${encodeURIComponent(state.securityId)}/fundamentals?as_of=${encodeURIComponent(state.draft.context.as_of)}&known_at=${encodeURIComponent(state.draft.context.known_at)}&`;
      return perform(async (call, apply) => { const response = await call(`${path}limit=100&offset=${items.length}`); const more = kind === 'evidence' ? response.items : response; const seen = new Set(items.map(item => item.id)); apply({ [kind]: [...items, ...more.filter(item => !seen.has(item.id))], [`${kind}More`]: more.length === 100 }); });
    },
    evaluate() {
      update({ output: null });
      const { draft, securityId } = state;
      return perform(async (call, apply) => { const body = buildEvaluation(draft, securityId); const output = await call('/valuation/evaluate', { method: 'POST', body }); apply({ output }); });
    },
  };
  return workspace;
}
