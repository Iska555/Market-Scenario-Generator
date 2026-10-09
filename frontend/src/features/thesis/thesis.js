export const NARRATIVES = ['variant_perception', 'business_quality', 'earnings_drivers', 'catalysts', 'risks', 'bear_case', 'base_case', 'bull_case', 'invalidation_conditions', 'notes'];
export const REVIEW_NARRATIVES = ['what_changed', 'what_was_correct', 'what_was_wrong', 'new_information', 'notes'];
export const DECISIONS = ['BUY_MORE', 'HOLD', 'REDUCE', 'EXIT', 'WATCH'];
export const label = field => field.replaceAll('_', ' ').replace(/^./, letter => letter.toUpperCase());
export const displayDecimal = value => String(value).includes('.') ? String(value).replace(/0+$/, '').replace(/\.$/, '') : String(value);
const blankFields = fields => Object.fromEntries(fields.map(field => [field, '']));
export const emptyThesis = (currency = '') => ({ status: '', conviction: '', horizon_months: '', valuation_currency: currency, target_low: '', target_high: '', required_return: '', ...blankFields(NARRATIVES) });
export const emptyReview = (currency = '') => ({ decision: '', thesis_still_valid: '', current_price: '', valuation_currency: currency, updated_expected_return: '', ...blankFields(REVIEW_NARRATIVES) });
const decimal = value => value === '' || value == null ? null : String(value).trim();
export function buildRevision(draft, expectedRevision) {
  if (!draft.status || !draft.conviction || !draft.horizon_months) throw new Error('Choose status, conviction and a positive horizon.');
  const result = { status: draft.status, conviction: draft.conviction, horizon_months: Number(draft.horizon_months), valuation_currency: draft.valuation_currency.trim().toUpperCase(), target_low: decimal(draft.target_low), target_high: decimal(draft.target_high), required_return: decimal(draft.required_return), ...Object.fromEntries(NARRATIVES.map(field => [field, draft[field] ?? ''])) };
  if (expectedRevision != null) result.expected_revision = expectedRevision;
  return result;
}
export function buildReview(draft, revisionId) {
  if (!DECISIONS.includes(draft.decision)) throw new Error('Choose a review decision explicitly.');
  if (!['true', 'false'].includes(draft.thesis_still_valid)) throw new Error('Answer whether the thesis is still valid.');
  return { revision_id: revisionId, decision: draft.decision, thesis_still_valid: draft.thesis_still_valid === 'true', valuation_currency: draft.valuation_currency.trim().toUpperCase(), current_price: decimal(draft.current_price), updated_expected_return: decimal(draft.updated_expected_return), ...Object.fromEntries(REVIEW_NARRATIVES.map(field => [field, draft[field] ?? ''])) };
}

const ERRORS = { 401: 'Private workspace key was not accepted. Lock the workspace and unlock it with the correct key.', 404: 'This record is unavailable. Reload the list.', 409: 'A newer revision or conflicting record exists. Your draft is preserved. Reload latest before editing again.', 422: 'Check required fields, positive horizon and prices, paired ordered targets, currency codes, and annual returns greater than −1. Active theses require every substantive narrative.', 503: 'The research service is unavailable or not configured. Try again later.' };
export async function researchRequest(base, key, path, options = {}, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/research${path}`, { ...options, cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, ...(options.body ? { body: JSON.stringify(options.body) } : {}) });
  } catch {
    throw new Error('Research service could not be reached. Your draft is preserved.');
  }
  // Never echo server/network error text: it can contain the owner key or private input.
  if (!response.ok) throw Object.assign(new Error(ERRORS[response.status] || 'Research request failed. Your draft is preserved.'), { status: response.status });
  return response.json();
}

const initial = () => ({ connected: false, busy: false, error: '', notice: '', securities: [], securitiesOffset: 0, securitiesMore: false, prompts: [], securityId: '', theses: [], thesesMore: false, thesisId: '', draft: null, dirty: false, expectedRevision: null, latest: null, revisions: [], revisionsMore: false, reviews: [], reviewsMore: false, viewed: null, review: emptyReview(), reviewDirty: false, conflict: false });
const editable = revision => Object.fromEntries(Object.keys(emptyThesis()).map(field => [field, revision[field] ?? '']));
export function createWorkspace(request) {
  let state = initial();
  let key = '';
  let generation = 0;
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const clearThesis = () => ({ thesisId: '', draft: null, dirty: false, expectedRevision: null, latest: null, revisions: [], revisionsMore: false, reviews: [], reviewsMore: false, viewed: null, review: emptyReview(), reviewDirty: false, conflict: false });
  async function perform(action) {
    const token = ++generation;
    const sessionKey = key;
    update({ busy: true, error: '', notice: '' });
    const current = () => token === generation;
    const call = (path, options) => request(path, options, sessionKey);
    try { await action(call, patch => { if (current()) update(patch); }, current); }
    catch (error) { if (current()) update({ error: error.message, conflict: error.status === 409 }); }
    finally { if (current()) update({ busy: false }); }
  }
  const workspace = {
    getSnapshot: () => state,
    subscribe: listener => { listeners.add(listener); return () => listeners.delete(listener); },
    disconnect() { ++generation; key = ''; state = initial(); listeners.forEach(listener => listener()); },
    connect(ownerKey) {
      workspace.disconnect(); key = ownerKey;
      return perform(async (call, apply) => {
        const [securities, prompts] = await Promise.all([call('/securities?limit=100&offset=0'), call('/theses/prompts')]);
        apply({ connected: true, securities, prompts, securitiesMore: securities.length === 100 });
      });
    },
    securityPage(offset) {
      update({ ...clearThesis(), securityId: '', theses: [], thesesMore: false });
      return perform(async (call, apply) => {
        const securities = await call(`/securities?limit=100&offset=${offset}`);
        apply({ securities, securitiesOffset: offset, securitiesMore: securities.length === 100 });
      });
    },
    selectSecurity(securityId) {
      update({ ...clearThesis(), securityId, theses: [], thesesMore: false });
      return perform(async (call, apply) => {
        const theses = securityId ? await call(`/theses?security_id=${encodeURIComponent(securityId)}&limit=100&offset=0`) : [];
        apply({ theses, thesesMore: theses.length === 100 });
      });
    },
    createSecurity(body) {
      return perform(async (call, apply) => {
        const security = await call('/securities', { method: 'POST', body });
        apply({ ...clearThesis(), securities: [security, ...state.securities.filter(item => item.id !== security.id)], securityId: security.id, theses: [], thesesMore: false, notice: 'Security saved. You can now create its thesis.' });
      });
    },
    selectThesis(thesisId) {
      update({ ...clearThesis(), thesisId });
      return workspace.reloadThesis();
    },
    reloadThesis() {
      const id = state.thesisId;
      const draft = state.draft;
      const review = state.review;
      return perform(async (call, apply) => {
        const [thesis, revisions, reviews] = await Promise.all([call(`/theses/${id}`), call(`/theses/${id}/revisions?limit=100&offset=0`), call(`/theses/${id}/reviews?limit=100&offset=0`)]);
        apply({ latest: thesis.latest, ...(state.draft === draft ? { draft: editable(thesis.latest), expectedRevision: thesis.latest.revision, dirty: false, conflict: false } : {}), revisions, revisionsMore: revisions.length === 100, reviews, reviewsMore: reviews.length === 100, ...(state.review === review ? { viewed: thesis.latest, review: emptyReview(thesis.latest.valuation_currency), reviewDirty: false } : {}) });
      });
    },
    newThesis() {
      ++generation;
      const currency = state.securities.find(item => item.id === state.securityId)?.currency || '';
      update({ ...clearThesis(), busy: false, draft: emptyThesis(currency), dirty: true, error: '', notice: '' });
    },
    editThesis(field, value) { update({ draft: { ...state.draft, [field]: value }, dirty: true }); },
    discardEdits() { update({ draft: state.latest ? editable(state.latest) : null, dirty: false, review: emptyReview(state.viewed?.valuation_currency), reviewDirty: false }); },
    viewRevision(revision) { update({ viewed: revision, review: emptyReview(revision.valuation_currency), reviewDirty: false }); },
    editReview(field, value) { update({ review: { ...state.review, [field]: value }, reviewDirty: true }); },
    saveThesis() {
      const draft = state.draft;
      const id = state.thesisId;
      const securityId = state.securityId;
      const expected = state.expectedRevision;
      return perform(async (call, apply) => {
        const body = buildRevision(draft, id ? expected : undefined);
        const result = await call(id ? `/theses/${id}/revisions` : '/theses', { method: 'POST', body: id ? body : { ...body, security_id: securityId } });
        const latest = id ? result : result.latest;
        const thesisId = id || result.id;
        const thesis = id ? { ...state.theses.find(item => item.id === id), id, security_id: securityId, latest } : result;
        // Edits made while a request is in flight must survive the response.
        const untouched = state.draft === draft;
        apply({ thesisId, latest, ...(untouched ? { draft: editable(latest), expectedRevision: latest.revision, dirty: false } : {}), revisions: [latest, ...state.revisions], theses: [thesis, ...state.theses.filter(item => item.id !== thesisId)], ...(!state.reviewDirty ? { viewed: latest, review: emptyReview(latest.valuation_currency), reviewDirty: false } : {}), conflict: false, notice: `Saved immutable revision ${latest.revision}.` });
      });
    },
    saveReview() {
      const draft = state.review;
      const revisionId = state.viewed.id;
      const thesisId = state.thesisId;
      return perform(async (call, apply) => {
        const review = await call(`/theses/${thesisId}/reviews`, { method: 'POST', body: buildReview(draft, revisionId) });
        apply({ reviews: [review, ...state.reviews], ...(state.review === draft ? { review: emptyReview(state.viewed.valuation_currency), reviewDirty: false } : {}), notice: 'Review saved for the selected revision. Thesis status is unchanged.' });
      });
    },
    loadMore(kind) {
      const items = state[kind];
      const path = kind === 'theses' ? `/theses?security_id=${encodeURIComponent(state.securityId)}` : `/theses/${state.thesisId}/${kind}?`;
      return perform(async (call, apply) => {
        const more = await call(`${path}${kind === 'theses' ? '&' : ''}limit=100&offset=${items.length}`);
        const seen = new Set(items.map(item => item.id));
        apply({ [kind]: [...items, ...more.filter(item => !seen.has(item.id))], [`${kind}More`]: more.length === 100 });
      });
    },
  };
  return workspace;
}
