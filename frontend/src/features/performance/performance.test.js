import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setImmediate } from 'node:timers';
import { createPerformance, evidenceTemplate, performanceRequest, buildPerformanceRequest } from './performance.js';
import { createPrivateSession } from '../workspace/session.js';

const draft = { start: '2026-01-01', end: '2026-01-03', known_at: '2026-01-04T12:00:00Z', risk_free_rate: '0', confidence: '0.95', max_mark_age_days: '3' };
const evidence = { daily_marks: ['01', '02', '03'].map(day => ({ date: `2026-01-${day}`, prices: [], fx: [] })), flow_marks: [] };
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const setup = (post = async () => ({ twr: { value: .1 } })) => {
  const calls = [];
  const request = async (path, options, key) => {
    calls.push({ path, options, key });
    if (path === '/portfolios') return [{ id: 'a', name: 'A', version: 7 }, { id: 'b', name: 'B', version: 4 }];
    return { version: path.includes('/a/') ? 7 : 4, active_transaction_ids: [], positions: [], cash: [] };
  };
  return { store: createPerformance(request, post), calls };
};

test('request preserves decimal strings and explicit conventions; rejects numeric evidence and dates outside selection', () => {
  const supplied = structuredClone(evidence);
  supplied.daily_marks[0].prices = [{ security_id: 's', currency: 'USD', price: '123.1234567890123456789', observed_at: '2026-01-01T12:00:00Z', source: 'reviewed' }];
  const body = buildPerformanceRequest(draft, JSON.stringify(supplied), 7);
  assert.equal(body.daily_marks[0].prices[0].price, '123.1234567890123456789');
  assert.equal(body.expected_version, 7);
  assert.equal(body.periods_per_year, 365);
  assert.equal(body.calendar, 'UTC_calendar_daily');
  assert.equal(body.price_convention, 'unadjusted');
  assert.equal(body.max_mark_age_days, 3);
  supplied.daily_marks[0].prices[0].price = 123;
  assert.throws(() => buildPerformanceRequest(draft, JSON.stringify(supplied), 7), /decimal strings/);
  assert.throws(() => buildPerformanceRequest({ ...draft, end: '2026-01-02' }, JSON.stringify(evidence), 7), /selected window/);
});

test('template has consecutive daily empty marks and only active, known, within-window external flow IDs', () => {
  const rows = [
    { id: 'opening', type: 'DEPOSIT', effective_at: '2026-01-01T10:00:00Z', recorded_at: '2026-01-01T10:00:00Z' },
    { id: 'flow', type: 'WITHDRAWAL', effective_at: '2026-01-02T10:00:00Z', recorded_at: '2026-01-02T10:00:00Z' },
    { id: 'reversed', type: 'DEPOSIT', effective_at: '2026-01-02T10:00:00Z', recorded_at: '2026-01-02T10:00:00Z' },
  ];
  assert.deepEqual(evidenceTemplate(draft, rows, ['opening', 'flow']), { ...evidence, flow_marks: [{ transaction_id: 'flow', prices: [], fx: [] }] });
});

test('global session supplies credential and lock clears drafts and rejects late results and file imports', async () => {
  const pending = deferred();
  const { store, calls } = setup(() => pending.promise);
  const session = createPrivateSession(async () => {});
  session.attach(store);
  await session.unlock('private-only');
  await new Promise(resolve => setImmediate(resolve));
  store.edit(draft); store.editEvidence(JSON.stringify(evidence));
  const running = store.run();
  session.lock(); pending.resolve({ twr: { value: .5 } }); await running;
  assert.equal(store.getSnapshot().report, null);
  assert.equal(store.getSnapshot().evidence, '');
  assert.equal(store.getSnapshot().connected, false);
  assert.equal(calls[0].key, 'private-only');
  assert.doesNotMatch(JSON.stringify(store.getSnapshot()), /private-only/);
  await store.connect('k');
  const file = deferred(); const importing = store.importEvidence(file.promise);
  store.disconnect(); file.resolve(JSON.stringify(evidence)); await importing;
  assert.equal(store.getSnapshot().evidence, '');
});

test('account changes discard evidence and use new version; failed reports clear stale results', async () => {
  const requests = []; let fail = false;
  const { store } = setup(async (id, body) => { requests.push([id, body]); if (fail) throw Object.assign(new Error('secret body'), { status: 409 }); return { twr: { value: .1 } }; });
  await store.connect('k'); store.edit(draft); store.editEvidence(JSON.stringify(evidence)); await store.run();
  assert.equal(requests[0][1].expected_version, 7);
  await store.select('b');
  assert.equal(store.getSnapshot().evidence, ''); assert.equal(store.getSnapshot().report, null);
  store.edit(draft); store.editEvidence(JSON.stringify(evidence)); await store.run();
  assert.equal(requests[1][0], 'b'); assert.equal(requests[1][1].expected_version, 4);
  fail = true; await store.run();
  assert.equal(store.getSnapshot().report, null);
  assert.match(store.getSnapshot().error, /Reload/); assert.doesNotMatch(store.getSnapshot().error, /secret/);
});

test('private performance request has no-store and exact request body, sanitizes server errors', async () => {
  let capture;
  await performanceRequest('https://local/', 'k', 'a', { daily_marks: evidence.daily_marks }, async (url, options) => { capture = { url, options }; return { ok: true, json: async () => ({}) }; });
  assert.equal(capture.url, 'https://local/api/performance/portfolios/a/report');
  assert.equal(capture.options.cache, 'no-store');
  assert.equal(capture.options.headers['X-Research-Key'], 'k');
  await assert.rejects(performanceRequest('', 'k', 'a', {}, async () => ({ ok: false, status: 422 })), /supplied evidence/);
});

test('a late account response cannot replace the newly selected account', async () => {
  const first = deferred();
  const store = createPerformance(async path => {
    if (path === '/portfolios') return [{ id: 'a' }, { id: 'b' }];
    if (path === '/portfolios/a/state') return first.promise;
    return { version: 9 };
  }, async () => ({}));
  const connecting = store.connect('k'); await new Promise(resolve => setImmediate(resolve));
  await store.select('b'); first.resolve({ version: 2 }); await connecting;
  assert.equal(store.getSnapshot().selectedId, 'b'); assert.equal(store.getSnapshot().ledger.version, 9);
});

test('template paginates real history, uses historical active IDs, and blocks changing ledger versions', async () => {
  const paths = []; let changed = false;
  const row = { id: 'actual-flow', sequence: 4, type: 'DEPOSIT', effective_at: '2026-01-02T10:00:00Z', recorded_at: '2026-01-02T10:00:00Z' };
  const store = createPerformance(async path => {
    paths.push(path);
    if (path === '/portfolios') return [{ id: 'a' }];
    if (path.includes('/transactions?')) return { version: changed ? 8 : 7, total: 2, transactions: path.endsWith('offset=0') ? [row] : [{ ...row, id: 'reversed-flow' }] };
    return { version: 7, active_transaction_ids: ['actual-flow'] };
  }, async () => ({}));
  await store.connect('k'); store.edit(draft); await store.makeTemplate();
  assert.equal(JSON.parse(store.getSnapshot().evidence).flow_marks[0].transaction_id, 'actual-flow');
  assert.equal(JSON.parse(store.getSnapshot().evidence).flow_marks.length, 1);
  assert.ok(paths.some(path => path.endsWith('offset=1')));
  assert.ok(paths.some(path => path.includes('known_at=2026-01-04T12%3A00%3A00Z')));
  changed = true; await store.makeTemplate();
  assert.equal(store.getSnapshot().evidence, ''); assert.match(store.getSnapshot().error, /ledger changed/);
});

test('evidence validation handles malformed rows and missing provenance without exposing implementation errors', () => {
  const malformed = structuredClone(evidence);
  malformed.daily_marks[0] = null;
  assert.throws(() => buildPerformanceRequest(draft, JSON.stringify(malformed), 7), /selected window/);
  malformed.daily_marks[0] = { date: draft.start, prices: [{ price: '1', source: 23, currency: 'GBP', observed_at: '2026-01-01T12:00:00Z' }], fx: [] };
  assert.throws(() => buildPerformanceRequest(draft, JSON.stringify(malformed), 7), /source/);
});
