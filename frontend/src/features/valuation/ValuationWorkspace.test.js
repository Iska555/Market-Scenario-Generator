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
  components = await server.ssrLoadModule('/src/features/valuation/ValuationWorkspace.jsx');
});
after(async () => { await server?.close(); });
const context = { horizon_years: 3, return_basis: 'total', money_basis: 'nominal', valuation_currency: 'USD', currency_basis: 'local' };
const render = result => renderToStaticMarkup(React.createElement(components.ValuationResults, { output: { result, manifest: { schema: 'replay', inputs: 'inspectable' } } }));

test('workspace starts disconnected with a memory-only password field', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { apiUrl: 'http://localhost', isDark: false }));
  assert.doesNotMatch(html, /type="password"/);
  assert.match(html, /Unlock private workspace to continue/);
  assert.match(html, /memory only/);
  assert.match(html, /Valuation/);
});

test('scenario results show server rates with horizon currency basis and no forced probabilities', () => {
  const html = render({ kind: 'scenario_set', context, scenarios: ['bear', 'base', 'bull'].map(name => ({ name, probability: null, valuation: { context, returns: { annualized_return: 0.092, cumulative_return: 0.3 }, assumptions: {}, uncertainty: {} } })), probability_weighted_return: null });
  for (const value of ['bear', 'base', 'bull', '9.2%', '3-year horizon', 'USD', 'nominal', 'total return', 'No probabilities supplied', 'Run manifest']) assert.ok(html.includes(value), value);
  assert.ok(!html.includes('BUY'));
});

test('historical diagnostic is visibly distinct and undefined SE is not zero', () => {
  const html = render({ kind: 'historical_diagnostic', context, annualized_arithmetic_mean: { value: 0.08 }, annualized_mean_standard_error: { value: null, reason: 'At least two observations required' }, observation_count: 1, frequency: 'annual', periods_per_year: 1, window_start: '2025-01-01', window_end: '2026-01-01', uncertainty: {} });
  assert.match(html, /Historical estimate — not a forward forecast/);
  assert.match(html, /At least two observations required/);
  assert.ok(!html.includes('0.0%'));
  assert.match(html, /2025-01-01/);
});

test('undefined reverse result includes reason and held assumptions', () => {
  const html = render({ kind: 'reverse_valuation', context, required_terminal_multiple: { value: null, reason: 'No positive solution' }, required_return: { annualized_return: 0.1, cumulative_return: 0.331 }, held_fixed: { annual_per_share_growth: 0.04 } });
  assert.match(html, /No positive solution/);
  assert.match(html, /Held-fixed assumptions/);
  assert.match(html, /0.04/);
});

test('CAPM output is a model estimate and is not labeled an investor view', () => {
  const html = render({ kind: 'model_estimate', model: 'capm', context, returns: { annualized_return: 0.09, cumulative_return: 0.295029 }, input: { benchmark: 'MARKET' }, uncertainty: {} });
  assert.match(html, /CAPM model estimate/);
  assert.ok(!html.includes('Explicit expected-return view'));
  assert.match(html, /not automatically adopted/);
});
