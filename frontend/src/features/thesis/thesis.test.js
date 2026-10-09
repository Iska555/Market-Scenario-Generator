import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildRevision, buildReview, emptyThesis, emptyReview, researchRequest, createWorkspace, displayDecimal } from './thesis.js';

test('draft requests preserve declared decimals and version concurrency without metadata', () => {
  const draft = { ...emptyThesis('USD'), status: 'draft', conviction: 'low', horizon_months: '24', target_low: '10.123456789', target_high: '12', required_return: '0.08', id: 'private-history' };
  const request = buildRevision(draft, 7);
  assert.equal(request.expected_revision, 7);
  assert.equal(request.target_low, '10.123456789');
  assert.equal(request.required_return, '0.08');
  assert.equal(request.horizon_months, 24);
  assert.equal(request.variant_perception, '');
  assert.equal(request.id, undefined);
});

test('review requires an explicit decision and validity answer and ties to viewed revision', () => {
  assert.throws(() => buildReview(emptyReview('USD'), 'revision-1'), /decision/i);
  assert.throws(() => buildReview({ ...emptyReview('USD'), decision: 'WATCH' }, 'revision-1'), /valid/i);
  const result = buildReview({ ...emptyReview('USD'), decision: 'EXIT', thesis_still_valid: 'false', updated_expected_return: '-0.2' }, 'old-revision');
  assert.equal(result.revision_id, 'old-revision');
  assert.equal(result.thesis_still_valid, false);
  assert.equal(result.updated_expected_return, '-0.2');
  assert.equal(result.current_price, null);
});

test('private request sends key only in header and hides server-reflected secrets in errors', async () => {
  let observed;
  const fetcher = async (url, options) => {
    observed = { url, options };
    return { ok: false, status: 401, json: async () => ({ detail: 'secret-owner-key' }) };
  };
  await assert.rejects(researchRequest('https://example.test', 'secret-owner-key', '/theses', {}, fetcher), /Private workspace key was not accepted/);
  assert.equal(observed.url, 'https://example.test/api/research/theses');
  assert.equal(observed.options.headers['X-Research-Key'], 'secret-owner-key');
  assert.equal(observed.options.cache, 'no-store');
});

test('disconnect invalidates late private connection responses', async () => {
  const pending = [];
  const workspace = createWorkspace((path) => new Promise(resolve => pending.push({ path, resolve })));
  const connecting = workspace.connect('key');
  workspace.disconnect();
  for (const item of pending) item.resolve([{ id: 'private' }]);
  await connecting;
  assert.equal(workspace.getSnapshot().connected, false);
  assert.deepEqual(workspace.getSnapshot().securities, []);
  assert.deepEqual(workspace.getSnapshot().prompts, []);
});

test('a later security selection wins when older response arrives last', async () => {
  const pending = [];
  const workspace = createWorkspace(async path => {
    if (path.startsWith('/securities') || path === '/theses/prompts') return [];
    return new Promise(resolve => pending.push({ path, resolve }));
  });
  await workspace.connect('key');
  const first = workspace.selectSecurity('first');
  const second = workspace.selectSecurity('second');
  pending[1].resolve([{ id: 'new' }]);
  await second;
  pending[0].resolve([{ id: 'stale' }]);
  await first;
  assert.equal(workspace.getSnapshot().securityId, 'second');
  assert.deepEqual(workspace.getSnapshot().theses, [{ id: 'new' }]);
});

test('conflict preserves editor and expected revision; browsing history does not replace draft', async () => {
  const latest = { ...emptyThesis('USD'), id: 'revision-2', revision: 2, status: 'draft', conviction: 'low', horizon_months: 12 };
  const workspace = createWorkspace(async (path, options) => {
    if (options?.method === 'POST') throw Object.assign(new Error('Reload latest'), { status: 409 });
    if (path === '/theses/thesis-1') return { id: 'thesis-1', latest };
    return [];
  });
  await workspace.connect('key');
  await workspace.selectThesis('thesis-1');
  workspace.editThesis('notes', 'unsaved research');
  workspace.viewRevision({ ...latest, id: 'revision-1', revision: 1 });
  await workspace.saveThesis();
  assert.equal(workspace.getSnapshot().draft.notes, 'unsaved research');
  assert.equal(workspace.getSnapshot().expectedRevision, 2);
  assert.equal(workspace.getSnapshot().viewed.revision, 1);
  assert.equal(workspace.getSnapshot().conflict, true);
});

test('saving a thesis preserves a pending review and its selected historical revision', async () => {
  const latest = { ...emptyThesis('USD'), id: 'revision-2', revision: 2, status: 'draft', conviction: 'low', horizon_months: 12 };
  const workspace = createWorkspace(async (path, options) => {
    if (options?.method === 'POST') return { ...latest, id: 'revision-3', revision: 3 };
    if (path === '/theses/thesis-1') return { id: 'thesis-1', latest };
    return [];
  });
  await workspace.connect('key');
  await workspace.selectThesis('thesis-1');
  workspace.viewRevision({ ...latest, id: 'revision-1', revision: 1 });
  workspace.editReview('what_changed', 'Pending review of original thesis');
  workspace.editReview('decision', 'WATCH');
  workspace.editThesis('notes', 'Updated research');
  await workspace.saveThesis();
  const state = workspace.getSnapshot();
  assert.equal(state.latest.revision, 3);
  assert.equal(state.viewed.revision, 1);
  assert.equal(state.review.what_changed, 'Pending review of original thesis');
  assert.equal(state.review.decision, 'WATCH');
  assert.equal(state.reviewDirty, true);
});

test('display strips insignificant decimal zeros without converting exact decimal strings', () => {
  assert.equal(displayDecimal('95.0000000000'), '95');
  assert.equal(displayDecimal('0.0800000000'), '0.08');
  assert.equal(displayDecimal('12345678901234567890.1234000000'), '12345678901234567890.1234');
  assert.equal(displayDecimal('-0.2000000000'), '-0.2');
  assert.equal(displayDecimal('100'), '100');
});

test('late reload cannot overwrite an edit made after reload started', async () => {
  let resolveReload;
  let reload = false;
  const latest = { ...emptyThesis('USD'), id: 'revision-2', revision: 2, status: 'draft', conviction: 'low', horizon_months: 12 };
  const workspace = createWorkspace(async path => {
    if (path === '/theses/thesis-1') return reload ? new Promise(resolve => { resolveReload = resolve; }) : { id: 'thesis-1', latest };
    return [];
  });
  await workspace.connect('key');
  await workspace.selectThesis('thesis-1');
  reload = true;
  const pending = workspace.reloadThesis();
  workspace.editThesis('notes', 'Typed after reload');
  resolveReload({ id: 'thesis-1', latest: { ...latest, revision: 3 } });
  await pending;
  assert.equal(workspace.getSnapshot().draft.notes, 'Typed after reload');
  assert.equal(workspace.getSnapshot().expectedRevision, 2);
});
