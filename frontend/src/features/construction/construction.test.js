import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildConstructionRequest, createConstructionWorkspace, constructionRequest, emptyConstructionDraft } from './construction.js';

const draft = () => ({ ...emptyConstructionDraft(), valuation_date: '2026-01-02', currency: 'USD', valuation_calendar: 'XNYS close', as_of: '2026-01-02T00:00:00Z', known_at: '2026-01-02T00:00:00Z', risk_free_rate: '0.04', history: JSON.stringify({ security_ids: ['security-a'], observations: [] }) });
const asset = { security_id: 'security-a', current_weight: '1', adopt_view: false, annualized_return: '0.081234567890123456', rationale: 'Owner supplied assumption' };

test('risk-only request leaves investor views absent and preserves explicit units and decimal strings', () => {
  const result = buildConstructionRequest(draft(), [asset]);
  assert.equal(result.assets[0].investor_view, null);
  assert.equal(result.risk_free_rate, '0.04');
  assert.equal(result.assets[0].current_weight, '1');
  assert.equal(result.annualization_assumption, 'iid_period_covariance');
});
test('only an explicitly adopted view reaches construction with matching one-year total return context', () => {
  const result = buildConstructionRequest(draft(), [{ ...asset, adopt_view: true }]);
  assert.equal(result.assets[0].investor_view.annualized_return, '0.081234567890123456');
  assert.deepEqual(result.assets[0].investor_view.context, { security_id: 'security-a', valuation_date: '2026-01-02', horizon_years: 1, return_basis: 'total', money_basis: 'nominal', currency_basis: 'local', local_currency: 'USD', valuation_currency: 'USD', valuation_calendar: 'XNYS close', as_of: '2026-01-02T00:00:00Z', known_at: '2026-01-02T00:00:00Z' });
  assert.throws(() => buildConstructionRequest(draft(), [{ ...asset, adopt_view: true, rationale: '' }]), /rationale/);
});
test('history identifiers are rejected when reordered rather than silently reassigned', () => {
  assert.throws(() => buildConstructionRequest({ ...draft(), history: '{"security_ids":["other"]}' }, [asset]), /ordered/);
  assert.throws(() => buildConstructionRequest({ ...draft(), history: 'invalid' }, [asset]), /JSON/);
});
test('edits and disconnect prevent late private outputs from returning', async () => {
  let resolve;
  const workspace = createConstructionWorkspace(path => path.startsWith('/securities') ? Promise.resolve([{ id: 'security-a', currency: 'USD' }]) : new Promise(done => { resolve = done; }));
  await workspace.connect('private-key');
  workspace.toggleSecurity('security-a');
  for (const [field, value] of Object.entries(draft())) workspace.edit(field, value);
  workspace.editAsset('security-a', 'current_weight', '1');
  const pending = workspace.evaluate();
  workspace.edit('risk_free_rate', '0.05');
  resolve({ result: 'stale' });
  await pending;
  assert.equal(workspace.getSnapshot().output, null);
  const second = workspace.evaluate();
  workspace.disconnect();
  resolve({ result: 'private' });
  await second;
  assert.equal(workspace.getSnapshot().connected, false);
  assert.deepEqual(workspace.getSnapshot().assets, []);
  assert.equal(workspace.getSnapshot().output, null);
});
test('new owner connection supersedes a pending older connection', async () => {
  let resolve;
  const workspace = createConstructionWorkspace((path, options, key) => key === 'old' ? new Promise(done => { resolve = done; }) : Promise.resolve([{ id: 'new' }]));
  const old = workspace.connect('old');
  await workspace.connect('new');
  resolve([{ id: 'old' }]);
  await old;
  assert.equal(workspace.getSnapshot().securities[0].id, 'new');
});
test('changing currency requires explicit readoption instead of reinterpreting an adopted view', async () => {
  const workspace = createConstructionWorkspace(async () => [{ id: 'security-a', currency: 'USD' }]);
  await workspace.connect('key');
  workspace.toggleSecurity('security-a');
  workspace.edit('currency', 'USD');
  workspace.editAsset('security-a', 'adopt_view', true);
  workspace.edit('currency', 'EUR');
  assert.equal(workspace.getSnapshot().assets[0].adopt_view, false);
});
test('private transport masks reflected server and network secrets', async () => {
  const request = (fetcher) => constructionRequest('http://local', 'secret', '/construction/evaluate', {}, fetcher);
  await assert.rejects(request(async () => ({ ok: false, status: 422, json: async () => ({ detail: 'secret' }) })), error => !error.message.includes('secret') && error.message.includes('weights'));
  await assert.rejects(request(async () => { throw new Error('secret'); }), /could not be reached/);
});
