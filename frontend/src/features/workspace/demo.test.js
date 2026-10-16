import assert from 'node:assert/strict';
import test from 'node:test';
import { createLedgerWorkspace } from '../ledger/ledger.js';
import { createPerformance } from '../performance/performance.js';
import { demoRequest } from './portfolioIdentity.js';

const accounts = [{ id: 'demo', base_currency: 'GBP', identity: { mode: 'demo' } }, { id: 'legacy', identity: { mode: 'unclassified' } }];
const request = async path => path === '/portfolios' ? accounts : path.includes('/transactions?') ? { version: 13, transactions: [], total: 13 } : { version: 13, portfolio_id: path.split('/')[2], active_transaction_ids: [], positions: [], cash: [] };
const evidence = () => ({ mode: 'demo', receipt: { portfolio_id: 'demo', start: '2025-12-20', end: '2026-02-05' }, performance: { expected_version: 13, known_at: '2026-10-14T00:00:00Z', daily_marks: [], flow_marks: [] }, benchmark: { identity: { name: 'Original synthetic comparison' }, levels: [] } });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('demo transport is owner-only, no-store and uses deliberate POST only for load', async () => {
  const calls = [];
  const fetcher = async (url, options) => { calls.push([url, options]); return { ok: true, json: async () => ({ mode: 'demo' }) }; };
  await demoRequest('http://local/', 'in-memory-owner', 'id/value', 'load', fetcher);
  await demoRequest('http://local', 'in-memory-owner', 'id/value', 'evidence', fetcher);
  assert.equal(calls[0][0], 'http://local/api/portfolio-identity/portfolios/id%2Fvalue/demo/load');
  assert.equal(calls[0][1].method, 'POST');
  assert.equal(calls[1][1].method, 'GET');
  assert.equal(calls[0][1].cache, 'no-store');
  assert.equal(calls[0][1].headers['X-Research-Key'], 'in-memory-owner');
  await assert.rejects(demoRequest('http://local', 'owner', 'demo', 'load', async () => ({ ok: false, status: 409 })));
});

test('fixture loader refreshes coherent ledger and never targets unclassified history', async () => {
  let loads = 0;
  const store = createLedgerWorkspace(request, async () => { ++loads; return { ledger_version: 13 }; });
  await store.connect('owner');
  await store.loadDemoFixture();
  assert.equal(loads, 1);
  assert.equal(store.getSnapshot().history.version, 13);
  assert.equal(store.getSnapshot().ledgerState.portfolio_id, 'demo');
  await store.selectPortfolio('legacy'); await store.loadDemoFixture();
  assert.equal(loads, 1);
});

test('locked loader response cannot repopulate private demo state', async () => {
  const pending = deferred();
  const store = createLedgerWorkspace(request, () => pending.promise);
  await store.connect('owner');
  const loading = store.loadDemoFixture(); store.disconnect();
  pending.resolve({ ledger_version: 13 }); await loading;
  assert.equal(store.getSnapshot().selectedPortfolioId, '');
  assert.equal(store.getSnapshot().ledgerState, null);
});

test('demo report setup selects explicit synthetic inputs but does not calculate or publish', async () => {
  let calculations = 0;
  const store = createPerformance(request, async () => { ++calculations; }, null, null, null, null, null, async () => evidence());
  await store.connect('owner'); await store.loadDemoEvidence();
  const state = store.getSnapshot();
  assert.equal(state.draft.start, '2025-12-20');
  assert.equal(state.draft.known_at, '2026-10-14T00:00:00Z');
  assert.equal(state.draft.include_contribution, true);
  assert.equal(state.draft.include_benchmark, true);
  assert.equal(state.draft.include_factors, false);
  assert.equal(state.draft.max_mark_age_days, '0');
  assert.deepEqual(JSON.parse(state.evidence), { daily_marks: [], flow_marks: [] });
  assert.equal(calculations, 0);
  assert.equal(state.report, null);
});

test('late or mismatched demo evidence is rejected after selection and lock', async () => {
  const pending = deferred();
  const store = createPerformance(request, async () => ({}), null, null, null, null, null, () => pending.promise);
  await store.connect('owner');
  const loading = store.loadDemoEvidence(); await store.select('legacy');
  pending.resolve(evidence()); await loading;
  assert.equal(store.getSnapshot().evidence, '');
  assert.equal(store.getSnapshot().selectedId, 'legacy');
  store.disconnect();
  assert.equal(store.getSnapshot().benchmarkEvidence, '');
  const mismatched = createPerformance(request, async () => ({}), null, null, null, null, null, async () => ({ ...evidence(), mode: 'real' }));
  await mismatched.connect('owner'); await mismatched.loadDemoEvidence();
  assert.equal(mismatched.getSnapshot().evidence, '');
  assert.match(mismatched.getSnapshot().error, /unavailable/);
});
