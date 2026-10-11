import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { benchmarkTemplate, buildBenchmarkEvidence, comparisonRequest, createPerformance } from './performance.js';

const draft = { start: '2025-01-01', end: '2025-01-03', known_at: '2025-02-01T12:00:00Z', risk_free_rate: '0', confidence: '.95', max_mark_age_days: '3', include_benchmark: true, include_contribution: true };
const performanceEvidence = JSON.stringify({ daily_marks: ['2025-01-01', '2025-01-02', '2025-01-03'].map(date => ({ date, prices: [], fx: [] })), flow_marks: [] });
const identity = { benchmark_id: 'reviewed-benchmark', revision: 'v1', name: 'Reviewed total return', provider: 'Reviewed source', methodology_reference: 'Explicit fixture', currency: 'GBP', return_basis: 'net_total_return', hedging: 'unhedged', effective_from: draft.start, effective_to: draft.end, published_at: '2025-01-01T20:00:00Z', retrieved_at: draft.known_at, calendar: 'UTC_calendar_daily', periods_per_year: 365, currency_policy: 'already_in_portfolio_currency' };
const benchmarkEvidence = JSON.stringify({ identity, max_level_age_days: 0, levels: [] });
const metric = (value, reason = null) => ({ value, reason, observations: 2 });
const result = { performance: { twr: metric(.15) }, contribution: { reconciliation: { within_tolerance: true } }, benchmark: JSON.parse(benchmarkEvidence), benchmark_sha256: 'exact-evidence-hash', expected_intervals: 2, paired_intervals: 2, benchmark_return: metric(.1), cumulative_active_return: metric(.05), cumulative_relative_return: metric(1.15 / 1.1 - 1), statistics: { mean_daily_active_return: metric(.025), annualized_arithmetic_active_return: metric(9.125), annualized_tracking_error: metric(.1), information_ratio: metric(2), beta: metric(1.5), correlation: metric(.9) }, daily: [], warnings: ['Short sample; no alpha or skill inference.'] };
const accounting = async path => path === '/portfolios' ? [{ id: 'a', base_currency: 'GBP' }, { id: 'b', base_currency: 'USD' }] : { version: 4 };
const prepare = async store => { await store.connect('private-key-only-memory'); store.edit(draft); store.editEvidence(performanceEvidence); store.editBenchmark(benchmarkEvidence); };
let server, components, inputs;
before(async () => { server = await createServer({ configFile: false, esbuild: { jsx: 'automatic' }, server: { middlewareMode: true } }); components = await server.ssrLoadModule('/src/features/performance/BenchmarkResults.jsx'); inputs = await server.ssrLoadModule('/src/features/performance/BenchmarkInputs.jsx'); });
after(async () => { await server?.close(); });

test('benchmark template preserves dates/currency with no invented choice, level or timestamp', () => {
  const template = benchmarkTemplate(draft, 'GBP');
  assert.equal(template.identity.currency, 'GBP'); assert.equal(template.identity.benchmark_id, '');
  assert.equal(template.identity.return_basis, ''); assert.equal(template.levels.length, 3);
  assert.ok(template.levels.every(row => row.level === null && row.observed_at === ''));
  assert.throws(() => buildBenchmarkEvidence(draft, JSON.stringify(template)), /Review/);
  const complete = JSON.parse(benchmarkEvidence); complete.levels = [{ date: draft.start, level: '100' }, { date: draft.end, level: null }];
  assert.deepEqual(buildBenchmarkEvidence(draft, JSON.stringify(complete)), complete);
  for (const change of [r => { r.levels[0].level = 100; }, r => { r.identity.return_basis = 'price_return'; }, r => { r.identity.periods_per_year = 252; }, r => { r.levels[0].date = '2024-01-01'; }, r => { r.levels.push(r.levels[0]); }]) {
    const invalid = structuredClone(complete); change(invalid); assert.throws(() => buildBenchmarkEvidence(draft, JSON.stringify(invalid)));
  }
});

test('comparison transport keeps the exact private request and no-store policy', async () => {
  let captured;
  const body = { performance: { expected_version: 4 }, benchmark: JSON.parse(benchmarkEvidence), include_contribution: true };
  await comparisonRequest('http://local/', 'key', 'a', body, async (url, options) => { captured = { url, options }; return { ok: true, json: async () => result }; });
  assert.equal(captured.url, 'http://local/api/benchmark/portfolios/a/comparison');
  assert.equal(captured.options.cache, 'no-store'); assert.equal(captured.options.headers['X-Research-Key'], 'key');
  assert.deepEqual(JSON.parse(captured.options.body), body);
  await assert.rejects(comparisonRequest('local', 'k', 'a', body, async () => ({ ok: false, status: 422, json: () => ({ detail: 'private payload' }) })), error => !error.message.includes('private payload'));
});

test('one comparison supplies all results; inputs, options and account reload clear all', async () => {
  let comparisons = 0, other = 0, captured;
  const store = createPerformance(accounting, async () => { other++; }, async () => { other++; }, async (id, body) => { comparisons++; captured = body; return result; });
  await prepare(store); await store.run();
  assert.equal(comparisons, 1); assert.equal(other, 0); assert.equal(captured.include_contribution, true);
  assert.equal(store.getSnapshot().report, result.performance); assert.equal(store.getSnapshot().contribution, result.contribution); assert.equal(store.getSnapshot().comparison, result);
  assert.doesNotMatch(JSON.stringify(store.getSnapshot()), /private-key-only-memory/);
  store.editBenchmark(benchmarkEvidence); assert.equal(store.getSnapshot().comparison, null); assert.equal(store.getSnapshot().report, null); assert.equal(store.getSnapshot().contribution, null);
  await store.run(); store.edit({ include_benchmark: false }); assert.equal(store.getSnapshot().comparison, null);
  store.edit({ include_benchmark: true }); await store.run(); await store.select('b'); assert.equal(store.getSnapshot().benchmarkEvidence, ''); assert.equal(store.getSnapshot().comparison, null);
});

test('edited benchmark, lock and late file imports cannot restore stale private results', async () => {
  let resolve;
  const store = createPerformance(accounting, async () => {}, async () => {}, () => new Promise(done => { resolve = done; }));
  await prepare(store); let running = store.run(); store.editBenchmark(benchmarkEvidence); resolve(result); await running; assert.equal(store.getSnapshot().comparison, null);
  running = store.run(); store.disconnect(); resolve(result); await running; assert.equal(store.getSnapshot().comparison, null); assert.equal(store.getSnapshot().benchmarkEvidence, '');
  await prepare(store); const importing = store.importBenchmark(new Promise(done => { resolve = done; })); store.disconnect(); resolve(benchmarkEvidence); await importing;
  assert.equal(store.getSnapshot().benchmarkEvidence, ''); assert.equal(store.getSnapshot().connected, false);
});

test('stale ledger and invalid benchmark clear coherent results and expose only safe errors', async () => {
  let fail = false;
  const store = createPerformance(accounting, async () => {}, async () => {}, async () => { if (fail) throw Object.assign(new Error('secret payload'), { status: 409 }); return result; });
  await prepare(store); await store.run(); fail = true; await store.run();
  assert.equal(store.getSnapshot().comparison, null); assert.equal(store.getSnapshot().contribution, null); assert.equal(store.getSnapshot().report, null); assert.match(store.getSnapshot().error, /Reload/); assert.doesNotMatch(store.getSnapshot().error, /secret payload/);
  store.editBenchmark('invalid JSON'); await store.run(); assert.match(store.getSnapshot().error, /reviewed benchmark evidence/);
});

test('benchmark results distinguish percentages, active percentage points, ratios and provenance', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { result }));
  for (const phrase of ['How your portfolio compares', '10.00%', '5.00 pp', '1.50', 'revision', 'v1', '365', 'exact-evidence-hash', '2 of 2', 'tracking error', 'Short sample']) assert.ok(html.includes(phrase), phrase);
  assert.doesNotMatch(html, /NaN|Infinity|1.50%/);
});

test('missing comparative values show reasons rather than zero or complete coverage', () => {
  const gap = metric(null, 'incomplete_paired_coverage');
  const missing = { ...result, paired_intervals: 0, benchmark_return: gap, cumulative_active_return: gap, cumulative_relative_return: gap, statistics: Object.fromEntries(Object.keys(result.statistics).map(key => [key, gap])) };
  const html = renderToStaticMarkup(React.createElement(components.default, { result: missing }));
  assert.match(html, /Not defined/); assert.match(html, /incomplete paired coverage/); assert.match(html, /withheld/);
  assert.doesNotMatch(html, /0.00%|Complete paired coverage/);
});

test('benchmark input is an explicit optional selection with honest empty-template guidance', () => {
  const html = renderToStaticMarkup(React.createElement(inputs.default, { state: { busy: '', draft, benchmarkEvidence: '' }, workspace: {}, button: '', input: '' }));
  for (const phrase of ['Compare with a reviewed benchmark', 'no index or market data is selected automatically', 'no benchmark choice or invented level', 'Supplied benchmark evidence JSON', 'Prepare empty benchmark template']) assert.ok(html.includes(phrase));
  assert.doesNotMatch(html, /SPY|S&amp;P/);
});
