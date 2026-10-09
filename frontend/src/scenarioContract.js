export const DEFAULT_ASSUMPTIONS = Object.freeze({
  years: 3,
  horizon: 252,
  numPaths: 1000,
  model: 'gaussian',
  randomSeed: 42,
  driftModel: 'zero_log_drift',
  riskFreeRate: 0,
  periodsPerYear: 252,
  confidence: 0.95,
  initialValue: 1000,
  currency: 'USD',
  covarianceEstimator: 'ledoit_wolf',
  gmmComponents: 3,
  gmmRegCovar: 0.000001,
  ewmaLambda: 0.94,
  rebalance: 'buy_and_hold',
});

export const MODEL_OPTIONS = Object.freeze([
  { value: 'gaussian', label: 'Multivariate Gaussian', singleLabel: 'Gaussian single-asset model', singleDescription: 'One fitted return distribution with a fixed volatility estimate.', description: 'One fitted return distribution with a fixed volatility and correlation structure.' },
  { value: 'gmm', label: 'Joint GMM', singleLabel: 'Univariate GMM', singleDescription: 'A mixture of return regimes with different volatility. Components are statistical regimes, not guaranteed economic states.', description: 'A mixture of return regimes with different volatility and correlation structures. Components are statistical regimes, not guaranteed economic states.' },
  { value: 'ewma', label: 'EWMA', singleLabel: 'EWMA recent-weighted volatility', description: 'Gives recent observations more weight so conditional volatility responds more quickly to recent market moves.' },
]);

export function estimationWindowPreset(years) {
  if (Number(years) === 3) return 'recent';
  if (Number(years) === 5) return 'medium';
  if (Number(years) === 10) return 'long';
  return 'custom';
}

export function yearsForEstimationWindow(preset, currentYears) {
  if (preset === 'recent') return 3;
  if (preset === 'medium') return 5;
  if (preset === 'long') return 10;
  if (preset === 'custom') return currentYears;
  throw new Error('Unknown estimation window preset.');
}

const PERCENTILE_KEYS = Object.freeze(['p01', 'p05', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99']);

function requiredNumber(value, label) {
  if (value === null || value === undefined || String(value).trim() === '') {
    throw new Error(`${label} is required; enter zero explicitly when intended.`);
  }
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${label} must be a finite number.`);
  return number;
}

function buildCommonRequest(assumptions) {
  return {
    years: requiredNumber(assumptions.years, 'History'),
    horizon: requiredNumber(assumptions.horizon, 'Horizon'),
    num_paths: requiredNumber(assumptions.numPaths, 'Simulation paths'),
    model: assumptions.model,
    random_seed: requiredNumber(assumptions.randomSeed, 'Random seed'),
    drift_model: assumptions.driftModel,
    risk_free_rate: requiredNumber(assumptions.riskFreeRate, 'Risk-free rate'),
    periods_per_year: requiredNumber(assumptions.periodsPerYear, 'Periods per year'),
    confidence: requiredNumber(assumptions.confidence, 'Confidence'),
    initial_value: requiredNumber(assumptions.initialValue, 'Initial value'),
    currency: assumptions.currency,
    covariance_estimator: assumptions.covarianceEstimator,
    gmm_components: requiredNumber(assumptions.gmmComponents, 'GMM components'),
    gmm_reg_covar: requiredNumber(assumptions.gmmRegCovar, 'GMM regularizer'),
    ewma_lambda: requiredNumber(assumptions.ewmaLambda, 'EWMA lambda'),
    rebalance: assumptions.rebalance,
  };
}

export function buildSingleRequest(ticker, assumptions) {
  return {
    ticker: ticker.trim().toUpperCase(),
    ...buildCommonRequest(assumptions),
  };
}

export function buildPortfolioRequest(assets, assumptions) {
  if (assumptions.model === 'ewma') {
    throw new Error('EWMA is available only for single-asset scenarios.');
  }
  return {
    tickers: assets.map((asset) => asset.ticker.trim().toUpperCase()),
    weights: assets.map((asset) => requiredNumber(asset.weight, `${asset.ticker} weight`) / 100),
    ...buildCommonRequest(assumptions),
  };
}

export function normalizeWeightPercentages(assets) {
  const values = assets.map((asset) => Math.max(0, Number(asset.weight) || 0));
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total === 0) return assets;

  const exactBasisPoints = values.map((value) => (value / total) * 10_000);
  const basisPoints = exactBasisPoints.map(Math.floor);
  let residual = 10_000 - basisPoints.reduce((sum, value) => sum + value, 0);
  const residualOrder = exactBasisPoints
    .map((value, index) => ({ index, fraction: value - basisPoints[index] }))
    .sort((left, right) => right.fraction - left.fraction || left.index - right.index);

  for (let index = 0; index < residual; index += 1) {
    basisPoints[residualOrder[index].index] += 1;
  }

  return assets.map((asset, index) => ({
    ...asset,
    weight: (basisPoints[index] / 100).toFixed(2),
  }));
}

export function assertV3Response(response) {
  if (response?.api_version !== '3.0.0') {
    throw new Error('This interface requires API v3.0.0. Check the configured backend URL.');
  }
  if (!response.statistics || !response.percentiles || !response.percentile_values) {
    throw new Error('The backend returned an incomplete API v3.0.0 scenario response.');
  }
  return response;
}

export function buildChartData(paths = []) {
  if (!paths.length) return [];
  return Array.from({ length: paths[0].length }, (_, day) => {
    const row = { day };
    paths.forEach((path, pathIndex) => {
      row[`path_${pathIndex}`] = path[day];
    });
    return row;
  });
}

export function buildHistogramData(histogram = []) {
  return histogram.map(({ lower, upper, count }) => ({
    lower,
    upper,
    count,
    bin: `${formatPercent(lower, 1)} to ${formatPercent(upper, 1)}`,
  }));
}

export function buildPercentileRows(response) {
  return PERCENTILE_KEYS.map((key) => ({
    key,
    label: key.slice(1),
    returnValue: response.percentiles[key],
    endingValue: response.percentile_values[key],
  }));
}

export function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Unavailable';
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSignedPercent(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Unavailable';
  const sign = value > 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(digits)}%`;
}

export function formatRatio(value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Unavailable';
  return value.toFixed(2);
}

export function formatCurrency(value, currency = 'USD') {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Unavailable';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function describeDriftModel(driftModel) {
  if (driftModel === 'historical_diagnostic') {
    return 'Historical diagnostic: the fitted historical log-return location is used for diagnostic calibration. It is not a forecast.';
  }
  return 'Zero log drift: the applied mean log return is zero. This does not imply a zero expected simple return or a risk-neutral model.';
}

export function driftModelLabel(driftModel) {
  if (driftModel === 'zero_log_drift') return 'No directional return assumption';
  if (driftModel === 'historical_diagnostic') return 'Historical average — diagnostic only';
  return driftModel;
}
