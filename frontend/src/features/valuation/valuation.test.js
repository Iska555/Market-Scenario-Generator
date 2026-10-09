import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildEvaluation, emptyDraft, createValuationWorkspace, valuationRequest } from './valuation.js';

test('user return strings reach the API without a floating point round trip', () => {
  const draft = emptyDraft('USD');
  draft.annualized_return = '0.123456789012345';
  draft.cumulative_return = '';
  draft.rationale = 'Explicit view';
  const body = buildEvaluation(draft, 'security');
  assert.equal(body.annualized_return, '0.123456789012345');
  assert.equal(body.cumulative_return, null);
  assert.equal(body.context.security_id, 'security');
});

test('scenario probabilities remain absent unless explicitly enabled', () => {
  const draft = emptyDraft('USD');
  draft.model = 'scenario_set';
  let body = buildEvaluation(draft, 'security');
  assert.ok(body.scenarios.every(item => item.probability === null));
  assert.equal(body.probability_source, null);
  draft.useProbabilities = true;
  draft.probability_source = 'Owner assumptions';
  draft.scenarios.bear.probability = '0.2';
  draft.scenarios.base.probability = '0.6';
  draft.scenarios.bull.probability = '0.2';
  body = buildEvaluation(draft, 'security');
  assert.deepEqual(body.scenarios.map(item => item.probability), ['0.2', '0.6', '0.2']);
  assert.equal(body.probability_type, 'user_assumption');
});

test('changing to another valuation currency requires freshly supplied FX assumptions', () => {
  const workspace = createValuationWorkspace(async () => []);
  workspace.editContext('local_currency', 'USD');
  workspace.editContext('valuation_currency', 'USD');
  workspace.editAssumption('spot_fx_base_per_local', '1');
  workspace.editAssumption('terminal_fx_base_per_local', '1');
  workspace.editContext('valuation_currency', 'EUR');
  const draft = workspace.getSnapshot().draft;
  assert.equal(draft.assumptions.spot_fx_base_per_local, '');
  assert.equal(draft.assumptions.terminal_fx_base_per_local, '');
  assert.ok(Object.values(draft.scenarios).every(item => item.terminal_fx_base_per_local === ''));
});

test('edits invalidate a pending evaluation and never install stale output', async () => {
  let resolve;
  const workspace = createValuationWorkspace(async path => path.includes('evaluate') ? new Promise(done => { resolve = done; }) : []);
  await workspace.connect('secret');
  await workspace.selectSecurity('security');
  const pending = workspace.evaluate();
  workspace.edit('annualized_return', '0.1');
  resolve({ result: { kind: 'investor_view' }, manifest: {} });
  await pending;
  assert.equal(workspace.getSnapshot().output, null);
  assert.equal(workspace.getSnapshot().draft.annualized_return, '0.1');
});

test('disconnect and a new security reject stale private responses', async () => {
  let resolve;
  const workspace = createValuationWorkspace(async path => path.startsWith('/theses?') ? new Promise(done => { resolve = done; }) : []);
  await workspace.connect('secret');
  const pending = workspace.selectSecurity('old');
  workspace.disconnect();
  resolve([{ id: 'private-thesis' }]);
  await pending;
  assert.equal(workspace.getSnapshot().connected, false);
  assert.deepEqual(workspace.getSnapshot().theses, []);
  assert.equal(workspace.getSnapshot().securityId, '');
});

test('validation and network errors cannot expose echoed secrets or private input', async () => {
  await assert.rejects(valuationRequest('http://api/', 'secret', '/valuation/evaluate', {}, async () => ({ ok: false, status: 422, json: () => ({ detail: 'secret' }) })), error => !error.message.includes('secret') && error.message.includes('assumptions'));
  await assert.rejects(valuationRequest('http://api', 'secret', '/securities', {}, async () => { throw new Error('secret'); }), error => !error.message.includes('secret'));
});

test('CAPM requires an explicit sample and preserves rf and ERP inputs', () => {
  const draft = emptyDraft('USD');
  draft.model = 'capm';
  assert.throws(() => buildEvaluation(draft, 'security'), /sample/);
  draft.sample = '{"observations":[]}';
  draft.risk_free_rate = '0.03';
  draft.equity_risk_premium = '0.05';
  const body = buildEvaluation(draft, 'security');
  assert.equal(body.risk_free_rate, '0.03');
  assert.equal(body.equity_risk_premium, '0.05');
  assert.equal(body.horizon_assumption, 'iid_annual_gross_mean');
});

test('a previous owner connection cannot replace a newer connection', async () => {
  let resolveOld;
  const keys = [];
  const workspace = createValuationWorkspace(async (_path, _options, key) => {
    keys.push(key);
    return key === 'old-key' ? new Promise(resolve => { resolveOld = resolve; }) : [{ id: 'new-security', currency: 'USD' }];
  });
  const old = workspace.connect('old-key');
  await workspace.connect('new-key');
  resolveOld([{ id: 'private-old-security' }]);
  await old;
  assert.deepEqual(keys, ['old-key', 'new-key']);
  assert.equal(workspace.getSnapshot().securities[0].id, 'new-security');
});

test('switching security rejects late thesis records for the previous selection', async () => {
  let resolveOld;
  const workspace = createValuationWorkspace(async path => path.includes('security_id=old') ? new Promise(resolve => { resolveOld = resolve; }) : path.includes('security_id=new') ? [{ id: 'new-thesis' }] : []);
  await workspace.connect('key');
  const old = workspace.selectSecurity('old');
  await workspace.selectSecurity('new');
  resolveOld([{ id: 'old-thesis' }]);
  await old;
  assert.equal(workspace.getSnapshot().securityId, 'new');
  assert.deepEqual(workspace.getSnapshot().theses, [{ id: 'new-thesis' }]);
});

test('cutoff changes clear selected observations and reject late evidence', async () => {
  let resolveEvidence;
  const workspace = createValuationWorkspace(async path => path.includes('fundamentals') ? new Promise(resolve => { resolveEvidence = resolve; }) : []);
  await workspace.connect('key');
  await workspace.selectSecurity('security');
  workspace.editContext('as_of', '2026-01-01T00:00:00Z');
  const pending = workspace.loadEvidence();
  workspace.editContext('as_of', '2025-01-01T00:00:00Z');
  resolveEvidence({ items: [{ id: 'future-evidence' }] });
  await pending;
  assert.deepEqual(workspace.getSnapshot().evidence, []);
  workspace.toggleEvidence('old-evidence');
  workspace.editContext('known_at', '2025-01-01T00:00:00Z');
  assert.deepEqual(workspace.getSnapshot().draft.context.observation_ids, []);
});
