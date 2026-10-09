import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildChartData,
  buildHistogramData,
  buildPercentileRows,
  buildPortfolioRequest,
  buildSingleRequest,
  assertV3Response,
  formatRatio,
  formatSignedPercent,
  normalizeWeightPercentages,
  DEFAULT_ASSUMPTIONS,
  estimationWindowPreset,
  yearsForEstimationWindow,
  MODEL_OPTIONS,
  driftModelLabel,
} from './scenarioContract.js';

test('frontend defaults to buy and hold without changing the v3 request fields', () => {
  assert.equal(DEFAULT_ASSUMPTIONS.rebalance, 'buy_and_hold');
  assert.equal(DEFAULT_ASSUMPTIONS.covarianceEstimator, 'ledoit_wolf');
  assert.equal(buildPortfolioRequest([{ ticker: 'SPY', weight: 50 }, { ticker: 'TLT', weight: 50 }], DEFAULT_ASSUMPTIONS).rebalance, 'buy_and_hold');
});

test('estimation presets retain their exact request years and custom input', () => {
  assert.deepEqual([3, 5, 10, 7].map(estimationWindowPreset), ['recent', 'medium', 'long', 'custom']);
  assert.equal(yearsForEstimationWindow('recent', 7), 3);
  assert.equal(yearsForEstimationWindow('medium', 7), 5);
  assert.equal(yearsForEstimationWindow('long', 7), 10);
  assert.equal(yearsForEstimationWindow('custom', 7), 7);
  assert.equal(buildSingleRequest('SPY', { ...DEFAULT_ASSUMPTIONS, years: yearsForEstimationWindow('custom', 7) }).years, 7);
});

test('model labels identify single and portfolio methods precisely', () => {
  assert.equal(MODEL_OPTIONS.find((option) => option.value === 'gmm').singleLabel, 'Univariate GMM');
  assert.equal(MODEL_OPTIONS.find((option) => option.value === 'gaussian').singleLabel, 'Gaussian single-asset model');
});

test('drift labels retain the chosen model without presenting history as a forecast', () => {
  assert.equal(driftModelLabel('zero_log_drift'), 'No directional return assumption');
  assert.equal(driftModelLabel('historical_diagnostic'), 'Historical average — diagnostic only');
});

const assumptions = {
  years: 3,
  horizon: 40,
  numPaths: 2000,
  model: 'gmm',
  randomSeed: 42,
  driftModel: 'zero_log_drift',
  riskFreeRate: 0.03,
  periodsPerYear: 252,
  confidence: 0.975,
  initialValue: 2500,
  currency: 'USD',
  covarianceEstimator: 'sample',
  gmmComponents: 4,
  gmmRegCovar: 0.00001,
  ewmaLambda: 0.91,
  rebalance: 'buy_and_hold',
};

test('single request sends the complete v3 assumption contract', () => {
  assert.deepEqual(buildSingleRequest(' spy ', assumptions), {
    ticker: 'SPY',
    years: 3,
    horizon: 40,
    num_paths: 2000,
    model: 'gmm',
    random_seed: 42,
    drift_model: 'zero_log_drift',
    risk_free_rate: 0.03,
    periods_per_year: 252,
    confidence: 0.975,
    initial_value: 2500,
    currency: 'USD',
    covariance_estimator: 'sample',
    gmm_components: 4,
    gmm_reg_covar: 0.00001,
    ewma_lambda: 0.91,
    rebalance: 'buy_and_hold',
  });
});

test('portfolio request converts percentage weights and rejects EWMA', () => {
  assert.deepEqual(
    buildPortfolioRequest(
      [{ ticker: 'spy', weight: '60' }, { ticker: 'tlt', weight: '40' }],
      { ...assumptions, model: 'gaussian' },
    ),
    {
      tickers: ['SPY', 'TLT'],
      weights: [0.6, 0.4],
      years: 3,
      horizon: 40,
      num_paths: 2000,
      model: 'gaussian',
      random_seed: 42,
      drift_model: 'zero_log_drift',
      risk_free_rate: 0.03,
      periods_per_year: 252,
      confidence: 0.975,
      initial_value: 2500,
      currency: 'USD',
      covariance_estimator: 'sample',
      gmm_components: 4,
      gmm_reg_covar: 0.00001,
      ewma_lambda: 0.91,
      rebalance: 'buy_and_hold',
    },
  );

  assert.throws(
    () => buildPortfolioRequest([{ ticker: 'SPY', weight: '100' }], { ...assumptions, model: 'ewma' }),
    /EWMA is available only for single-asset scenarios/,
  );
});

test('displayed percentile rows are unchanged by a misleading chart sample', () => {
  const response = {
    percentiles: { p01: -0.42, p05: -0.2, p10: -0.1, p25: 0.01, p50: 0.12, p75: 0.25, p90: 0.4, p95: 0.5, p99: 0.7 },
    percentile_values: { p01: 580, p05: 800, p10: 900, p25: 1010, p50: 1120, p75: 1250, p90: 1400, p95: 1500, p99: 1700 },
    paths_chart_sample: [[1000, 999999999]],
  };
  const first = buildPercentileRows(response);
  response.paths_chart_sample = [[1000, 1], [1000, 2]];

  assert.deepEqual(buildPercentileRows(response), first);
  assert.deepEqual(first.map((row) => row.returnValue), [-0.42, -0.2, -0.1, 0.01, 0.12, 0.25, 0.4, 0.5, 0.7]);
});

test('chart transformation preserves day zero and every server sample point', () => {
  assert.deepEqual(buildChartData([[1000, 1010, 1020], [1000, 980, 990]]), [
    { day: 0, path_0: 1000, path_1: 1000 },
    { day: 1, path_0: 1010, path_1: 980 },
    { day: 2, path_0: 1020, path_1: 990 },
  ]);
});

test('histogram presentation preserves server bins without rebucketing', () => {
  assert.deepEqual(buildHistogramData([
    { lower: -0.2, upper: -0.1, count: 7 },
    { lower: -0.1, upper: 0, count: 11 },
  ]), [
    { lower: -0.2, upper: -0.1, count: 7, bin: '-20.0% to -10.0%' },
    { lower: -0.1, upper: 0, count: 11, bin: '-10.0% to 0.0%' },
  ]);
});

test('null ratios and signed negative metrics remain explicit', () => {
  assert.equal(formatRatio(null), 'Unavailable');
  assert.equal(formatRatio(0), '0.00');
  assert.equal(formatSignedPercent(-0.0312), '-3.12%');
  assert.equal(formatSignedPercent(0.0312), '+3.12%');
});

test('normalizing three equal entries allocates the rounding residual exactly', () => {
  const normalized = normalizeWeightPercentages([
    { ticker: 'A', weight: '1' },
    { ticker: 'B', weight: '1' },
    { ticker: 'C', weight: '1' },
  ]);

  assert.deepEqual(normalized.map((asset) => asset.weight), ['33.34', '33.33', '33.33']);
  assert.equal(normalized.reduce((sum, asset) => sum + Number(asset.weight), 0), 100);
});

test('normalizing ten entries remains exactly one hundred percent', () => {
  const normalized = normalizeWeightPercentages(
    Array.from({ length: 10 }, (_, index) => ({ ticker: `T${index}`, weight: String(index + 1) })),
  );

  assert.equal(normalized.reduce((sum, asset) => sum + Number(asset.weight), 0), 100);
  assert.ok(normalized.every((asset) => Number(asset.weight) >= 0));
});

test('v3 response guard rejects stale or incomplete backend payloads', () => {
  const valid = { api_version: '3.0.0', statistics: {}, percentiles: {}, percentile_values: {} };
  assert.equal(assertV3Response(valid), valid);
  assert.throws(() => assertV3Response({ ...valid, api_version: '2.0.0' }), /requires API v3\.0\.0/);
  assert.throws(() => assertV3Response({ api_version: '3.0.0' }), /incomplete API v3\.0\.0/);
});

test('cleared assumptions and weights cannot silently become zero', () => {
  for (const field of ['riskFreeRate', 'randomSeed']) {
    assert.throws(() => buildSingleRequest('SPY', { ...assumptions, [field]: '' }), /required/);
  }
  assert.throws(() => buildPortfolioRequest([
    { ticker: 'SPY', weight: '100' }, { ticker: 'TLT', weight: '' },
  ], assumptions), /required/);
  const explicitZero = buildSingleRequest('SPY', { ...assumptions, riskFreeRate: '0', randomSeed: '0' });
  assert.equal(explicitZero.risk_free_rate, 0);
  assert.equal(explicitZero.random_seed, 0);
});
