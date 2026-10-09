import assert from 'node:assert/strict';
import test from 'node:test';

import {
  accountingRequest,
  buildManualTransaction,
  correctionFields,
  createLedgerWorkspace,
  emptyManualDraft,
} from './ledger.js';

const portfolio = (id, version = 0) => ({
  id,
  name: `Portfolio ${id}`,
  base_currency: 'GBP',
  broker: 'Lightyear',
  account_label: 'Stocks & Shares ISA',
  created_at: '2026-09-12T08:00:00+00:00',
  version,
});

const emptyState = id => ({
  portfolio_id: id,
  base_currency: 'GBP',
  version: 0,
  as_of: '2026-09-12T08:00:00+00:00',
  known_at: '2026-09-12T08:00:00+00:00',
  cash: [],
  positions: [],
  active_transaction_ids: [],
  convention: 'trade_date_economic_cash',
});

const flush = async () => { await Promise.resolve(); await Promise.resolve(); };
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function connectedWorkspace(overrides = {}) {
  const calls = [];
  const request = async (path, options, key) => {
    calls.push({ path, options, key });
    if (path === '/portfolios') return [portfolio('p1')];
    if (path.includes('/transactions?')) return { transactions: [], version: 0, total: 0 };
    if (path.includes('/state')) return emptyState(path.split('/')[2]);
    return overrides.request?.(path, options, key, calls);
  };
  const workspace = createLedgerWorkspace(request);
  return { workspace, calls };
}

test('manual transaction builder preserves exact decimal text and includes only type fields', () => {
  const draft = {
    ...emptyManualDraft(),
    type: 'BUY',
    effective_at: '2026-09-12T10:30:00+04:00',
    currency: 'GBP',
    security_id: '14edacba-e269-4eb7-89d0-17536509f32a',
    quantity: '0.1234567890',
    price: '10.0000000001',
    fees: '0.0100000000',
    source: 'manual',
    external_reference: 'manual-20260912-001',
    note: 'Owner-entered fill',
  };

  assert.deepEqual(buildManualTransaction(draft), {
    type: 'BUY',
    effective_at: '2026-09-12T10:30:00+04:00',
    currency: 'GBP',
    security_id: '14edacba-e269-4eb7-89d0-17536509f32a',
    quantity: '0.1234567890',
    price: '10.0000000001',
    fees: '0.0100000000',
    source: 'manual',
    external_reference: 'manual-20260912-001',
    note: 'Owner-entered fill',
  });
});

test('choosing a correction copies the original economic timestamp and currency', () => {
  assert.deepEqual(correctionFields({
    id: 'original-1', effective_at: '2026-09-10T08:15:00+04:00', currency: 'USD',
  }), {
    reverses_id: 'original-1', effective_at: '2026-09-10T08:15:00+04:00', currency: 'USD',
  });
});

test('preview captures the exact request and save reuses it atomically', async () => {
  let previewBody;
  let savedBody;
  const { workspace } = connectedWorkspace({ request: async (path, options) => {
    if (path.endsWith('/transactions/preview')) {
      previewBody = options.body;
      return { version: 0, inserted: 1, duplicates: 0, transactions: [{ id: 't-preview', ...options.body.transactions[0] }], state: emptyState('p1') };
    }
    if (path.endsWith('/transactions')) {
      savedBody = options.body;
      return { version: 1, inserted: 1, duplicates: 0, transactions: [{ id: 't1', ...options.body.transactions[0] }], state: { ...emptyState('p1'), version: 1 } };
    }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editManual({
    type: 'DEPOSIT', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '1000.0000000000',
    source: 'manual', external_reference: 'deposit-1', note: '',
  });
  await workspace.previewManual();
  assert.equal(workspace.getSnapshot().canSavePreview, true);
  await workspace.savePreview();

  assert.deepEqual(savedBody, previewBody);
  assert.equal(savedBody.transactions[0].amount, '1000.0000000000');
  assert.equal(workspace.getSnapshot().saveStatus, 'saved');
});

test('editing after preview invalidates save and ignores the older preview response', async () => {
  const late = deferred();
  const { workspace } = connectedWorkspace({ request: path => {
    if (path.endsWith('/transactions/preview')) return late.promise;
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editManual({ type: 'DEPOSIT', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '10', source: 'manual', external_reference: 'deposit-race' });
  const pending = workspace.previewManual();
  workspace.editManual({ amount: '11' });
  late.resolve({ version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') });
  await pending;

  assert.equal(workspace.getSnapshot().preview, null);
  assert.equal(workspace.getSnapshot().canSavePreview, false);
  assert.equal(workspace.getSnapshot().manual.amount, '11');
  assert.equal(workspace.getSnapshot().busy, '');
});

test('editing valuation while its request is pending clears busy and ignores its result', async () => {
  const late = deferred();
  const { workspace } = connectedWorkspace({ request: path => {
    if (path.endsWith('/valuation')) return late.promise;
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editValuation({ as_of: '2026-09-12T11:00:00+04:00' });
  const pending = workspace.valuePortfolio();
  workspace.editValuation({ as_of: '2026-09-12T12:00:00+04:00' });
  late.resolve({ state: emptyState('p1'), nav: '10', positions: [], cash: [], reason: null, inputs: {} });
  await pending;
  assert.equal(workspace.getSnapshot().busy, '');
  assert.equal(workspace.getSnapshot().valuationResult, null);
});

test('a preview request cannot overlap an in-flight supplied-mark valuation', async () => {
  const late = deferred();
  let previews = 0;
  const { workspace } = connectedWorkspace({ request: path => {
    if (path.endsWith('/valuation')) return late.promise;
    if (path.endsWith('/transactions/preview')) { previews += 1; return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') }; }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editValuation({ as_of: '2026-09-12T11:00:00+04:00' });
  const pending = workspace.valuePortfolio();
  await workspace.previewManual();
  assert.equal(previews, 0);
  late.resolve({ state: emptyState('p1'), nav: null, positions: [], cash: [], reason: 'empty', inputs: {} });
  await pending;
});

test('account and disconnect generations prevent stale account loads from changing state', async () => {
  const p1Transactions = deferred();
  const request = async path => {
    if (path === '/portfolios') return [portfolio('p1'), portfolio('p2')];
    if (path.includes('/portfolios/p1/transactions?')) return p1Transactions.promise;
    if (path.includes('/portfolios/p1/state')) return emptyState('p1');
    if (path.includes('/portfolios/p2/transactions?')) return { transactions: [{ id: 'p2-row' }], version: 2, total: 1 };
    if (path.includes('/portfolios/p2/state')) return { ...emptyState('p2'), version: 2 };
    throw new Error(`Unexpected ${path}`);
  };
  const workspace = createLedgerWorkspace(request);
  const connecting = workspace.connect('owner-secret');
  await flush();
  const switching = workspace.selectPortfolio('p2');
  await switching;
  p1Transactions.resolve({ transactions: [{ id: 'stale-p1-row' }], version: 1, total: 1 });
  await connecting;

  assert.equal(workspace.getSnapshot().selectedPortfolioId, 'p2');
  assert.deepEqual(workspace.getSnapshot().history.transactions, [{ id: 'p2-row' }]);

  const late = deferred();
  const disconnected = createLedgerWorkspace(async path => path === '/portfolios' ? late.promise : emptyState('unused'));
  const pending = disconnected.connect('do-not-display');
  disconnected.disconnect();
  late.resolve([portfolio('stale')]);
  await pending;
  assert.equal(disconnected.getSnapshot().connected, false);
  assert.deepEqual(disconnected.getSnapshot().portfolios, []);
});

test('switching portfolios clears account-scoped drafts and captured valuation', async () => {
  const workspace = createLedgerWorkspace(async path => {
    if (path === '/portfolios') return [portfolio('p1'), portfolio('p2')];
    if (path.includes('/transactions?')) return { transactions: [], version: 0, total: 0 };
    if (path.includes('/state')) return emptyState(path.split('/')[2]);
    if (path.endsWith('/valuation')) return { state: emptyState('p1'), nav: '1', positions: [], cash: [], reason: null, inputs: {} };
    throw new Error(`Unexpected ${path}`);
  });
  await workspace.connect('owner-secret');
  workspace.editManual({ amount: '111', external_reference: 'p1-reference' });
  workspace.editImport({ csv_text: 'p1-private-csv' });
  workspace.editValuation({ as_of: '2026-09-12T11:00:00+04:00' });
  await workspace.valuePortfolio();
  await workspace.selectPortfolio('p2');
  assert.equal(workspace.getSnapshot().manual.external_reference, '');
  assert.equal(workspace.getSnapshot().importDraft.csv_text, '');
  assert.equal(workspace.getSnapshot().valuationDraft.as_of, '');
  assert.equal(workspace.getSnapshot().valuationResult, null);
});

test('editing the portfolio draft prevents a late create response from clearing the newer draft', async () => {
  const late = deferred();
  const workspace = createLedgerWorkspace(async (path, options) => {
    if (path === '/portfolios' && options.method === 'POST') return late.promise;
    if (path === '/portfolios') return [portfolio('p1')];
    if (path.includes('/transactions?')) return { transactions: [], version: 0, total: 0 };
    if (path.includes('/state')) return emptyState('p1');
    throw new Error(`Unexpected ${path}`);
  });
  await workspace.connect('owner-secret');
  workspace.editPortfolio({ id: '11111111-1111-4111-8111-111111111111', name: 'First name' });
  const pending = workspace.createPortfolio();
  workspace.editPortfolio({ name: 'Newer draft name' });
  late.resolve(portfolio('11111111-1111-4111-8111-111111111111'));
  await pending;
  assert.equal(workspace.getSnapshot().portfolioDraft.name, 'Newer draft name');
  assert.equal(workspace.getSnapshot().selectedPortfolioId, 'p1');
});

test('an uncertain save is retried with the same captured idempotency fields', async () => {
  const saved = [];
  let attempts = 0;
  const { workspace } = connectedWorkspace({ request: async (path, options) => {
    if (path.endsWith('/transactions/preview')) return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') };
    if (path.endsWith('/transactions')) {
      saved.push(structuredClone(options.body));
      attempts += 1;
      if (attempts === 1) {
        const error = new Error('The accounting service could not be reached.');
        error.uncertain = true;
        throw error;
      }
      return { version: 1, inserted: 0, duplicates: 1, transactions: [], state: { ...emptyState('p1'), version: 1 } };
    }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editManual({ type: 'FEE', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '2.50', source: 'manual', external_reference: 'fee-stable-ref' });
  await workspace.previewManual();
  await workspace.savePreview();
  assert.equal(workspace.getSnapshot().saveStatus, 'uncertain');
  assert.equal(workspace.getSnapshot().canSavePreview, true);
  await workspace.savePreview();
  assert.deepEqual(saved[1], saved[0]);
  assert.equal(saved[1].transactions[0].external_reference, 'fee-stable-ref');
});

test('a second save click while the first is pending cannot send a duplicate request', async () => {
  const late = deferred();
  let saves = 0;
  const { workspace } = connectedWorkspace({ request: path => {
    if (path.endsWith('/transactions/preview')) return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') };
    if (path.endsWith('/transactions')) { saves += 1; return late.promise; }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editManual({ type: 'DEPOSIT', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '100', source: 'manual', external_reference: 'double-save' });
  await workspace.previewManual();
  const pending = workspace.savePreview();
  await workspace.savePreview();
  assert.equal(saves, 1);
  late.resolve({ version: 1, inserted: 1, duplicates: 0, transactions: [], state: { ...emptyState('p1'), version: 1 } });
  await pending;
});

test('successful save invalidates a prior supplied-mark valuation', async () => {
  const { workspace } = connectedWorkspace({ request: async path => {
    if (path.endsWith('/valuation')) return { state: emptyState('p1'), nav: '100', positions: [], cash: [], reason: null, inputs: {} };
    if (path.endsWith('/transactions/preview')) return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') };
    if (path.endsWith('/transactions')) return { version: 1, inserted: 1, duplicates: 0, transactions: [], state: { ...emptyState('p1'), version: 1 } };
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editValuation({ as_of: '2026-09-12T11:00:00+04:00' });
  await workspace.valuePortfolio();
  workspace.editManual({ type: 'DEPOSIT', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '100', source: 'manual', external_reference: 'post-valuation' });
  await workspace.previewManual();
  await workspace.savePreview();
  assert.equal(workspace.getSnapshot().valuationResult, null);
});

test('history loads beyond the first 100 in sequence order without duplicating rows', async () => {
  const first = Array.from({ length: 100 }, (_, index) => ({ id: `row-${200 - index}`, sequence: 200 - index }));
  const next = Array.from({ length: 100 }, (_, index) => ({ id: `row-${100 - index}`, sequence: 100 - index }));
  const workspace = createLedgerWorkspace(async path => {
    if (path === '/portfolios') return [portfolio('p1', 200)];
    if (path.includes('offset=0')) return { transactions: first, version: 200, total: 200 };
    if (path.includes('offset=100')) return { transactions: next, version: 200, total: 200 };
    if (path.includes('/state')) return { ...emptyState('p1'), version: 200 };
    throw new Error(`Unexpected ${path}`);
  });
  await workspace.connect('owner-secret');
  await workspace.loadMoreHistory();
  const history = workspace.getSnapshot().history;
  assert.equal(history.transactions.length, 200);
  assert.equal(history.transactions[0].sequence, 200);
  assert.equal(history.transactions[199].sequence, 1);
  assert.equal(new Set(history.transactions.map(row => row.id)).size, 200);
});

test('replaying an old row keeps history pagination contiguous and duplicate-free', async () => {
  const first = Array.from({ length: 100 }, (_, i) => ({ id: `row-${200 - i}`, sequence: 200 - i }));
  const old = { id: 'row-1', sequence: 1 };
  const result = { version: 200, inserted: 0, duplicates: 2, transactions: [old, old], state: { ...emptyState('p1'), version: 200 } };
  const workspace = createLedgerWorkspace(async path => {
    if (path === '/portfolios') return [portfolio('p1', 200)];
    if (path.includes('/transactions?')) return { transactions: first, version: 200, total: 200 };
    if (path.includes('/state')) return result.state;
    return result;
  });
  await workspace.connect('owner-secret');
  await workspace.previewManual();
  await workspace.savePreview();
  assert.deepEqual(workspace.getSnapshot().history.transactions, first);
});

test('duplicate references within a saved batch do not duplicate history rows', async () => {
  const row = { id: 'row-1', sequence: 1 };
  const result = { version: 1, inserted: 1, duplicates: 1, transactions: [row, row], state: { ...emptyState('p1'), version: 1 } };
  const { workspace } = connectedWorkspace({ request: async () => result });
  await workspace.connect('owner-secret');
  await workspace.previewManual();
  await workspace.savePreview();
  assert.deepEqual(workspace.getSnapshot().history.transactions, [row]);
});

test('a stale duplicate retry reloads history from offset zero rather than skipping unseen rows', async () => {
  const row = { id: 'row-1', sequence: 1 };
  const result = { version: 2, inserted: 0, duplicates: 1, transactions: [row], state: { ...emptyState('p1'), version: 2 } };
  const { workspace } = connectedWorkspace({ request: async () => result });
  await workspace.connect('owner-secret');
  await workspace.previewManual();
  await workspace.savePreview();
  assert.deepEqual(workspace.getSnapshot().history.transactions, []);
  assert.equal(workspace.getSnapshot().history.total, 2);
  assert.equal(workspace.getSnapshot().ledgerState.version, 2);
});

test('a mismatched state and history version is not presented as one coherent ledger', async () => {
  const workspace = createLedgerWorkspace(async path => {
    if (path === '/portfolios') return [portfolio('p1', 1)];
    if (path.includes('/transactions?')) return { transactions: [{ id: 'row-1', sequence: 1 }], version: 1, total: 1 };
    if (path.includes('/state')) return { ...emptyState('p1'), version: 2 };
    throw new Error(`Unexpected ${path}`);
  });
  await workspace.connect('owner-secret');
  assert.equal(workspace.getSnapshot().ledgerState, null);
  assert.match(workspace.getSnapshot().error, /Refresh/);
});

test('a definitive save conflict disables retry until the batch is previewed again', async () => {
  const { workspace } = connectedWorkspace({ request: async path => {
    if (path.endsWith('/transactions/preview')) return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') };
    if (path.endsWith('/transactions')) {
      const error = new Error('The portfolio changed or a source/reference conflicts with different content. Refresh before continuing.');
      error.status = 409;
      throw error;
    }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editManual({ type: 'DEPOSIT', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '100', source: 'manual', external_reference: 'ref-conflict' });
  await workspace.previewManual();
  await workspace.savePreview();
  assert.equal(workspace.getSnapshot().canSavePreview, false);
  assert.equal(workspace.getSnapshot().saveStatus, '');
  assert.match(workspace.getSnapshot().error, /Refresh/);
});

test('editing another draft after preview removes save permission', async () => {
  const { workspace } = connectedWorkspace({ request: path => {
    if (path.endsWith('/transactions/preview')) return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1') };
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editManual({ type: 'DEPOSIT', effective_at: '2026-09-12T09:00:00+04:00', currency: 'GBP', amount: '100', source: 'manual', external_reference: 'ref-other-draft' });
  await workspace.previewManual();
  workspace.editValuation({ as_of: '2026-09-12T12:00:00+04:00' });
  assert.equal(workspace.getSnapshot().canSavePreview, false);
  assert.equal(workspace.getSnapshot().preview, null);
});

test('CSV preview captures the backend normalized request for explicit save', async () => {
  const normalized = { expected_version: 0, transactions: [{ type: 'DEPOSIT', effective_at: '2026-09-12T08:00:00+00:00', currency: 'GBP', amount: '25.00', fees: '0', source: 'lightyear_reviewed', external_reference: 'row-1', note: '' }] };
  let saved;
  const { workspace } = connectedWorkspace({ request: async (path, options) => {
    if (path.endsWith('/imports/preview')) return { version: 0, inserted: 1, duplicates: 0, transactions: [], state: emptyState('p1'), normalized_request: normalized };
    if (path.endsWith('/transactions')) { saved = options.body; return { version: 1, inserted: 1, duplicates: 0, transactions: [], state: { ...emptyState('p1'), version: 1 } }; }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editImport({ csv_text: 'type,effective_at,currency,amount,fees,source,external_reference,note\nDEPOSIT,2026-09-12T08:00:00+00:00,GBP,25.00,0,,row-1,', source: 'lightyear_reviewed' });
  await workspace.previewImport();
  await workspace.savePreview();
  assert.deepEqual(saved, normalized);
});

test('CSV preview displays only the validated failing line number', async () => {
  const { workspace } = connectedWorkspace({ request: path => {
    if (path.endsWith('/imports/preview')) throw new Error('Canonical CSV line 4 is invalid or unsupported.');
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editImport({ csv_text: 'type,effective_at,currency,external_reference\nwrong', source: 'lightyear_reviewed' });
  await workspace.previewImport();
  assert.match(workspace.getSnapshot().error, /line 4/);
  assert.doesNotMatch(workspace.getSnapshot().error, /wrong/);
});

test('valuation sends supplied price and FX strings without doing browser calculations', async () => {
  let body;
  const { workspace } = connectedWorkspace({ request: async (path, options) => {
    if (path.endsWith('/valuation')) { body = options.body; return { ...emptyState('p1'), nav: '122.34', reason: null, positions: [], cash: [], inputs: options.body }; }
    throw new Error(`Unexpected ${path}`);
  } });
  await workspace.connect('owner-secret');
  workspace.editValuation({ as_of: '2026-09-12T12:00:00+04:00', known_at: '', prices_text: '[{"security_id":"s1","currency":"USD","price":"99.9900","observed_at":"2026-09-12T10:00:00+04:00","source":"owner supplied"}]', fx_text: '[{"currency":"USD","rate":"0.740000","observed_at":"2026-09-12T10:00:00+04:00","source":"owner supplied"}]' });
  await workspace.valuePortfolio();
  assert.deepEqual(body, { as_of: '2026-09-12T12:00:00+04:00', prices: [{ security_id: 's1', currency: 'USD', price: '99.9900', observed_at: '2026-09-12T10:00:00+04:00', source: 'owner supplied' }], fx: [{ currency: 'USD', rate: '0.740000', observed_at: '2026-09-12T10:00:00+04:00', source: 'owner supplied' }] });
  assert.equal(workspace.getSnapshot().valuationResult.nav, '122.34');
});

test('accounting request uses private no-store headers and safe errors', async () => {
  let init;
  const result = await accountingRequest('http://local/', 'super-secret', '/portfolios', {}, async (url, options) => {
    init = { url, options };
    return { ok: true, json: async () => [] };
  });
  assert.deepEqual(result, []);
  assert.equal(init.url, 'http://local/api/accounting/portfolios');
  assert.equal(init.options.cache, 'no-store');
  assert.equal(init.options.headers['X-Research-Key'], 'super-secret');

  await assert.rejects(
    accountingRequest('http://local', 'super-secret', '/portfolios', {}, async () => ({ ok: false, status: 422, json: async () => ({ detail: 'super-secret leaked row' }) })),
    error => error.message === 'Check the accounting fields, exact decimals, currencies, timestamps and available cash or holdings.',
  );
});

test('canonical CSV errors disclose only their failing line number', async () => {
  await assert.rejects(
    accountingRequest('http://local', 'owner-secret', '/portfolios/p1/imports/preview', { method: 'POST', body: { csv_text: 'secret' } }, async () => ({ ok: false, status: 422, json: async () => ({ detail: 'CSV line 4: secret account information' }) })),
    error => error.message === 'Canonical CSV line 4 is invalid or unsupported.' && !error.message.includes('secret'),
  );
});
