import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
let server;
let components;
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL('../../..', import.meta.url)), appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true } });
  components = await server.ssrLoadModule('/src/features/stress/StressWorkspace.jsx');
});
after(async () => { await server?.close(); });
test('stress workspace begins disconnected and has no fabricated positions', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { apiUrl: 'http://localhost', isDark: false }));
  assert.doesNotMatch(html, /type="password"/);
  assert.match(html, /Unlock private workspace to continue/);
  assert.match(html, /memory only/);
  assert.match(html, /Risk &amp; Scenario Lab/);
  assert.ok(!html.includes('AAPL'));
});
test('server stress results show undefined reasons, units, population and replay provenance', () => {
  const undefinedMetric = { value: null, reason: 'One scenario has no empirical tail distribution' };
  const result = { scenario_name: 'Explicit losses', interpretation: 'Conditional stress evidence, not a forecast', currency: 'USD', horizon_label: 'Immediate', population_size: 1, scenario_mean_terminal_return: -.5, scenario_mean_terminal_value: 50, scenario_max_drawdown_median: .5, scenario_max_drawdown_p95: .5, scenario_var: undefinedMetric, scenario_expected_shortfall: undefinedMetric, scenario_annualized_volatility: undefinedMetric, scenario_sharpe_ratio: undefinedMetric, scenario_sortino_ratio: undefinedMetric, scenario_calmar_ratio_median: undefinedMetric, calmar_defined_paths: 0, calmar_total_paths: 1, tail_effective_count: null, tail_confidence: null, methodology: ['Weighted simple security shocks'], uncertainty: 'Parameter uncertainty not propagated' };
  const html = renderToStaticMarkup(React.createElement(components.StressResults, { output: { result, manifest: { random_seed: null } } }));
  for (const value of ['−50', 'USD', 'Immediate', '1', 'One scenario has no empirical tail distribution', 'Run manifest', 'Weighted simple security shocks']) assert.ok(html.includes(value), value);
  assert.ok(!html.includes('BUY'));
});
