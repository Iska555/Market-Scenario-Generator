import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { createPerformance } from './performance.js';
import { emptySource, sourceBody, sourceReviewRequest } from './sourceReview.js';

const source = { csv: 'native-source-text', retrieved: '2026-10-12T14:48:51Z', published: '', publicationNote: '', note: 'Actual source reviewed' };
const draft = { start: '1990-07-02', end: '1990-07-09' };
const result = { selected_rows: 6, total_source_rows: 6, native_currency: 'USD', database_vintage: '202608', missing_cells: 1, source_first: draft.start, source_last: draft.end, calendar_gaps: [{ absent_calendar_dates: 2 }], blockers: ['source_currency_differs_from_account_currency', 'historical_publication_availability_unknown'], rows: [{ date: draft.start, returns: { 'Mkt-RF': '0.0069', SMB: '-0.0008', HML: null, RMW: '0.0021', CMA: '0', RF: '0.0003' } }], submitted_text_sha256: 'retained-text-hash' };
const accounting = async path => path === '/portfolios' ? [{ id: 'a', base_currency: 'GBP' }, { id: 'b', base_currency: 'USD' }] : { version: 1 };
const prepare = async request => { const store = createPerformance(accounting, async () => {}, null, null, null, null, request); await store.connect('private-key'); store.edit(draft); store.editSource(source); return store; };
let server, Component;
before(async () => { server = await createServer({ configFile: false, esbuild: { jsx: 'automatic' }, server: { middlewareMode: true } }); Component = (await server.ssrLoadModule('/src/features/performance/FactorSourceReview.jsx')).default; });
after(async () => { await server?.close(); });

test('source payload preserves exact text, unknown publication and requires explicit metadata', () => {
  assert.deepEqual(emptySource(), { csv: '', retrieved: '', published: '', publicationNote: '', note: '' });
  const body = sourceBody({ ...source, csv: '\ufeff text\r\n' }, draft);
  assert.equal(body.csv_text, '\ufeff text\r\n'); assert.equal(body.metadata.published_at, null); assert.equal(body.start, draft.start);
  for (const patch of [{ csv: '' }, { csv: 'é'.repeat(1000001) }, { retrieved: '' }, { retrieved: '2026-01-01T00:00:00' }, { published: 'invalid' }, { note: '' }, { published: '2026-01-01T00:00:00Z' }]) assert.throws(() => sourceBody({ ...source, ...patch }, draft));
  assert.throws(() => sourceBody(source, { start: '', end: '' }));
});

test('source transport is private no-store and sanitizes failures', async () => {
  let captured;
  await sourceReviewRequest('http://local/', 'key', 'a', sourceBody(source, draft), async (url, options) => { captured = { url, options }; return { ok: true, json: async () => result }; });
  assert.equal(captured.url, 'http://local/api/factors/portfolios/a/source-review'); assert.equal(captured.options.cache, 'no-store'); assert.equal(captured.options.headers['X-Research-Key'], 'key');
  await assert.rejects(sourceReviewRequest('local', 'key', 'a', {}, async () => ({ ok: false, status: 422 })), error => error.status === 422);
  await assert.rejects(sourceReviewRequest('local', 'key', 'a', {}, async () => { throw new Error('private-secret'); }), error => !error.message.includes('private-secret'));
});

test('source review never populates factor evidence or activates regression and edits clear receipt', async () => {
  const store = await prepare(async (id, body, key) => { assert.equal(id, 'a'); assert.equal(key, 'private-key'); assert.equal(body.metadata.published_at, null); return result; });
  await store.reviewSource(); assert.equal(store.getSnapshot().sourceReview, result); assert.equal(store.getSnapshot().factorEvidence, ''); assert.equal(store.getSnapshot().draft.include_factors, false);
  assert.doesNotMatch(JSON.stringify(store.getSnapshot()), /private-key/);
  store.edit({ start: '1990-07-03' }); assert.equal(store.getSnapshot().sourceReview, null);
  await store.reviewSource(); store.editSource({ note: 'changed' }); assert.equal(store.getSnapshot().sourceReview, null);
  await store.select('b'); assert.deepEqual(store.getSnapshot().sourceDraft, emptySource()); assert.equal(store.getSnapshot().sourceReview, null);
});

test('late source reads and responses cannot restore private state after lock, edits or account switch', async () => {
  let resolve;
  const store = await prepare(() => new Promise(done => { resolve = done; }));
  let pending = store.reviewSource(); store.editSource({ note: 'new review' }); resolve(result); await pending; assert.equal(store.getSnapshot().sourceReview, null);
  pending = store.reviewSource(); await store.select('b'); resolve(result); await pending; assert.equal(store.getSnapshot().sourceReview, null);
  store.editSource(source); pending = store.reviewSource(); store.disconnect(); resolve(result); await pending; assert.deepEqual(store.getSnapshot().sourceDraft, emptySource());
  await store.connect('key'); pending = store.importSource(new Promise(done => { resolve = done; })); store.disconnect(); resolve('private CSV'); await pending; assert.equal(store.getSnapshot().sourceDraft.csv, '');
});

test('source import resets provenance and invalid responses remain sanitized', async () => {
  const store = await prepare(async () => { throw Object.assign(new Error('private-secret'), { status: 422 }); });
  await store.importSource(Promise.resolve(source.csv)); assert.equal(store.getSnapshot().sourceDraft.retrieved, '');
  await store.reviewSource(); assert.match(store.getSnapshot().error, /timestamps/);
  store.editSource(source); await store.reviewSource(); assert.match(store.getSnapshot().error, /source format/); assert.doesNotMatch(store.getSnapshot().error, /private-secret/);
  await store.importSource(Promise.reject(new Error('secret'))); assert.match(store.getSnapshot().error, /could not be read/);
});

test('source UI distinguishes native rows, unknown publication, missing values and alignment blockers', () => {
  const html = renderToStaticMarkup(React.createElement(Component, { state: { sourceDraft: source, sourceReview: result }, workspace: {}, button: '', input: '' }));
  for (const phrase of ['alignment required', 'USD', '1990-07-02', '6 selected rows', 'Missing', '-0.0008', 'Publication timestamp (optional)', 'Historical publication availability is unknown', 'retained-text-hash', 'Download source review', 'not confirmed missing trading observations']) assert.ok(html.includes(phrase), phrase);
  assert.doesNotMatch(html, /NaN|Infinity|Use for regression/);
});
