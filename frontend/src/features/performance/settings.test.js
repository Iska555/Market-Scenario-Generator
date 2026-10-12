import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createPerformance, benchmarkSettingsRequest } from './performance.js';

const identity = { benchmark_id: 'reviewed', revision: 'v1', name: 'Reviewed fixture', provider: 'manual', methodology_reference: 'fixture', currency: 'GBP', return_basis: 'net_total_return', hedging: 'unhedged', effective_from: '2025-01-01', effective_to: '2025-12-31', published_at: '2025-01-01T20:00:00Z', retrieved_at: '2025-02-01T00:00:00Z', calendar: 'UTC_calendar_daily', periods_per_year: 365, currency_policy: 'already_in_portfolio_currency' };
const first = { id: 'saved-id', portfolio_id: 'a', revision: 1, identity, recorded_at: '2025-02-02T00:00:00Z', reason: 'Reviewed choice' };
const history = { revision: 1, total: 1, latest: first, records: [first] };
const accounting = async path => path === '/portfolios' ? [{ id: 'a', base_currency: 'GBP' }, { id: 'b', base_currency: 'USD' }] : { version: 1 };
const draft = { start: '2025-01-01', end: '2025-01-03', known_at: '2025-03-01T00:00:00Z', risk_free_rate: '0', confidence: '.95', max_mark_age_days: '3' };
const marks = JSON.stringify({ daily_marks: [draft.start, '2025-01-02', draft.end].map(date => ({ date, prices: [], fx: [] })), flow_marks: [] });
let server, component;
before(async () => { server = await createServer({ configFile: false, esbuild: { jsx: 'automatic' }, server: { middlewareMode: true } }); component = await server.ssrLoadModule('/src/features/performance/BenchmarkSettings.jsx'); });
after(async () => { await server?.close(); });

test('private settings transport uses explicit GET/POST and sanitizes errors', async () => {
  const calls = [];
  const fetcher = async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => history }; };
  await benchmarkSettingsRequest('http://local/', 'private-memory-key', 'a', null, fetcher);
  await benchmarkSettingsRequest('http://local/', 'private-memory-key', 'a', { expected_revision: 1 }, fetcher);
  assert.equal(calls[0].url, 'http://local/api/benchmark/portfolios/a/settings');
  assert.equal(calls[0].options.method, 'GET'); assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[1].options.method, 'POST'); assert.deepEqual(JSON.parse(calls[1].options.body), { expected_revision: 1 });
  await assert.rejects(benchmarkSettingsRequest('local', 'k', 'a', null, async () => ({ ok: false, status: 409 })), /Reload/);
  await assert.rejects(benchmarkSettingsRequest('local', 'k', 'a', null, async () => { throw new Error('private error'); }), /could not be reached/);
});

test('saved choice loads privately, stays opt-in, templates empty levels and links reviewed evidence', async () => {
  let sent;
  const store = createPerformance(accounting, async () => {}, null, async (id, body) => { sent = body; return { performance: {}, selection: first }; }, null, async () => history);
  await store.connect('private-memory-key');
  assert.equal(store.getSnapshot().settings.latest, first); assert.equal(store.getSnapshot().draft.include_benchmark, false);
  store.edit(draft); store.editEvidence(marks); store.useSavedBenchmark();
  const template = JSON.parse(store.getSnapshot().benchmarkEvidence);
  assert.deepEqual(template.identity, identity); assert.ok(template.levels.every(row => row.level === null));
  assert.equal(store.getSnapshot().savedBenchmarkRevision, 1);
  store.editBenchmark(JSON.stringify(template)); assert.equal(store.getSnapshot().savedBenchmarkRevision, null);
  store.linkSavedBenchmark(); assert.equal(store.getSnapshot().savedBenchmarkRevision, 1);
  await store.run(); assert.equal(sent.saved_benchmark_revision, 1);
  template.identity.name = 'Other'; store.editBenchmark(JSON.stringify(template)); store.linkSavedBenchmark();
  assert.match(store.getSnapshot().error, /differs/); assert.equal(store.getSnapshot().savedBenchmarkRevision, null);
  assert.doesNotMatch(JSON.stringify(store.getSnapshot()), /private-memory-key/);
});

test('save and clear retain retry ID across uncertain writes, reload current history and clear old evidence', async () => {
  let fail = true, bodies = [], current = history;
  const settings = async (id, body) => { if (!body) return current; bodies.push(body); if (fail) throw new Error('connection lost'); const saved = { ...first, id: body.id, revision: 2, identity: body.identity, reason: body.reason }; current = { revision: 2, total: 2, latest: saved, records: [saved, first] }; return saved; };
  const store = createPerformance(accounting, null, null, null, null, settings);
  await store.connect('key'); store.edit(draft); store.useSavedBenchmark();
  store.editSetting({ settingIdentity: JSON.stringify(identity), settingReason: 'Updated review' });
  await store.saveSetting(); assert.ok(store.getSnapshot().settingPending.id);
  fail = false; await store.saveSetting(); assert.equal(bodies[0].id, bodies[1].id);
  assert.equal(store.getSnapshot().settings.revision, 2); assert.equal(store.getSnapshot().benchmarkEvidence, ''); assert.equal(store.getSnapshot().savedBenchmarkRevision, null);
  store.editSetting({ settingReason: 'Clear choice' }); await store.saveSetting(true);
  assert.equal(bodies.at(-1).identity, null); assert.equal(store.getSnapshot().settings.latest.identity, null);
});

test('late settings reads and writes cannot repopulate lock/account state', async () => {
  let resolve;
  let settings = async () => history;
  const store = createPerformance(accounting, null, null, null, null, (...args) => settings(...args));
  await store.connect('key'); settings = () => new Promise(done => { resolve = done; });
  let running = store.reloadSettings(); store.disconnect(); resolve(history); await running;
  assert.equal(store.getSnapshot().settings, null);
  settings = async () => history; await store.connect('key'); store.editSetting({ settingIdentity: JSON.stringify(identity), settingReason: 'Save' });
  settings = () => new Promise(done => { resolve = done; }); running = store.saveSetting(); store.disconnect(); resolve(first); await running;
  assert.equal(store.getSnapshot().settings, null); assert.equal(store.getSnapshot().settingPending, null);
  settings = async () => history; await store.connect('key'); await store.select('b');
  assert.equal(store.getSnapshot().settingIdentity, ''); assert.equal(store.getSnapshot().savedBenchmarkRevision, null);
});

test('saved template rejects uncovered window and settings recorded after cutoff', async () => {
  const store = createPerformance(accounting, null, null, null, null, async () => history);
  await store.connect('key'); store.edit({ ...draft, end: '2026-01-01' }); store.useSavedBenchmark(); assert.match(store.getSnapshot().error, /cover/);
  store.edit({ ...draft, known_at: '2025-02-01T00:00:00Z' }); store.useSavedBenchmark(); assert.match(store.getSnapshot().error, /cutoff/);
  await store.saveSetting(); assert.match(store.getSnapshot().error, /Explain why/);
});

test('settings view exposes permanence, reasons, explicit selection and recent history', () => {
  const html = renderToStaticMarkup(React.createElement(component.default, { state: { busy: '', settings: history, draft, settingReason: '', settingIdentity: '' }, workspace: {}, button: '', input: '' }));
  for (const text of ['Portfolio benchmark setting', 'permanent revision', 'Saving does not enable comparison', 'Saved revision 1', 'Reason for saving or clearing', 'Recent setting history', 'Reviewed choice', 'Link reviewed evidence to saved revision']) assert.ok(html.includes(text), text);
  assert.doesNotMatch(html, /SPY|S&amp;P/);
});
