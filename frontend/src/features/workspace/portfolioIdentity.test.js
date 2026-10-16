import assert from 'node:assert/strict';
import test from 'node:test';
import { DEMO_LABEL, modeLabel, portfolioRequest } from './portfolioIdentity.js';
import { createLedgerWorkspace } from '../ledger/ledger.js';
import { createOverview } from './overview.js';
import { createPerformance } from '../performance/performance.js';

const portfolio = (id, mode) => ({ id, name: id, base_currency: 'GBP', identity: { mode, publication_eligible: mode === 'demo', visibility: 'private', broker_verified: false } });
const ledger = id => ({ portfolio_id: id, version: 0, cash: [], positions: [], active_transaction_ids: [] });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('identity labels reserve paper and real and fail closed for legacy or unknown mode', () => {
  assert.equal(modeLabel(portfolio('d', 'demo')), DEMO_LABEL);
  assert.match(modeLabel(portfolio('p', 'paper')), /hypothetical; no real money/);
  assert.match(modeLabel(portfolio('r', 'real')), /not verified/);
  for (const row of [{}, portfolio('x', 'unexpected'), portfolio('u', 'unclassified')]) assert.match(modeLabel(row), /Private \/ unclassified/);
});

test('private adapter reads identity list and sends only explicit demo creation fields', async () => {
  const calls = [];
  const fetcher = async (url, options) => { calls.push([url, options]); return { ok: true, json: async () => portfolio('d', 'demo') }; };
  await portfolioRequest('http://local/', 'owner', '/portfolios', {}, fetcher);
  await portfolioRequest('http://local', 'owner', '/portfolios', { method: 'POST', body: { id: 'd', name: 'demo', base_currency: 'GBP', mode: 'demo', broker: 'PRIVATE', account_label: 'PRIVATE' } }, fetcher);
  assert.equal(calls[0][0], 'http://local/api/portfolio-identity/portfolios');
  assert.equal(calls[0][1].headers['X-Research-Key'], 'owner');
  assert.equal(calls[0][1].cache, 'no-store');
  assert.deepEqual(JSON.parse(calls[1][1].body), { id: 'd', name: 'demo', base_currency: 'GBP', mode: 'demo' });
});

test('legacy creation strips only mode and financial transports retain old accounting contracts', async () => {
  const calls = [];
  const fetcher = async (url, options) => { calls.push([url, options]); return { ok: true, json: async () => ({}) }; };
  await portfolioRequest('http://local', 'owner', '/portfolios', { method: 'POST', body: { id: 'u', mode: 'unclassified', broker: 'Intended', account_label: 'Private' } }, fetcher);
  await portfolioRequest('http://local', 'owner', '/portfolios/u/state', {}, fetcher);
  assert.equal(calls[0][0], 'http://local/api/accounting/portfolios');
  assert.deepEqual(JSON.parse(calls[0][1].body), { id: 'u', broker: 'Intended', account_label: 'Private' });
  assert.equal(calls[1][0], 'http://local/api/accounting/portfolios/u/state');
  await assert.rejects(portfolioRequest('http://local', 'owner', '/portfolios', { method: 'POST', body: { mode: 'real' } }, fetcher));
  assert.equal(calls.length, 2);
});

test('identity failures never fall back to inferred classification', async () => {
  let calls = 0;
  await assert.rejects(portfolioRequest('http://local', 'owner', '/portfolios', {}, async () => { ++calls; return { ok: false, status: 503 }; }));
  assert.equal(calls, 1);
});

test('choosing demo resets identity draft and creates a distinct empty ledger deliberately', async () => {
  const requests = [];
  const request = async (path, options = {}) => {
    requests.push([path, options]);
    if (path === '/portfolios') return options.method ? portfolio(options.body.id, 'demo') : [portfolio('u', 'unclassified')];
    if (path.endsWith('/state')) return ledger(path.split('/')[2]);
    return { version: 0, transactions: [], total: 0 };
  };
  const store = createLedgerWorkspace(request);
  await store.connect('owner');
  store.editPortfolio({ id: 'old', name: 'Old identity' });
  store.choosePortfolioMode('demo');
  assert.equal(store.getSnapshot().portfolioDraft.id, '');
  assert.equal(store.getSnapshot().portfolioDraft.mode, 'demo');
  store.editPortfolio({ id: 'new-demo' });
  await store.createPortfolio();
  assert.equal(store.getSnapshot().selectedPortfolioId, 'new-demo');
  assert.equal(store.getSnapshot().ledgerState.portfolio_id, 'new-demo');
  assert.equal(store.getSnapshot().manual.source, 'synthetic_demo');
  assert.equal(store.getSnapshot().importDraft.source, 'synthetic_demo');
  assert.equal(store.getSnapshot().portfolios[0].identity.mode, 'unclassified');
  assert.equal(requests.filter(([, options]) => options.method === 'POST').length, 1);
  store.disconnect();
  assert.deepEqual(store.getSnapshot().portfolios, []);
  assert.equal(store.getSnapshot().portfolioDraft.mode, 'unclassified');
});

test('Overview late demo response cannot attach demo holdings beneath a legacy identity', async () => {
  const pending = deferred();
  const store = createOverview(async path => path === '/portfolios' ? [portfolio('u', 'unclassified'), portfolio('d', 'demo')] : path.includes('/d/') ? pending.promise : ledger('u'), async () => ({}));
  await store.connect('owner');
  const old = store.select('d');
  assert.equal(store.getSnapshot().ledger, null);
  await store.select('u');
  pending.resolve(ledger('d')); await old;
  assert.equal(store.getSnapshot().selectedId, 'u');
  assert.equal(store.getSnapshot().ledger.portfolio_id, 'u');
  assert.match(modeLabel(store.getSnapshot().portfolios[0]), /unclassified/);
  store.disconnect();
  assert.equal(store.getSnapshot().selectedId, '');
});

test('Performance reload, mode switch and lock clear reports and ignore a late demo response', async () => {
  const pending = deferred();
  const store = createPerformance(async path => path === '/portfolios' ? [portfolio('u', 'unclassified'), portfolio('d', 'demo')] : path.includes('/d/') ? pending.promise : ledger('u'), async () => ({}));
  await store.connect('owner');
  store.editEvidence('private draft');
  const old = store.select('d');
  assert.equal(store.getSnapshot().evidence, '');
  assert.equal(store.getSnapshot().report, null);
  await store.select('u');
  pending.resolve(ledger('d')); await old;
  assert.equal(store.getSnapshot().ledger.portfolio_id, 'u');
  store.editEvidence('new draft'); await store.select('u');
  assert.equal(store.getSnapshot().evidence, '');
  store.disconnect();
  assert.equal(store.getSnapshot().selectedId, '');
  assert.equal(store.getSnapshot().ledger, null);
});
