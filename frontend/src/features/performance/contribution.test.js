import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createPerformance, performanceRequest } from './performance.js';

const draft = { start: '2025-01-01', end: '2025-01-02', known_at: '2025-02-01T12:00:00Z', risk_free_rate: '0', confidence: '.95', max_mark_age_days: '3', include_contribution: true };
const evidence = JSON.stringify({ daily_marks: [{ date: draft.start, prices: [], fx: [] }, { date: draft.end, prices: [], fx: [] }], flow_marks: [] });
const accounting = async path => path === '/portfolios' ? [{ id: 'a' }, { id: 'b' }] : { version: 4 };
const value = (v, reason = null) => ({ value: v, reason });
const row = { key: 'security:a', kind: 'security', security_id: 'stable-equity-id', price: value('.2'), dividends: value('0'), fees: value('-.01'), fx: value('0'), total: value('.19'), pnl_base: '19' };
const result = { performance: { twr: { value: .19 } }, reconciliation: { component_total: value('.19'), residual: value('0'), tolerance: '0.00000000000119', within_tolerance: true }, components: [row], top_contributors: ['security:a'], bottom_contributors: [], segments: [], warnings: ['endpoint FX convention; closed equities retained'] };
let server, components;
before(async () => { server = await createServer({ configFile: false, esbuild: { jsx: 'automatic' }, server: { middlewareMode: true } }); components = await server.ssrLoadModule('/src/features/performance/ContributionResults.jsx'); });
after(async () => { await server?.close(); });

test('contribution endpoint uses private no-store transport and preserves exact input', async () => {
  let captured;
  await performanceRequest('http://local/', 'key-only-memory', 'a', { known_at: draft.known_at }, async (url, options) => { captured = { url, options }; return { ok: true, json: async () => result }; }, true);
  assert.equal(captured.url, 'http://local/api/attribution/portfolios/a/contribution');
  assert.equal(captured.options.cache, 'no-store');
  assert.equal(captured.options.headers['X-Research-Key'], 'key-only-memory');
});

test('one contribution request supplies both coherent results; edits and account changes clear both', async () => {
  let reports = 0, contributions = 0;
  const store = createPerformance(accounting, async () => { reports++; }, async () => { contributions++; return result; });
  await store.connect('private-key'); store.edit(draft); store.editEvidence(evidence); await store.run();
  assert.equal(reports, 0); assert.equal(contributions, 1);
  assert.equal(store.getSnapshot().report, result.performance); assert.equal(store.getSnapshot().contribution, result);
  assert.doesNotMatch(JSON.stringify(store.getSnapshot()), /private-key/);
  store.edit({ include_contribution: false }); assert.equal(store.getSnapshot().contribution, null); assert.equal(store.getSnapshot().report, null);
  store.edit({ include_contribution: true }); await store.run();
  await store.select('b'); assert.equal(store.getSnapshot().contribution, null);
});

test('lock and edited evidence discard late contribution responses', async () => {
  let resolve;
  const store = createPerformance(accounting, async () => {}, () => new Promise(done => { resolve = done; }));
  await store.connect('k'); store.edit(draft); store.editEvidence(evidence);
  let running = store.run(); store.editEvidence(evidence); resolve(result); await running;
  assert.equal(store.getSnapshot().contribution, null); assert.equal(store.getSnapshot().report, null);
  running = store.run(); store.disconnect(); resolve(result); await running;
  assert.equal(store.getSnapshot().contribution, null); assert.equal(store.getSnapshot().connected, false);
});

test('stale version failure clears both results and asks to reload', async () => {
  let fail = false;
  const store = createPerformance(accounting, async () => {}, async () => { if (fail) throw Object.assign(new Error('private payload'), { status: 409 }); return result; });
  await store.connect('k'); store.edit(draft); store.editEvidence(evidence); await store.run();
  fail = true; await store.run(); assert.equal(store.getSnapshot().contribution, null); assert.equal(store.getSnapshot().report, null);
  assert.match(store.getSnapshot().error, /Reload/); assert.doesNotMatch(store.getSnapshot().error, /private payload/);
});

test('contribution presentation distinguishes percentage points, security identity and exact residual', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { result }));
  for (const phrase of ['+19.000 pp', 'Reconciled to TWR', 'stable-equity-id', 'Top equity contributors', 'Residual', 'Net dividends', 'Fees', 'opening exposures', 'endpoint FX']) assert.ok(html.includes(phrase), phrase);
  assert.doesNotMatch(html, /NaN|Infinity|Benchmark/);
});

test('undefined contribution cannot masquerade as a zero or a reconciled result', () => {
  const missing = value(null, 'missing_contribution_fx:USD');
  const html = renderToStaticMarkup(React.createElement(components.default, { result: { ...result, top_contributors: [], components: [{ ...row, price: missing, dividends: missing, fees: missing, fx: missing, total: missing }], reconciliation: { component_total: missing, residual: missing, tolerance: null, within_tolerance: null } } }));
  assert.match(html, /Contribution not defined/); assert.match(html, /missing contribution fx:USD/);
  assert.doesNotMatch(html, /0\.000 pp|Reconciled to TWR/);
});
