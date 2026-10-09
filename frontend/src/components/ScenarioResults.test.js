import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';

import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';

import { buildPercentileRows } from '../scenarioContract.js';

let server;
let PercentileTable;
let PortfolioRisk;
let Statistics;
let ResultNotice;
let ResponseAssumptions;

before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL('../..', import.meta.url)),
    appType: 'custom',
    configLoader: 'native',
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
  ({ PercentileTable, PortfolioRisk, Statistics, ResultNotice, ResponseAssumptions } = await server.ssrLoadModule('/src/components/ScenarioResults.jsx'));
});

after(async () => {
  await server.close();
});

test('percentile table renders server percentiles independent of chart samples', () => {
  const response = {
    percentiles: { p01: -0.42, p05: -0.2, p10: -0.1, p25: 0.01, p50: 0.12, p75: 0.25, p90: 0.4, p95: 0.5, p99: 0.7 },
    percentile_values: { p01: 580, p05: 800, p10: 900, p25: 1010, p50: 1120, p75: 1250, p90: 1400, p95: 1500, p99: 1700 },
    paths_chart_sample: [[1000, 999999999]],
  };
  const render = () => renderToStaticMarkup(React.createElement(PercentileTable, {
    rows: buildPercentileRows(response),
    currency: 'USD',
    isDark: false,
  }));
  const firstMarkup = render();
  response.paths_chart_sample = [[1000, 1], [1000, 2]];

  assert.equal(render(), firstMarkup);
  assert.match(firstMarkup, /P01/);
  assert.match(firstMarkup, /-42\.00%/);
  assert.match(firstMarkup, /P99/);
  assert.match(firstMarkup, /\+70\.00%/);
});

test('portfolio risk table renders unavailable marginal risk and signed negative contributions', () => {
  const result = {
    tickers: ['HEDGE', 'CORE'],
    asset_stats: [
      {
        ticker: 'HEDGE',
        weight: 0.2,
        marginal_risk_contribution: null,
        component_risk_contribution: -0.015,
        risk_contribution_pct: -0.1,
      },
      {
        ticker: 'CORE',
        weight: 0.8,
        marginal_risk_contribution: 0.2,
        component_risk_contribution: 0.15,
        risk_contribution_pct: 1.1,
      },
    ],
    risk_decomposition: {
      annualized_volatility: 0.135,
      covariance_estimator: 'ledoit_wolf',
      shrinkage: 0.12,
      basis: 'historical_simple_returns_at_initial_weights',
    },
    correlation_matrix: {
      HEDGE: { HEDGE: 1, CORE: -0.25 },
      CORE: { HEDGE: -0.25, CORE: 1 },
    },
  };
  const markup = renderToStaticMarkup(React.createElement(PortfolioRisk, { result, isDark: false }));

  assert.match(markup, /Unavailable/);
  assert.match(markup, /-1\.50%/);
  assert.match(markup, /-10\.00%/);
  assert.match(markup, /Risk share/);
  assert.match(markup, /historical simple-return covariance at initial weights/);
});

test('statistics render null ratios and Calmar path coverage as unavailable', () => {
  const statistics = {
    conditional_scenario_return_mean: 0.02,
    annualized_return_median: 0.03,
    annualized_volatility: null,
    sharpe_ratio: null,
    sortino_ratio: null,
    calmar_ratio_median: null,
    calmar_defined_paths: 83,
    calmar_total_paths: 100,
    max_drawdown_median: 0.04,
    max_drawdown_p95: 0.12,
    prob_loss: 0.4,
    min_return: -0.2,
    max_return: 0.3,
  };
  const markup = renderToStaticMarkup(React.createElement(Statistics, {
    statistics,
    riskFreeRate: 0.015,
    isDark: false,
  }));

  assert.match(markup, /Sharpe ratio[\s\S]*Unavailable/);
  assert.match(markup, /Sortino ratio[\s\S]*Unavailable/);
  assert.match(markup, /Unavailable \(83\/100 paths defined\)/);
  assert.match(markup, /risk-free rate of \+1\.50%/);
});

test('completed results identify their captured instruments independently of editable inputs', () => {
  const common = {
    message: 'Conditional scenarios under stated assumptions; not a forecast.',
    estimation_start: '2024-01-02',
    estimation_end: '2025-01-02',
    valuation_date: '2025-01-02',
    estimation_observations: 252,
    excluded_interval_count: 0,
    api_version: '3.0.0',
  };
  const single = renderToStaticMarkup(React.createElement(ResultNotice, {
    result: { ...common, ticker: 'SPY' }, isDark: false,
  }));
  const portfolio = renderToStaticMarkup(React.createElement(ResultNotice, {
    result: { ...common, tickers: ['SPY', 'TLT'] }, isDark: false,
  }));
  assert.match(single, /Instrument: SPY/);
  assert.match(portfolio, /Instruments: SPY, TLT/);
});

test('result assumptions disclose the forward return choice in plain language', () => {
  const html = renderToStaticMarkup(React.createElement(ResponseAssumptions, {
    result: { model: 'gaussian', assumptions: {
      years: 3, horizon: 252, num_paths: 1000, random_seed: 42,
      drift_model: 'historical_diagnostic', risk_free_rate: 0,
      periods_per_year: 252, confidence: 0.95, initial_value: 1000,
      currency: 'USD', covariance_estimator: 'ledoit_wolf',
      rebalance: 'buy_and_hold', gmm_components: 3, gmm_reg_covar: 0.000001,
      ewma_lambda: 0.94,
    } }, isDark: false,
  }));
  assert.ok(html.includes('Forward return assumption'));
  assert.ok(html.includes('Historical average — diagnostic only'));
  assert.ok(!html.includes('>historical_diagnostic<'));
});

test('result assumptions identify single and joint GMM without changing model codes', () => {
  const assumptions = { years: 3, horizon: 252, num_paths: 1000,
    random_seed: 42, drift_model: 'zero_log_drift', risk_free_rate: 0,
    periods_per_year: 252, confidence: 0.95, initial_value: 1000,
    currency: 'USD', covariance_estimator: 'ledoit_wolf',
    rebalance: 'buy_and_hold', gmm_components: 3, gmm_reg_covar: 0.000001,
    ewma_lambda: 0.94 };
  const single = renderToStaticMarkup(React.createElement(ResponseAssumptions, {
    result: { model: 'gmm', ticker: 'SPY', assumptions }, isDark: false,
  }));
  const portfolio = renderToStaticMarkup(React.createElement(ResponseAssumptions, {
    result: { model: 'gmm', tickers: ['SPY', 'TLT'], assumptions }, isDark: false,
  }));
  assert.ok(single.includes('Univariate GMM'));
  assert.ok(portfolio.includes('Joint GMM'));
});
