import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createOverview } from './overview.js';

test('overview reads recorded accounts and exact server holdings without market-value calculations', async () => {
  const calls = [];
  const store = createOverview(async (path, options, key) => {
    calls.push([path, key]);
    return path === '/portfolios' ? [{ id: 'p', name: 'My account', base_currency: 'GBP' }] : { version: 2, positions: [{ security_id: 's', quantity: '2.5000', currency: 'GBP' }], cash: [] };
  }, async () => ({ ticker: 'TEST', name: 'Test equity' }));
  await store.connect('private');
  assert.equal(store.getSnapshot().ledger.positions[0].quantity, '2.5000');
  assert.equal(store.getSnapshot().securities.s.ticker, 'TEST');
  assert.deepEqual(calls, [['/portfolios', 'private'], ['/portfolios/p/state', 'private']]);
  assert.equal(store.getSnapshot().ledger.nav, undefined);
  store.disconnect();
  assert.deepEqual(store.getSnapshot().portfolios, []);
  assert.equal(store.getSnapshot().ledger, null);
});

test('overview discards late responses on lock and presents unavailable separately from empty', async () => {
  let finish;
  const store = createOverview(() => new Promise(resolve => { finish = resolve; }), async () => ({}));
  const pending = store.connect('key'); store.disconnect(); finish([{ id: 'private' }]); await pending;
  assert.deepEqual(store.getSnapshot().portfolios, []);
  const failed = createOverview(async () => { throw new Error('secret server body'); }, async () => ({}));
  await failed.connect('key');
  assert.equal(failed.getSnapshot().connected, false);
  assert.match(failed.getSnapshot().error, /unavailable/);
  assert.doesNotMatch(failed.getSnapshot().error, /secret/);
});
