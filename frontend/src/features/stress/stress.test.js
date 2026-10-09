import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildStress, createStressWorkspace, emptyStress } from './stress.js';

const securities = [{ id: 'a', ticker: 'AAA', currency: 'USD' }, { id: 'b', ticker: 'BBB', currency: 'USD' }];
test('historical replay defaults to buy and hold without changing explicit rebalancing', () => {
  const draft = { ...emptyStress(), history: '{}', assets: [] };
  assert.equal(buildStress(draft).rebalance, 'buy_and_hold');
  assert.equal(buildStress({ ...draft, rebalance: 'per_observation' }).rebalance, 'per_observation');
});
test('request preserves explicit decimal weights and security shocks without finance calculations', () => {
  const draft = { ...emptyStress(), method: 'deterministic_shock', assets: [{ security_id: 'a', weight: '0.60', shock: '-1' }, { security_id: 'b', weight: '0.40', shock: '0.25' }], shock_horizon_label: 'Immediate' };
  const body = buildStress(draft);
  assert.deepEqual(body.assets, [{ security_id: 'a', weight: '0.60' }, { security_id: 'b', weight: '0.40' }]);
  assert.deepEqual(body.shocks, ['-1', '0.25']);
  assert.ok(!('history' in body));
  assert.ok(!('risk_free_rate' in body));
});
test('bootstrap requires explicit integers, mean policy and an actual supplied history', () => {
  const draft = { ...emptyStress(), method: 'block_bootstrap', history: '{}', horizon_periods: '12', path_count: '100', block_length: '3', seed: '0', confidence: '0.95', acceptEmpirical: true };
  const body = buildStress(draft);
  assert.equal(body.seed, 0);
  assert.equal(body.path_count, 100);
  assert.equal(body.mean_policy, 'resample_observed_returns_not_expected_return');
  assert.throws(() => buildStress({ ...draft, seed: '' }), /explicit whole number/);
  assert.throws(() => buildStress({ ...draft, seed: '1.5' }), /explicit whole number/);
  assert.throws(() => buildStress({ ...draft, acceptEmpirical: false }), /empirical returns/);
  assert.throws(() => buildStress({ ...draft, history: '[]' }), /JSON object/);
});
test('workspace clears results when assumptions change and ignores stale evaluation', async () => {
  let resolve;
  const calls = [];
  const store = createStressWorkspace(async (path, options, key) => {
    calls.push({ path, options, key });
    return path.startsWith('/securities') ? securities : new Promise(done => { resolve = done; });
  });
  await store.connect('private-key');
  store.toggleSecurity('a');
  assert.equal(store.getSnapshot().draft.currency, 'USD');
  store.edit('method', 'deterministic_shock');
  store.edit('shock_horizon_label', 'Immediate');
  const pending = store.evaluate();
  store.editAsset('a', 'weight', '1');
  resolve({ result: { scenario_mean_terminal_return: .2 } });
  await pending;
  assert.equal(store.getSnapshot().output, null);
  assert.equal(calls[1].key, 'private-key');
  assert.equal(calls[1].path, '/stress/evaluate');
  store.disconnect();
  assert.deepEqual(store.getSnapshot().draft.assets, []);
  assert.equal(store.getSnapshot().connected, false);
});
test('disconnect prevents late connection from restoring private data and selection changes invalidate', async () => {
  let resolve;
  const store = createStressWorkspace(() => new Promise(done => { resolve = done; }));
  const pending = store.connect('secret');
  store.disconnect();
  resolve(securities);
  await pending;
  assert.deepEqual(store.getSnapshot().securities, []);
});
