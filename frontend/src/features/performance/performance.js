import { emptySource, sourceBody } from './sourceReview.js';
const blankDraft = () => ({ start: '', end: '', known_at: new Date().toISOString(), risk_free_rate: '0', confidence: '0.95', max_mark_age_days: '3', include_contribution: false, include_benchmark: false, include_factors: false });
const initial = () => ({ connected: false, busy: '', error: '', portfolios: [], selectedId: '', ledger: null, draft: blankDraft(), evidence: '', benchmarkEvidence: '', factorEvidence: '', report: null, contribution: null, comparison: null, regression: null, settings: null, settingIdentity: '', settingReason: '', settingPending: null, savedBenchmarkRevision: null, sourceDraft: emptySource(), sourceReview: null });
const errors = {
  401: 'Private workspace key was not accepted. Lock and unlock the private workspace.',
  404: 'The selected account is no longer available. Reload accounts.',
  409: 'The ledger changed. Reload the account and review its evidence before calculating again.',
  422: 'Check the selected dates, knowledge cutoff and supplied evidence. Prices and FX need valid sources, timestamps, currencies and exact decimals.',
  503: 'The private performance service is unavailable or not configured.',
};
const message = error => errors[error.status] || 'The private performance request failed. Check the service and retry.';

export async function performanceRequest(base, key, id, body, fetcher = fetch, contribution = false) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/${contribution ? 'attribution' : 'performance'}/portfolios/${encodeURIComponent(id)}/${contribution ? 'contribution' : 'report'}`, {
      method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, body: JSON.stringify(body),
    });
  } catch { throw new Error('The private performance service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error(errors[response.status] || 'The private performance request failed.'), { status: response.status });
  return response.json();
}

export async function benchmarkSettingsRequest(base, key, id, body = null, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/benchmark/portfolios/${encodeURIComponent(id)}/settings`, {
      method: body ? 'POST' : 'GET', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch { throw new Error('The private benchmark settings service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error(errors[response.status] || 'The private benchmark settings request failed.'), { status: response.status });
  return response.json();
}

export async function comparisonRequest(base, key, id, body, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/benchmark/portfolios/${encodeURIComponent(id)}/comparison`, {
      method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, body: JSON.stringify(body),
    });
  } catch { throw new Error('The private comparison service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error(errors[response.status] || 'The private comparison request failed.'), { status: response.status });
  return response.json();
}

export async function factorRequest(base, key, id, body, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/factors/portfolios/${encodeURIComponent(id)}/report`, {
      method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, body: JSON.stringify(body),
    });
  } catch { throw new Error('The private factor service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error(errors[response.status] || 'The private factor request failed.'), { status: response.status });
  return response.json();
}

export function buildFactorEvidence(draft, text) {
  let result;
  try { result = JSON.parse(text); } catch { throw new Error('Import or paste reviewed factor evidence JSON.'); }
  const identity = result?.identity;
  if (!identity || !Array.isArray(identity.factors) || !Array.isArray(result.rows)) throw new Error('Factor evidence needs identity, declared factors and rows.');
  for (const field of ['model_id', 'revision', 'name', 'provider', 'methodology_reference', 'currency', 'effective_from', 'effective_to', 'published_at', 'retrieved_at']) {
    if (typeof identity[field] !== 'string' || !identity[field].trim()) throw new Error('Review all factor model identity, currency and provenance fields.');
  }
  if (identity.units !== 'decimal_simple_return' || identity.risk_free_convention !== 'period_effective_return' || identity.calendar !== 'UTC_calendar_daily' || identity.periods_per_year !== 365 || identity.currency_policy !== 'already_in_portfolio_currency') throw new Error('Use reviewed daily decimal factor and period-effective risk-free returns in account currency.');
  const ids = identity.factors.map(row => row.factor_id), dates = datesInWindow(draft).slice(1), supplied = new Set();
  if (!ids.length || ids.length > 6 || new Set(ids).size !== ids.length || ids.includes('alpha') || ids.some(id => typeof id !== 'string' || !id.trim())) throw new Error('Declare one to six unique factors; alpha is reserved for the intercept.');
  for (const row of result.rows) {
    if (!row || !dates.includes(row.date) || supplied.has(row.date) || !row.factor_returns || typeof row.factor_returns !== 'object' || Array.isArray(row.factor_returns)) throw new Error('Factor rows need unique interval closing dates and factor_returns. Missing dates remain gaps.');
    supplied.add(row.date);
    for (const [id, value] of Object.entries(row.factor_returns)) if (!ids.includes(id) || (value !== null && (typeof value !== 'string' || !value.trim()))) throw new Error('Declared factor returns must be decimal strings or null.');
    if (row.risk_free_return !== null && (typeof row.risk_free_return !== 'string' || !row.risk_free_return.trim())) throw new Error('Period-effective risk-free returns must be decimal strings or null.');
  }
  return result;
}

export function factorTemplate(draft, currency) {
  return {
    identity: { model_id: '', revision: '', name: '', provider: '', methodology_reference: '', currency, currency_policy: 'already_in_portfolio_currency', calendar: 'UTC_calendar_daily', periods_per_year: 365, units: 'decimal_simple_return', risk_free_convention: 'period_effective_return', effective_from: draft.start, effective_to: draft.end, published_at: '', retrieved_at: '', factors: [] },
    rows: datesInWindow(draft).slice(1).map(date => ({ date, risk_free_return: null, factor_returns: {}, observed_at: '', published_at: '', retrieved_at: '', source: '' })),
  };
}

export function buildBenchmarkEvidence(draft, text) {
  let result;
  try { result = JSON.parse(text); } catch { throw new Error('Import or paste reviewed benchmark evidence JSON.'); }
  if (!result?.identity || !Array.isArray(result.levels)) throw new Error('Benchmark evidence needs identity and levels fields.');
  const identity = result.identity;
  for (const field of ['benchmark_id', 'revision', 'name', 'provider', 'methodology_reference', 'currency', 'return_basis', 'hedging', 'effective_from', 'effective_to', 'published_at', 'retrieved_at']) {
    if (typeof identity[field] !== 'string' || !identity[field].trim()) throw new Error('Review all benchmark identity, version, currency and provenance fields.');
  }
  if (!['gross_total_return', 'net_total_return'].includes(identity.return_basis) || identity.calendar !== 'UTC_calendar_daily' || identity.periods_per_year !== 365 || identity.currency_policy !== 'already_in_portfolio_currency') throw new Error('Use total-return levels in account currency on the declared UTC daily calendar, with 365 periods per year.');
  const dates = datesInWindow(draft), supplied = new Set();
  for (const row of result.levels) {
    if (!row || !dates.includes(row.date) || supplied.has(row.date)) throw new Error('Benchmark dates must be unique and belong to the selected window. Missing dates remain explicit gaps.');
    supplied.add(row.date);
    if (row.level !== null && (typeof row.level !== 'string' || !row.level.trim())) throw new Error('Benchmark levels must be exact decimal strings or null, never JSON numbers.');
  }
  return result;
}

export function benchmarkTemplate(draft, currency) {
  return {
    identity: { benchmark_id: '', revision: '', name: '', provider: '', methodology_reference: '', currency, return_basis: '', hedging: '', calendar: 'UTC_calendar_daily', periods_per_year: 365, currency_policy: 'already_in_portfolio_currency', effective_from: draft.start, effective_to: draft.end, published_at: '', retrieved_at: '' },
    max_level_age_days: 0,
    levels: datesInWindow(draft).map(date => ({ date, level: null, observed_at: '', published_at: '', retrieved_at: '', source: '' })),
  };
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

export function createPerformance(accounting, reportRequest, contributionRequest, comparisonRequest, factorRequest, settingsRequest, sourceRequest) {
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
      update({ selectedId: id, ledger: null, evidence: '', benchmarkEvidence: '', factorEvidence: '', report: null, contribution: null, comparison: null, regression: null, draft: blankDraft(), settings: null, settingIdentity: '', settingReason: '', settingPending: null, savedBenchmarkRevision: null, sourceDraft: emptySource(), sourceReview: null, error: '', busy: 'account' });
      try {
        const ledger = await accounting(`/portfolios/${encodeURIComponent(id)}/state`, {}, key);
        if (token !== generation) return;
        update({ ledger });
        const settings = settingsRequest ? await settingsRequest(id, null, key) : null;
        if (token === generation) update({ settings, busy: '' });
      } catch (error) { if (token === generation) update({ busy: '', error: message(error) }); }
    },
    editSetting(patch) {
      if (!state.connected) return;
      ++generation; update({ ...patch, settingPending: null, report: null, contribution: null, comparison: null, regression: null, error: '', busy: '' });
    },
    copyReportIdentity() {
      if (!state.connected) return;
      try { store.editSetting({ settingIdentity: JSON.stringify(buildBenchmarkEvidence(state.draft, state.benchmarkEvidence).identity, null, 2) }); }
      catch (error) { update({ error: error.message }); }
    },
    async reloadSettings() {
      if (!state.connected || !settingsRequest) return;
      const token = ++generation;
      update({ busy: 'settings', settings: null, settingPending: null, savedBenchmarkRevision: null, report: null, contribution: null, comparison: null, regression: null, error: '' });
      try {
        const settings = await settingsRequest(state.selectedId, null, key);
        if (token === generation) update({ settings, busy: '' });
      } catch (error) { if (token === generation) update({ busy: '', error: message(error) }); }
    },
    async saveSetting(clear = false) {
      if (!state.connected || !state.settings || !settingsRequest) return;
      const token = ++generation;
      update({ busy: 'settings', report: null, contribution: null, comparison: null, regression: null, error: '' });
      try {
        if (!state.settingReason.trim()) throw new Error('Explain why you are saving or clearing this benchmark.');
        let identity = null;
        if (!clear) {
          try { identity = JSON.parse(state.settingIdentity); } catch { throw new Error('Supply a reviewed benchmark identity JSON.'); }
          if (!identity || typeof identity !== 'object' || Array.isArray(identity)) throw new Error('Supply a reviewed benchmark identity JSON.');
        }
        const pending = state.settingPending;
        const body = pending && (pending.identity === null) === clear ? pending : { id: crypto.randomUUID(), expected_revision: state.settings.revision, identity, reason: state.settingReason.trim() };
        update({ settingPending: body });
        await settingsRequest(state.selectedId, body, key);
        if (token !== generation) return;
        const settings = await settingsRequest(state.selectedId, null, key);
        if (token === generation) update({ settings, settingPending: null, settingReason: '', benchmarkEvidence: '', savedBenchmarkRevision: null, busy: '' });
      } catch (error) { if (token === generation) update({ busy: '', error: error.status ? message(error) : error.message }); }
    },
    linkSavedBenchmark() {
      if (!state.connected || !state.settings?.latest?.identity) return;
      try {
        const evidence = buildBenchmarkEvidence(state.draft, state.benchmarkEvidence);
        const identity = state.settings.latest.identity;
        const keys = Object.keys(identity);
        if (Object.keys(evidence.identity).length !== keys.length || keys.some(key => evidence.identity[key] !== identity[key])) throw new Error('Reviewed evidence identity differs from the saved benchmark.');
        ++generation; update({ savedBenchmarkRevision: state.settings.latest.revision, report: null, contribution: null, comparison: null, regression: null, error: '', busy: '' });
      } catch (error) { update({ error: error.message }); }
    },
    useSavedBenchmark() {
      if (!state.connected || !state.settings?.latest?.identity) return;
      try {
        const template = benchmarkTemplate(state.draft, state.portfolios.find(row => row.id === state.selectedId)?.base_currency);
        const selection = state.settings.latest;
        if (selection.identity.effective_from > state.draft.start || selection.identity.effective_to < state.draft.end) throw new Error('Saved benchmark identity does not cover the selected period.');
        if (new Date(selection.recorded_at) > new Date(state.draft.known_at)) throw new Error('Saved benchmark setting was recorded after this knowledge cutoff.');
        template.identity = selection.identity;
        store.editBenchmark(JSON.stringify(template, null, 2));
        update({ savedBenchmarkRevision: selection.revision, draft: { ...state.draft, include_benchmark: true } });
      } catch (error) { update({ error: error.message }); }
    },
    edit(patch) { if (!state.connected) return; ++generation; update({ draft: { ...state.draft, ...patch }, sourceReview: null, report: null, contribution: null, comparison: null, regression: null, error: '', busy: '' }); },
    editEvidence(evidence) { if (!state.connected) return; ++generation; update({ evidence, report: null, contribution: null, comparison: null, regression: null, error: '', busy: '' }); },
    editBenchmark(benchmarkEvidence) { if (!state.connected) return; ++generation; update({ benchmarkEvidence, savedBenchmarkRevision: null, report: null, contribution: null, comparison: null, regression: null, error: '', busy: '' }); },
    editSource(patch) {
      if (!state.connected) return;
      ++generation; update({ sourceDraft: { ...state.sourceDraft, ...patch }, sourceReview: null, error: '', busy: '' });
    },
    async importSource(textPromise) {
      if (!state.connected) return;
      const token = ++generation;
      update({ sourceDraft: emptySource(), sourceReview: null, error: '', busy: 'source' });
      try { const csv = await textPromise; if (token === generation) update({ sourceDraft: { ...emptySource(), csv }, busy: '' }); }
      catch { if (token === generation) update({ busy: '', error: 'The source CSV could not be read. Use an unzipped file of at most 2 MB.' }); }
    },
    async reviewSource() {
      if (!state.connected || !state.ledger || !sourceRequest) return;
      const token = ++generation;
      update({ sourceReview: null, error: '', busy: 'source' });
      let body;
      try { body = sourceBody(state.sourceDraft, state.draft); }
      catch (error) { update({ busy: '', error: error.message }); return; }
      try {
        const result = await sourceRequest(state.selectedId, body, key);
        if (token === generation) update({ sourceReview: result, busy: '' });
      } catch (error) { if (token === generation) update({ busy: '', error: error.status === 422 ? 'Check source format, ordered dates, numeric values and provenance timestamps. Only the French developed five-factor daily CSV is supported.' : message(error) }); }
    },
    editFactors(factorEvidence) { if (!state.connected) return; ++generation; update({ factorEvidence, report: null, contribution: null, comparison: null, regression: null, error: '', busy: '' }); },
    async importFactors(textPromise) {
      if (!state.connected) return;
      const token = ++generation;
      update({ factorEvidence: '', report: null, contribution: null, comparison: null, regression: null, error: '', busy: 'import' });
      try {
        const text = await textPromise;
        if (token === generation) update({ factorEvidence: text, busy: '' });
      } catch { if (token === generation) update({ busy: '', error: 'The factor evidence file could not be read.' }); }
    },
    makeFactorTemplate() {
      if (!state.connected || !state.ledger) return;
      try {
        const currency = state.portfolios.find(row => row.id === state.selectedId)?.base_currency;
        store.editFactors(JSON.stringify(factorTemplate(state.draft, currency), null, 2));
      } catch { update({ error: 'Choose valid reporting dates before preparing factor evidence.' }); }
    },
    async importBenchmark(textPromise) {
      if (!state.connected) return;
      const token = ++generation;
      update({ savedBenchmarkRevision: null, benchmarkEvidence: '', factorEvidence: '', report: null, contribution: null, comparison: null, regression: null, error: '', busy: 'import' });
      try {
        const text = await textPromise;
        if (token === generation) update({ benchmarkEvidence: text, busy: '' });
      } catch { if (token === generation) update({ busy: '', error: 'The benchmark evidence file could not be read.' }); }
    },
    makeBenchmarkTemplate() {
      if (!state.connected || !state.ledger) return;
      try {
        const currency = state.portfolios.find(row => row.id === state.selectedId)?.base_currency;
        store.editBenchmark(JSON.stringify(benchmarkTemplate(state.draft, currency), null, 2));
      } catch { update({ error: 'Choose valid reporting dates before preparing benchmark evidence.' }); }
    },
    async importEvidence(textPromise) {
      if (!state.connected) return;
      const token = ++generation;
      update({ savedBenchmarkRevision: null, evidence: '', benchmarkEvidence: '', factorEvidence: '', report: null, contribution: null, comparison: null, regression: null, error: '', busy: 'import' });
      try {
        const text = await textPromise;
        if (token === generation) update({ evidence: text, busy: '' });
      } catch { if (token === generation) update({ busy: '', error: 'The evidence file could not be read.' }); }
    },
    async makeTemplate() {
      if (!state.connected || !state.ledger) return;
      const token = ++generation, id = state.selectedId, sessionKey = key, draft = { ...state.draft }, version = state.ledger.version;
      update({ busy: 'template', report: null, contribution: null, comparison: null, regression: null, evidence: '', error: '' });
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
      update({ report: null, contribution: null, comparison: null, regression: null, error: '', busy: 'report' });
      let body;
      try { body = buildPerformanceRequest(state.draft, state.evidence, state.ledger.version); }
      catch (error) { update({ error: error.message, busy: '' }); return; }
      try {
        const withContribution = state.draft.include_contribution, withBenchmark = state.draft.include_benchmark;
        if (state.draft.include_factors) {
          let factors, benchmark = null;
          try {
            factors = buildFactorEvidence(state.draft, state.factorEvidence);
            if (withBenchmark) benchmark = buildBenchmarkEvidence(state.draft, state.benchmarkEvidence);
          } catch (error) { if (token === generation) update({ error: error.message, busy: '' }); return; }
          if (!factorRequest) throw new Error('Factor service unavailable');
          const result = await factorRequest(state.selectedId, { performance: body, factors, include_contribution: withContribution, benchmark, ...(withBenchmark && state.savedBenchmarkRevision ? { saved_benchmark_revision: state.savedBenchmarkRevision } : {}) }, key);
          if (token === generation) update({ report: result.performance, contribution: result.contribution, comparison: result.comparison, regression: result, busy: '' });
        } else if (withBenchmark) {
          let benchmark;
          try { benchmark = buildBenchmarkEvidence(state.draft, state.benchmarkEvidence); }
          catch (error) { if (token === generation) update({ error: error.message, busy: '' }); return; }
          if (!comparisonRequest) throw new Error('Comparison service unavailable');
          const result = await comparisonRequest(state.selectedId, { performance: body, benchmark, include_contribution: withContribution, ...(state.savedBenchmarkRevision ? { saved_benchmark_revision: state.savedBenchmarkRevision } : {}) }, key);
          if (token === generation) update({ report: result.performance, contribution: result.contribution, comparison: result, busy: '' });
        } else {
          if (withContribution && !contributionRequest) throw new Error('Contribution service unavailable');
          const result = await (withContribution ? contributionRequest : reportRequest)(state.selectedId, body, key);
          if (token === generation) update({ report: withContribution ? result.performance : result, contribution: withContribution ? result : null, busy: '' });
        }
      } catch (error) { if (token === generation) update({ error: message(error), busy: '' }); }
    },
  };
  return store;
}
