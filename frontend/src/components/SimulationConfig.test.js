import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server;
let SimulationConfig;

before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL('../..', import.meta.url)),
    appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true },
  });
  ({ default: SimulationConfig } = await server.ssrLoadModule('/src/components/SimulationConfig.jsx'));
});

after(async () => { await server?.close(); });

const baseAssumptions = {
  years: 3, horizon: 252, numPaths: 1000, model: 'gaussian', randomSeed: 42,
  driftModel: 'zero_log_drift', riskFreeRate: 0, periodsPerYear: 252,
  confidence: 0.95, initialValue: 1000, currency: 'USD',
  covarianceEstimator: 'ledoit_wolf', gmmComponents: 3, gmmRegCovar: 0.000001,
  ewmaLambda: 0.94, rebalance: 'buy_and_hold',
};

function render(mode, overrides = {}, props = {}) {
  return renderToStaticMarkup(React.createElement(SimulationConfig, {
    mode, ticker: 'SPY', setTicker: () => {},
    assets: [{ ticker: 'SPY', weight: 60 }, { ticker: 'TLT', weight: 40 }],
    setAssets: () => {}, updateAsset: () => {}, totalWeight: 100,
    normalizeWeights: () => {}, assumptions: { ...baseAssumptions, ...overrides },
    setAssumptions: () => {}, onRun: () => {}, loading: false, isDark: false, ...props,
  }));
}

test('single form shows ordinary decisions and advanced disclosure without portfolio selectors', () => {
  const html = render('single');
  for (const label of ['Estimation window', 'Horizon', 'Scenario family', 'Forward return assumption', 'Valuation currency', 'Initial value', 'Advanced settings', 'Simulation paths', 'Random seed', 'Periods per year', 'Confidence', 'Annual effective risk-free rate']) {
    assert.ok(html.includes(label), label);
  }
  assert.ok(!html.includes('Covariance estimator'));
  assert.ok(!html.includes('Rebalancing'));
  assert.ok(html.includes('Gaussian single-asset model'));
  assert.ok(html.includes('One fitted return distribution with a fixed volatility estimate.'));
  assert.ok(html.includes('Univariate GMM'));
  assert.ok(html.includes('No directional return assumption'));
  assert.ok(html.includes('Historical average — diagnostic only'));
  assert.ok(!html.includes('saved investor view'));
  assert.ok(html.includes('zero expected simple return'));
  assert.ok(html.includes('risk-neutral'));
});

test('portfolio form keeps covariance and rebalancing in advanced settings', () => {
  const html = render('portfolio');
  assert.ok(html.indexOf('Weight policy: Buy and hold') < html.indexOf('<details'));
  assert.ok(html.includes('Weight policy: Buy and hold'));
  assert.match(html, /<details[^>]*>[\s\S]*Covariance estimator[\s\S]*Rebalancing[\s\S]*<\/details>/);
  assert.ok(html.includes('Ledoit-Wolf'));
  assert.ok(html.includes('recommended default'));
  assert.ok(html.includes('Buy and hold'));
  assert.ok(!html.includes('EWMA recent'));
});

test('custom year value stays visible and model-specific parameters stay in details', () => {
  const html = render('single', { years: 7, model: 'gmm' });
  assert.match(html, /Custom[\s\S]*value="7"/);
  assert.match(html, /<details[^>]*>[\s\S]*GMM components[\s\S]*GMM covariance regularizer[\s\S]*<\/details>/);
  const ewma = render('single', { model: 'ewma' });
  assert.match(ewma, /<details[^>]*>[\s\S]*EWMA lambda[\s\S]*<\/details>/);
});

test('capacity stays secondary at ordinary size and explains disabled oversized requests', () => {
  const normal = render('portfolio');
  assert.ok(normal.includes('Request capacity'));
  const oversized = render('portfolio', { numPaths: 5000, horizon: 1000 });
  assert.ok(oversized.includes('Reduce paths, horizon, or asset count'));
  assert.match(oversized, /disabled=""/);
});


test('locked visitors see an unlock action and cannot submit a simulation', () => {
  const html = render('portfolio', {}, { connected: false, onUnlock: () => {} });
  assert.match(html, /Simulations require owner access/);
  assert.match(html, /Unlock private workspace/);
  assert.match(html, /disabled=""[^>]*>[\s\S]*Run conditional scenarios/);
});
