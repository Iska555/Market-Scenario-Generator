const blankDraft = () => ({ start: '', end: '', known_at: new Date().toISOString(), risk_free_rate: '0', confidence: '0.95', max_mark_age_days: '3' });
const initial = () => ({ connected: false, busy: '', error: '', portfolios: [], selectedId: '', ledger: null, draft: blankDraft(), evidence: '', report: null });
const errors = {
  401: 'Private workspace key was not accepted. Lock and unlock the private workspace.',
  404: 'The selected account is no longer available. Reload accounts.',
  409: 'The ledger changed. Reload the account and review its evidence before calculating again.',
  422: 'Check the selected dates, knowledge cutoff and supplied evidence. Prices and FX need valid sources, timestamps, currencies and exact decimals.',
  503: 'The private performance service is unavailable or not configured.',
};
const message = error => errors[error.status] || 'The private performance request failed. Check the service and retry.';

export async function performanceRequest(base, key, id, body, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/performance/portfolios/${encodeURIComponent(id)}/report`, {
      method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, body: JSON.stringify(body),
    });
  } catch { throw new Error('The private performance service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error(errors[response.status] || 'The private performance request failed.'), { status: response.status });
  return response.json();
}

function datesInWindow(draft) {
  const canonical = value => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  if (!canonical(draft.start) || !canonical(draft.end)) throw new Error('Choose valid opening and closing dates.');
  const days = (Date.parse(draft.end) - Date.parse(draft.start)) / 86400000;
  if (days < 1 || days > 3660) throw new Error('Choose at least two consecutive valuation dates, up to 3661 dates.');
  return Array.from({ length: days + 1 }, (_, index) => new Date(Date.parse(draft.start) + index * 86400000).toISOString().slice(0, 10));
}
function validateCutoff(value) {
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error('Knowledge cutoff needs an ISO timestamp with a UTC offset.');
}

export function evidenceTemplate(draft, transactions, activeIds) {
  const dates = datesInWindow(draft);
  validateCutoff(draft.known_at);
  const opening = Date.parse(`${draft.start}T23:59:59.999Z`);
  const end = Date.parse(`${draft.end}T23:59:59.999Z`);
  const active = new Set(activeIds);
  return {
    daily_marks: dates.map(date => ({ date, prices: [], fx: [] })),
    flow_marks: transactions.filter(row => active.has(row.id) && ['DEPOSIT', 'WITHDRAWAL'].includes(row.type) && Date.parse(row.effective_at) > opening && Date.parse(row.effective_at) <= end && Date.parse(row.recorded_at) <= Date.parse(draft.known_at))
      .sort((a, b) => Date.parse(a.effective_at) - Date.parse(b.effective_at) || a.sequence - b.sequence)
      .map(row => ({ transaction_id: row.id, prices: [], fx: [] })),
  };
}

export function buildPerformanceRequest(draft, text, version) {
  const dates = datesInWindow(draft);
  validateCutoff(draft.known_at);
  let evidence;
  try { evidence = JSON.parse(text); } catch { throw new Error('Import or paste valid valuation evidence JSON.'); }
  if (!evidence || !Array.isArray(evidence.daily_marks) || !Array.isArray(evidence.flow_marks)) throw new Error('Evidence needs daily_marks and flow_marks arrays.');
  if (evidence.daily_marks.length !== dates.length || evidence.daily_marks.some((row, index) => row?.date !== dates[index])) throw new Error('Daily evidence dates must match every consecutive date in the selected window.');
  for (const row of [...evidence.daily_marks, ...evidence.flow_marks]) {
    if (!row || !Array.isArray(row.prices) || !Array.isArray(row.fx)) throw new Error('Each valuation needs prices and fx arrays, even when empty.');
    for (const [items, field] of [[row.prices, 'price'], [row.fx, 'rate']]) for (const item of items) {
      if (!item || typeof item[field] !== 'string') throw new Error('Prices and FX rates must be exact decimal strings, never JSON numbers.');
      if (typeof item.source !== 'string' || !item.source.trim() || typeof item.currency !== 'string' || !item.currency || typeof item.observed_at !== 'string' || !item.observed_at) throw new Error('Every price and FX quote needs a source, currency and observed timestamp.');
      validateCutoff(item.observed_at);
    }
  }
  const riskFree = Number(draft.risk_free_rate), confidence = Number(draft.confidence), age = Number(draft.max_mark_age_days);
  if (!draft.risk_free_rate.trim() || !Number.isFinite(riskFree) || riskFree <= -1 || riskFree > 10 || !Number.isFinite(confidence) || confidence <= 0 || confidence >= 1 || !draft.max_mark_age_days.trim() || !Number.isInteger(age) || age < 0 || age > 30) throw new Error('Check the advanced settings: annual rate, confidence and maximum quote age.');
  return { expected_version: version, known_at: draft.known_at, daily_marks: evidence.daily_marks, flow_marks: evidence.flow_marks, risk_free_rate: riskFree, confidence, max_mark_age_days: age, calendar: 'UTC_calendar_daily', price_convention: 'unadjusted', periods_per_year: 365 };
}

export function createPerformance(accounting, reportRequest) {
  let state = initial(), key = '', generation = 0;
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const store = {
    getSnapshot: () => state,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    disconnect() { ++generation; key = ''; state = initial(); listeners.forEach(listener => listener()); },
    async connect(candidate) {
      store.disconnect(); key = candidate; const token = generation;
      update({ busy: 'accounts' });
      try {
        const portfolios = await accounting('/portfolios', {}, key);
        if (token !== generation) return;
        update({ connected: true, portfolios, busy: '' });
        if (portfolios.length) await store.select(portfolios[0].id);
      } catch (error) { if (token === generation) update({ busy: '', error: message(error) }); }
    },
    async select(id) {
      if (!state.connected || !state.portfolios.some(row => row.id === id)) return;
      const token = ++generation;
      update({ selectedId: id, ledger: null, evidence: '', report: null, draft: blankDraft(), error: '', busy: 'account' });
      try {
        const ledger = await accounting(`/portfolios/${encodeURIComponent(id)}/state`, {}, key);
        if (token === generation) update({ ledger, busy: '' });
      } catch (error) { if (token === generation) update({ busy: '', error: message(error) }); }
    },
    edit(patch) { if (!state.connected) return; ++generation; update({ draft: { ...state.draft, ...patch }, report: null, error: '', busy: '' }); },
    editEvidence(evidence) { if (!state.connected) return; ++generation; update({ evidence, report: null, error: '', busy: '' }); },
    async importEvidence(textPromise) {
      if (!state.connected) return;
      const token = ++generation;
      update({ evidence: '', report: null, error: '', busy: 'import' });
      try {
        const text = await textPromise;
        if (token === generation) update({ evidence: text, busy: '' });
      } catch { if (token === generation) update({ busy: '', error: 'The evidence file could not be read.' }); }
    },
    async makeTemplate() {
      if (!state.connected || !state.ledger) return;
      const token = ++generation, id = state.selectedId, sessionKey = key, draft = { ...state.draft }, version = state.ledger.version;
      update({ busy: 'template', report: null, evidence: '', error: '' });
      try {
        datesInWindow(draft); validateCutoff(draft.known_at);
        const query = new URLSearchParams({ as_of: `${draft.end}T23:59:59.999999Z`, known_at: draft.known_at });
        const snapshot = await accounting(`/portfolios/${encodeURIComponent(id)}/state?${query}`, {}, sessionKey);
        if (token !== generation) return;
        let transactions = [], total = 1;
        while (transactions.length < total) {
          const page = await accounting(`/portfolios/${encodeURIComponent(id)}/transactions?limit=100&offset=${transactions.length}`, {}, sessionKey);
          if (token !== generation) return;
          if (page.version !== version) throw Object.assign(new Error(), { status: 409 });
          total = page.total;
          if (!page.transactions.length && transactions.length < total) throw new Error('Incomplete history');
          transactions = transactions.concat(page.transactions);
        }
        if (token === generation) update({ evidence: JSON.stringify(evidenceTemplate(draft, transactions, snapshot.active_transaction_ids), null, 2), busy: '' });
      } catch (error) { if (token === generation) update({ busy: '', error: error.status ? message(error) : 'Could not prepare evidence. Check dates and knowledge cutoff, then reload the account and retry.' }); }
    },
    async run() {
      if (!state.connected || !state.ledger) return;
      const token = ++generation;
      update({ report: null, error: '', busy: 'report' });
      let body;
      try { body = buildPerformanceRequest(state.draft, state.evidence, state.ledger.version); }
      catch (error) { update({ error: error.message, busy: '' }); return; }
      try {
        const report = await reportRequest(state.selectedId, body, key);
        if (token === generation) update({ report, busy: '' });
      } catch (error) { if (token === generation) update({ error: message(error), busy: '' }); }
    },
  };
  return store;
}
