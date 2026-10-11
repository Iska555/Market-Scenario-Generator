import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { buildFactorEvidence, createPerformance, factorRequest, factorTemplate } from './performance.js';

const draft = { start: '2025-01-01', end: '2025-02-02', known_at: '2025-03-01T00:00:00Z', risk_free_rate: '0', confidence: '.95', max_mark_age_days: '3', include_factors: true, include_contribution: true, include_benchmark: false };
const evidence = JSON.stringify({ daily_marks: Array.from({ length: 33 }, (_, i) => ({ date: new Date(Date.parse(draft.start) + i * 86400000).toISOString().slice(0, 10), prices: [], fx: [] })), flow_marks: [] });
const identity = { model_id: 'reviewed-market', revision: 'v1', name: 'Synthetic research factors', provider: 'Reviewed synthetic source', methodology_reference: 'Explicit fixture', currency: 'GBP', currency_policy: 'already_in_portfolio_currency', calendar: 'UTC_calendar_daily', periods_per_year: 365, units: 'decimal_simple_return', risk_free_convention: 'period_effective_return', effective_from: draft.start, effective_to: draft.end, published_at: '2025-01-01T20:00:00Z', retrieved_at: draft.known_at, factors: [{ factor_id: 'market', name: 'Market', convention: 'excess_market_return', description: 'Reviewed synthetic excess factor' }] };
const factors = JSON.stringify({ identity, rows: [] });
const metric = (value, reason = null) => ({ value, reason, observations: 32 });
const result = { performance: { start: draft.start, end: draft.end, twr: metric(.15) }, contribution: { reconciliation: { within_tolerance: true } }, comparison: null, factors: JSON.parse(factors), factors_sha256: 'factor-evidence-hash', expected_intervals: 32, paired_intervals: 32, residual_degrees_of_freedom: 30, fit_reason: null, coefficients: { alpha: { coefficient: metric(.002), standard_error: metric(.0002), t_statistic: metric(10) }, market: { coefficient: metric(-1.5), standard_error: metric(.1), t_statistic: metric(-15) } }, statistics: { r_squared: metric(.9), adjusted_r_squared: metric(.89), residual_standard_deviation: metric(.001), scaled_condition_number: metric(1) }, daily: [], warnings: ['Historical coefficients are not forecasts.'] };
const accounting = async path => path === '/portfolios' ? [{ id: 'a', base_currency: 'GBP' }, { id: 'b', base_currency: 'USD' }] : { version: 4 };
const prepare = async store => { await store.connect('memory-private-key'); store.edit(draft); store.editEvidence(evidence); store.editFactors(factors); };
let server, components, inputs;
before(async () => { server = await createServer({ configFile: false, esbuild: { jsx: 'automatic' }, server: { middlewareMode: true } }); components = await server.ssrLoadModule('/src/features/performance/FactorResults.jsx'); inputs = await server.ssrLoadModule('/src/features/performance/FactorInputs.jsx'); });
after(async () => { await server?.close(); });

test('factor template has interval dates/currency and no selected model, factors or invented returns', () => {
  const template = factorTemplate(draft, 'GBP'); assert.equal(template.rows.length, 32); assert.equal(template.rows[0].date, '2025-01-02'); assert.equal(template.identity.currency, 'GBP'); assert.deepEqual(template.identity.factors, []); assert.equal(template.identity.model_id, ''); assert.ok(template.rows.every(row => row.risk_free_return === null && !Object.keys(row.factor_returns).length));
  assert.throws(() => buildFactorEvidence(draft, JSON.stringify(template)), /Review/);
  const complete = JSON.parse(factors); complete.rows = [{ date: '2025-01-02', risk_free_return: '-0.0001', factor_returns: { market: '0.02' } }]; assert.deepEqual(buildFactorEvidence(draft, JSON.stringify(complete)), complete);
  for (const change of [r => { r.rows[0].risk_free_return = .01; }, r => { r.rows[0].factor_returns.market = .01; }, r => { r.identity.units = 'percent'; }, r => { r.identity.risk_free_convention = 'annual_effective'; }, r => { r.rows[0].date = draft.start; }, r => { r.rows.push(r.rows[0]); }, r => { r.identity.factors[0].factor_id = 'alpha'; }]) { const invalid = structuredClone(complete); change(invalid); assert.throws(() => buildFactorEvidence(draft, JSON.stringify(invalid))); }
});

test('factor private transport preserves exact payload and no-store, sanitizes service errors', async () => {
  let captured; const body = { performance: {}, factors: JSON.parse(factors), include_contribution: true, benchmark: null };
  await factorRequest('http://local/', 'key', 'a', body, async (url, options) => { captured = { url, options }; return { ok: true, json: async () => result }; });
  assert.equal(captured.url, 'http://local/api/factors/portfolios/a/report'); assert.equal(captured.options.cache, 'no-store'); assert.equal(captured.options.headers['X-Research-Key'], 'key'); assert.deepEqual(JSON.parse(captured.options.body), body);
  await assert.rejects(factorRequest('local', 'key', 'a', body, async () => ({ ok: false, status: 422 })), error => !error.message.includes('private payload'));
});

test('single factor request supplies selected reports and every evidence edit clears coherent results', async () => {
  let calls = 0; const fail = async () => assert.fail('Unexpected separate report request');
  const store = createPerformance(accounting, fail, fail, fail, async (id, body) => { calls++; assert.equal(body.include_contribution, true); assert.equal(body.benchmark, null); return result; });
  await prepare(store); await store.run(); assert.equal(calls, 1); assert.equal(store.getSnapshot().report, result.performance); assert.equal(store.getSnapshot().regression, result); assert.equal(store.getSnapshot().contribution, result.contribution); assert.doesNotMatch(JSON.stringify(store.getSnapshot()), /memory-private-key/);
  for (const edit of [() => store.editFactors(factors), () => store.editEvidence(evidence), () => store.editBenchmark('{}'), () => store.edit({ risk_free_rate: '.03' })]) { await store.run(); edit(); assert.equal(store.getSnapshot().regression, null); assert.equal(store.getSnapshot().report, null); }
  await store.select('b'); assert.equal(store.getSnapshot().factorEvidence, ''); assert.equal(store.getSnapshot().comparison, null);
});

test('factor request embeds optional benchmark and contribution coherently', async () => {
  const benchmark = { identity: { benchmark_id: 'b', revision: 'v1', name: 'Reviewed comparator', provider: 'Synthetic', methodology_reference: 'Reviewed', currency: 'GBP', return_basis: 'net_total_return', hedging: 'unhedged', effective_from: draft.start, effective_to: draft.end, published_at: identity.published_at, retrieved_at: identity.retrieved_at, calendar: 'UTC_calendar_daily', periods_per_year: 365, currency_policy: 'already_in_portfolio_currency' }, levels: [] };
  const combined = { ...result, comparison: { benchmark } };
  const store = createPerformance(accounting, async () => {}, async () => {}, async () => {}, async (id, body) => { assert.deepEqual(body.benchmark, benchmark); return combined; });
  await prepare(store); store.edit({ include_benchmark: true }); store.editBenchmark(JSON.stringify(benchmark)); await store.run(); assert.equal(store.getSnapshot().comparison, combined.comparison); assert.equal(store.getSnapshot().regression, combined);
});

test('lock, edited evidence and late factor imports/results cannot restore private state', async () => {
  let resolve; const store = createPerformance(accounting, async () => {}, async () => {}, async () => {}, () => new Promise(done => { resolve = done; }));
  await prepare(store); let running = store.run(); store.editFactors(factors); resolve(result); await running; assert.equal(store.getSnapshot().regression, null);
  running = store.run(); store.disconnect(); resolve(result); await running; assert.equal(store.getSnapshot().regression, null); assert.equal(store.getSnapshot().factorEvidence, '');
  await prepare(store); const importing = store.importFactors(new Promise(done => { resolve = done; })); store.disconnect(); resolve(factors); await importing; assert.equal(store.getSnapshot().factorEvidence, '');
});

test('invalid input and stale ledger clear factor results with safe error messages', async () => {
  const store = createPerformance(accounting, async () => {}, async () => {}, async () => {}, async () => { throw Object.assign(new Error('private-secret'), { status: 409 }); });
  await prepare(store); await store.run(); assert.match(store.getSnapshot().error, /Reload/); assert.doesNotMatch(store.getSnapshot().error, /private-secret/); assert.equal(store.getSnapshot().regression, null);
  store.editFactors('invalid'); await store.run(); assert.match(store.getSnapshot().error, /reviewed factor evidence/);
});

test('factor results display alpha with inference context, signed betas, R² and sample units', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { result }));
  for (const phrase of ['Historical factor explanation', 'Daily alpha', '0.20 pp', '0.02 pp', '-1.50', '-15.00', 'HC3 standard error', 'R²', '0.9000', '32 of 32', '30 residual', 'not a forecast', 'serial correlation', 'factor-evidence-hash']) assert.ok(html.includes(phrase), phrase);
  assert.doesNotMatch(html, /NaN|Infinity|-1.50%|annualized alpha/);
  const gap = metric(null, 'incomplete_paired_coverage'), missing = { ...result, fit_reason: 'incomplete_paired_coverage', paired_intervals: 31, coefficients: { alpha: { coefficient: gap, standard_error: gap, t_statistic: gap } }, statistics: { r_squared: gap } };
  const undefinedHtml = renderToStaticMarkup(React.createElement(components.default, { result: missing })); assert.match(undefinedHtml, /Not defined/); assert.match(undefinedHtml, /No partial-window/);
});

test('factor inputs explicitly separate daily risk-free evidence from annual performance setting', () => {
  const html = renderToStaticMarkup(React.createElement(inputs.default, { state: { busy: '', draft, factorEvidence: '' }, workspace: {}, button: '', input: '' }));
  for (const phrase of ['Analyze reviewed historical factors', 'At least 30', 'No factor data is downloaded', 'separate from the annual rate', 'no selected factors or invented returns', 'Supplied factor evidence JSON']) assert.ok(html.includes(phrase));
});
