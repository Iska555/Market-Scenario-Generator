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
  components = await server.ssrLoadModule('/src/features/construction/ConstructionWorkspace.jsx');
});
after(async () => { await server?.close(); });

test('construction starts disconnected with memory-only credentials and an honest empty state', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { apiUrl: 'http://local', isDark: false }));
  assert.doesNotMatch(html, /type="password"/);
  assert.match(html, /Unlock private workspace to continue/);
  assert.match(html, /memory only/);
  assert.match(html, /Your research universe/);
  assert.doesNotMatch(html, /\$[0-9]/);
});
test('comparison shows unavailable strategies and violations without making them usable allocations', () => {
  const html = renderToStaticMarkup(React.createElement(components.ConstructionResults, { output: {
    result: { currency: 'USD', valuation_date: '2026-01-02', covariance: { estimator: 'sample', frequency: 'annual', periods_per_year: 1, observation_count: 2, window_start: '2024-01-01', window_end: '2026-01-01', shrinkage: 0 }, comparisons: [{ strategy: 'maximum_sharpe', status: 'unavailable', reason: 'Missing explicit views' }, { strategy: 'current', status: 'available', constraints_satisfied: false, constraint_violations: ['Position above maximum'], report: { current_covariance_volatility: 0.2, expected_portfolio_return: { value: null, reason: 'No adopted return view' }, expected_sharpe_ratio: { value: null, reason: 'No adopted return view' }, assets: [] } }] }, manifest: { evidence: [] },
  } }));
  assert.match(html, /Missing explicit views/);
  assert.match(html, /Position above maximum/);
  assert.match(html, /Undefined — No adopted return view/);
  assert.match(html, /USD/);
});
test('asset detail keeps signed risk distinct from weights and expected return contribution', () => {
  const html = renderToStaticMarkup(React.createElement(components.ContributionTable, { assets: [{ security_id: 'hedge', weight: 0.2, annualized_asset_volatility: 0.3, marginal_risk_contribution: { value: -0.075 }, component_risk_contribution: -0.015, percentage_risk_contribution: { value: -0.1 }, expected_return_assumption: { value: null, reason: 'No view' }, expected_return_contribution: { value: null, reason: 'No view' } }], evidence: [{ security: { id: 'hedge', ticker: 'HEDGE' } }] }));
  for (const text of ['20.00%', '-1.50%', '-10.00%', 'HEDGE', 'Expected return contribution', 'Undefined — No view']) assert.ok(html.includes(text), text);
});
