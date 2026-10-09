export const TRANSACTION_TYPES = ['BUY', 'SELL', 'DIVIDEND', 'FEE', 'DEPOSIT', 'WITHDRAWAL', 'FX_CONVERSION', 'REVERSAL'];

export const emptyManualDraft = () => ({
  type: 'BUY',
  effective_at: '',
  currency: 'GBP',
  security_id: '',
  quantity: '',
  price: '',
  amount: '',
  fees: '0',
  to_currency: '',
  to_amount: '',
  fx_rate: '',
  reverses_id: '',
  source: 'manual',
  external_reference: '',
  note: '',
});

export const emptyPortfolioDraft = () => ({
  id: '',
  name: 'Lightyear ISA',
  base_currency: 'GBP',
  broker: 'Lightyear',
  account_label: 'Stocks & Shares ISA',
});

export const emptyImportDraft = () => ({ csv_text: '', source: 'lightyear_reviewed' });
export const emptyValuationDraft = () => ({ as_of: '', known_at: '', prices_text: '[]', fx_text: '[]' });

export const correctionFields = row => ({
  reverses_id: row.id,
  effective_at: row.effective_at,
  currency: row.currency,
});

const commonFields = draft => ({
  type: draft.type,
  effective_at: draft.effective_at,
  currency: draft.currency,
  fees: draft.fees || '0',
  source: draft.source,
  external_reference: draft.external_reference,
  note: draft.note || '',
});

export function buildManualTransaction(draft) {
  const row = commonFields(draft);
  if (draft.type === 'BUY' || draft.type === 'SELL') {
    return { ...row, security_id: draft.security_id, quantity: draft.quantity, price: draft.price };
  }
  if (draft.type === 'DIVIDEND') return { ...row, security_id: draft.security_id, amount: draft.amount };
  if (draft.type === 'FX_CONVERSION') {
    return { ...row, amount: draft.amount, to_currency: draft.to_currency, to_amount: draft.to_amount, fx_rate: draft.fx_rate };
  }
  if (draft.type === 'REVERSAL') return { ...row, reverses_id: draft.reverses_id };
  return { ...row, amount: draft.amount };
}

const ERRORS = {
  401: 'Private workspace key was not accepted. Lock the workspace and unlock it with the correct key.',
  404: 'The selected portfolio, security or transaction is unavailable.',
  409: 'The portfolio changed or a source/reference conflicts with different content. Refresh before continuing.',
  422: 'Check the accounting fields, exact decimals, currencies, timestamps and available cash or holdings.',
  503: 'The private accounting service is unavailable or not configured.',
};

export async function accountingRequest(base, key, path, options = {}, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/accounting${path}`, {
      ...options,
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Research-Key': key },
      ...(options.body ? { body: JSON.stringify(options.body) } : {}),
    });
  } catch {
    const error = new Error('The private accounting service could not be reached.');
    error.uncertain = true;
    throw error;
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const line = path.endsWith('/imports/preview') && response.status === 422 && typeof detail.detail === 'string'
      ? /^CSV line (\d+):/.exec(detail.detail)?.[1]
      : null;
    const error = new Error(line ? `Canonical CSV line ${line} is invalid or unsupported.` : ERRORS[response.status] || 'The private accounting request failed.');
    error.status = response.status;
    throw error;
  }
  try { return await response.json(); }
  catch {
    const error = new Error('The private accounting response could not be read.');
    error.uncertain = true;
    throw error;
  }
}

const initial = () => ({
  connected: false,
  busy: '',
  error: '',
  portfolios: [],
  selectedPortfolioId: '',
  history: { transactions: [], version: 0, total: 0 },
  ledgerState: null,
  manual: emptyManualDraft(),
  portfolioDraft: emptyPortfolioDraft(),
  importDraft: emptyImportDraft(),
  valuationDraft: emptyValuationDraft(),
  preview: null,
  capturedRequest: null,
  canSavePreview: false,
  saveStatus: '',
  valuationResult: null,
});

const cloned = value => typeof structuredClone === 'function' ? structuredClone(value) : JSON.parse(JSON.stringify(value));

export function createLedgerWorkspace(request) {
  let state = initial();
  let key = '';
  let sessionGeneration = 0;
  let accountGeneration = 0;
  let draftGeneration = 0;
  let historyGeneration = 0;
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const currentPortfolio = () => state.portfolios.find(item => item.id === state.selectedPortfolioId);
  const isCurrent = (session, account, draft = draftGeneration) => session === sessionGeneration && account === accountGeneration && draft === draftGeneration;
  const clearPreview = patch => {
    draftGeneration += 1;
    update({ preview: null, capturedRequest: null, canSavePreview: false, saveStatus: '', error: '',
      ...(['preview', 'valuation'].includes(state.busy) ? { busy: '' } : {}), ...patch });
  };

  async function loadPortfolio(id) {
    const session = sessionGeneration;
    const account = ++accountGeneration;
    historyGeneration += 1;
    const changed = id !== state.selectedPortfolioId;
    draftGeneration += 1;
    update({ selectedPortfolioId: id, busy: 'account', error: '', history: { transactions: [], version: 0, total: 0 }, ledgerState: null, preview: null, capturedRequest: null, canSavePreview: false, saveStatus: '', valuationResult: null,
      ...(changed ? { manual: emptyManualDraft(), importDraft: emptyImportDraft(), valuationDraft: emptyValuationDraft() } : {}) });
    try {
      const [history, ledgerState] = await Promise.all([
        request(`/portfolios/${id}/transactions?limit=100&offset=0`, {}, key),
        request(`/portfolios/${id}/state`, {}, key),
      ]);
      if (isCurrent(session, account)) {
        if (history.version !== ledgerState.version) {
          update({ error: 'The ledger changed while loading. Refresh to obtain one coherent state and history.' });
        } else {
          update({ history, ledgerState });
        }
      }
    } catch {
      if (isCurrent(session, account)) update({ error: 'The selected portfolio could not be loaded.' });
    } finally {
      if (isCurrent(session, account)) update({ busy: '' });
    }
  }

  const workspace = {
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    getSnapshot: () => state,
    disconnect() {
      sessionGeneration += 1;
      accountGeneration += 1;
      draftGeneration += 1;
      historyGeneration += 1;
      key = '';
      state = initial();
      listeners.forEach(listener => listener());
    },
    async connect(ownerKey) {
      workspace.disconnect();
      key = ownerKey;
      const session = sessionGeneration;
      update({ busy: 'connect', error: '' });
      try {
        const portfolios = await request('/portfolios', {}, key);
        if (session !== sessionGeneration) return;
        update({ connected: true, portfolios, busy: '' });
        if (portfolios.length) await loadPortfolio(portfolios[0].id);
      } catch {
        if (session === sessionGeneration) update({ busy: '', error: 'The private accounting service could not be connected.' });
      }
    },
    selectPortfolio(id) {
      if (!state.connected || !state.portfolios.some(item => item.id === id)) return Promise.resolve();
      return loadPortfolio(id);
    },
    refresh() {
      return state.selectedPortfolioId ? loadPortfolio(state.selectedPortfolioId) : Promise.resolve();
    },
    async loadMoreHistory() {
      const portfolio = currentPortfolio();
      if (!portfolio || state.busy || state.history.transactions.length >= state.history.total) return;
      const session = sessionGeneration;
      const account = accountGeneration;
      const draft = draftGeneration;
      const history = historyGeneration;
      const offset = state.history.transactions.length;
      const version = state.history.version;
      update({ busy: 'history', error: '' });
      try {
        const page = await request(`/portfolios/${portfolio.id}/transactions?limit=100&offset=${offset}`, {}, key);
        if (!isCurrent(session, account, draft) || history !== historyGeneration) return;
        if (page.version !== version) {
          update({ error: 'The ledger changed while loading history. Refresh before continuing.' });
          return;
        }
        const byId = new Map(state.history.transactions.map(row => [row.id, row]));
        page.transactions.forEach(row => byId.set(row.id, row));
        update({ history: { transactions: [...byId.values()].sort((left, right) => right.sequence - left.sequence), version, total: page.total } });
      } catch {
        if (isCurrent(session, account, draft) && history === historyGeneration) update({ error: 'Older transaction history could not be loaded.' });
      } finally {
        if (session === sessionGeneration && account === accountGeneration && history === historyGeneration && state.busy === 'history') update({ busy: '' });
      }
    },
    editPortfolio(patch) {
      if (state.busy === 'save') return;
      clearPreview({ portfolioDraft: { ...state.portfolioDraft, ...patch } });
    },
    async createPortfolio() {
      if (!state.connected || state.busy) return;
      const session = sessionGeneration;
      const account = accountGeneration;
      const draftGenerationAtSubmit = draftGeneration;
      const draft = cloned(state.portfolioDraft);
      update({ busy: 'create', error: '' });
      try {
        const created = await request('/portfolios', { method: 'POST', body: draft }, key);
        if (!isCurrent(session, account, draftGenerationAtSubmit)) return;
        const portfolios = state.portfolios.some(item => item.id === created.id) ? state.portfolios : [...state.portfolios, created];
        update({ portfolios, portfolioDraft: emptyPortfolioDraft(), busy: '' });
        await loadPortfolio(created.id);
      } catch {
        if (isCurrent(session, account, draftGenerationAtSubmit)) update({ busy: '', error: 'Portfolio creation was not confirmed. If retrying, keep the same UUID and account fields; the server may already have created it.' });
      } finally {
        if (session === sessionGeneration && account === accountGeneration && state.busy === 'create') update({ busy: '' });
      }
    },
    editManual(patch) {
      if (state.busy === 'save') return;
      clearPreview({ manual: { ...state.manual, ...patch } });
    },
    editImport(patch) {
      if (state.busy === 'save') return;
      clearPreview({ importDraft: { ...state.importDraft, ...patch } });
    },
    editValuation(patch) {
      if (state.busy === 'save') return;
      clearPreview({ valuationDraft: { ...state.valuationDraft, ...patch }, valuationResult: null });
    },
    async previewManual() {
      const portfolio = currentPortfolio();
      if (!portfolio || state.busy) return;
      const body = { expected_version: state.history.version, transactions: [buildManualTransaction(state.manual)] };
      const session = sessionGeneration;
      const account = accountGeneration;
      const draft = draftGeneration;
      update({ busy: 'preview', error: '', preview: null, capturedRequest: null, canSavePreview: false, saveStatus: '' });
      try {
        const preview = await request(`/portfolios/${portfolio.id}/transactions/preview`, { method: 'POST', body }, key);
        if (isCurrent(session, account, draft)) update({ preview, capturedRequest: cloned(body), canSavePreview: true });
      } catch {
        if (isCurrent(session, account, draft)) update({ error: 'The transaction preview failed. Check every required field and the available cash or holdings.' });
      } finally {
        if (isCurrent(session, account, draft)) update({ busy: '' });
      }
    },
    async previewImport() {
      const portfolio = currentPortfolio();
      if (!portfolio || state.busy) return;
      const body = { expected_version: state.history.version, csv_text: state.importDraft.csv_text, source: state.importDraft.source };
      const session = sessionGeneration;
      const account = accountGeneration;
      const draft = draftGeneration;
      update({ busy: 'preview', error: '', preview: null, capturedRequest: null, canSavePreview: false, saveStatus: '' });
      try {
        const preview = await request(`/portfolios/${portfolio.id}/imports/preview`, { method: 'POST', body }, key);
        if (isCurrent(session, account, draft)) update({ preview, capturedRequest: cloned(preview.normalized_request), canSavePreview: true });
      } catch (error) {
        if (isCurrent(session, account, draft)) {
          const line = /^Canonical CSV line (\d+) is invalid or unsupported\.$/.exec(error.message)?.[1];
          update({ error: line ? `Canonical CSV line ${line} is invalid or unsupported. Fix it and preview the whole file again.` : 'The canonical CSV preview failed. Check the header and rows, then preview the whole file again.' });
        }
      } finally {
        if (isCurrent(session, account, draft)) update({ busy: '' });
      }
    },
    async savePreview() {
      const portfolio = currentPortfolio();
      if (!portfolio || !state.canSavePreview || !state.capturedRequest || state.busy) return;
      const body = cloned(state.capturedRequest);
      const session = sessionGeneration;
      const account = accountGeneration;
      const draft = draftGeneration;
      update({ busy: 'save', error: '', saveStatus: 'saving', canSavePreview: false });
      try {
        const result = await request(`/portfolios/${portfolio.id}/transactions`, { method: 'POST', body }, key);
        if (!isCurrent(session, account, draft)) return;
        const contiguous = result.version === state.history.version + result.inserted;
        const byId = new Map([...state.history.transactions, ...result.transactions].map(row => [row.id, row]));
        const transactions = contiguous ? [...byId.values()]
          .sort((left, right) => right.sequence - left.sequence).slice(0, 100) : [];
        update({
          busy: '',
          preview: result,
          canSavePreview: false,
          capturedRequest: null,
          saveStatus: 'saved',
          ledgerState: result.state,
          valuationResult: null,
          history: { transactions, version: result.version, total: result.version },
          portfolios: state.portfolios.map(item => item.id === portfolio.id ? { ...item, version: result.version } : item),
        });
      } catch (error) {
        if (!isCurrent(session, account, draft)) return;
        if (error.uncertain) {
          update({ busy: '', saveStatus: 'uncertain', canSavePreview: true, error: 'The save outcome is uncertain. Retry this captured batch with the same source and external references; do not create new references.' });
        } else {
          update({ busy: '', saveStatus: '', canSavePreview: false, capturedRequest: null, error: error.status === 409 ? ERRORS[409] : 'The server rejected this batch. Refresh and preview it again before saving.' });
        }
      }
    },
    async valuePortfolio() {
      const portfolio = currentPortfolio();
      if (!portfolio || state.busy) return;
      let prices;
      let fx;
      try {
        prices = JSON.parse(state.valuationDraft.prices_text || '[]');
        fx = JSON.parse(state.valuationDraft.fx_text || '[]');
        if (!Array.isArray(prices) || !Array.isArray(fx)) throw new Error('arrays');
      } catch {
        update({ error: 'Prices and FX inputs must each be a JSON array.', valuationResult: null });
        return;
      }
      const body = { as_of: state.valuationDraft.as_of, ...(state.valuationDraft.known_at ? { known_at: state.valuationDraft.known_at } : {}), prices, fx };
      const session = sessionGeneration;
      const account = accountGeneration;
      const draft = draftGeneration;
      update({ busy: 'valuation', error: '', valuationResult: null });
      try {
        const valuationResult = await request(`/portfolios/${portfolio.id}/valuation`, { method: 'POST', body }, key);
        if (isCurrent(session, account, draft)) update({ valuationResult });
      } catch {
        if (isCurrent(session, account, draft)) update({ error: 'Valuation failed. Check supplied dates, security currencies, prices and FX rates.' });
      } finally {
        if (isCurrent(session, account, draft)) update({ busy: '' });
      }
    },
  };
  return workspace;
}
