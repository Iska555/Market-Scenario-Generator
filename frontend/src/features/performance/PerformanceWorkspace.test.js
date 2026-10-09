import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
let server, components;
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL('../../..', import.meta.url)), appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true } });
  components = await server.ssrLoadModule('/src/features/performance/PerformanceWorkspace.jsx');
});
after(async () => { await server?.close(); });

test('locked performance page uses shared unlock and explains supplied evidence without invented results', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { apiUrl: '', isDark: false }));
  assert.match(html, /Unlock private workspace above/);
  assert.match(html, /Time-weighted return/);
  assert.match(html, /Money-weighted return/);
  assert.match(html, /unadjusted/);
  assert.doesNotMatch(html, /type="password"|0\.00%|broker connected/i);
});

test('performance results preserve decimal history and typed missing reasons with replay download', () => {
  const report = { start: '2026-01-01', end: '2026-01-02', scope: 'selected_period', base_currency: 'GBP', twr: { value: .1, reason: null, observations: 1 }, xirr: { value: null, reason: 'non_conventional_cash_flows', observations: 2 }, daily: [{ date: '2026-01-01', nav: '100.00000000000001', units: '100', unit_value: '1', daily_return: { value: null, reason: 'opening_baseline', observations: 0 }, cumulative_return: { value: 0, observations: 0 }, reason: null }], linked: { monthly: [{ label: '2026-01', start: '2026-01-01', end: '2026-01-02', partial: true, return_value: { value: .1, observations: 1 } }] }, statistics: { annualized_return: { value: null, reason: 'less_than_one_year', observations: 1 }, sharpe: { value: null, reason: 'insufficient_observations', observations: 1 } }, external_flows: [], warnings: ['short_sample'], manifest: { ledger_version: 7, inputs: { known_at: '2026-01-03T12:00:00Z' } } };
  const html = renderToStaticMarkup(React.createElement(components.PerformanceResults, { report }));
  for (const value of ['10.00%', '100.00000000000001', 'Non conventional cash flows', 'Less than one year', 'Partial period', 'Short sample', 'Download replay JSON', 'Ledger version 7']) assert.ok(html.includes(value), value);
  assert.doesNotMatch(html, /NaN|Infinity|Benchmark/);
  const ordered = renderToStaticMarkup(React.createElement(components.PerformanceResults, { report: { ...report, linked: { daily: [], ...report.linked } } }));
  assert.match(ordered, /value="monthly" selected=""/);
});
