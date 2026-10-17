import { useMemo, useState, useSyncExternalStore } from 'react';
import {
  Bar, BarChart, Brush, CartesianGrid, Cell, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import {
  buildChartData,
  buildHistogramData,
  buildPercentileRows,
  describeDriftModel,
  driftModelLabel,
  MODEL_OPTIONS,
  formatCurrency,
  formatPercent,
  formatRatio,
  formatSignedPercent,
} from '../scenarioContract.js';

const panel = (isDark) => isDark
  ? 'bg-[#151e32] border-slate-700/60'
  : 'bg-white border-slate-200';

const motionQuery = '(prefers-reduced-motion: reduce)';
const subscribeMotion = (listener) => {
  const media = window.matchMedia(motionQuery);
  media.addEventListener('change', listener);
  return () => media.removeEventListener('change', listener);
};
const motionSnapshot = () => window.matchMedia(motionQuery).matches;

export default function ScenarioResults({ result, mode, isDark }) {
  const paths = useMemo(
    () => (mode === 'single' ? result.paths_chart_sample : result.portfolio_paths_chart_sample) || [],
    [mode, result],
  );
  const chartData = useMemo(() => buildChartData(paths), [paths]);
  const histogramData = useMemo(() => buildHistogramData(result.histogram), [result.histogram]);
  const percentileRows = useMemo(() => buildPercentileRows(result), [result]);
  const reduceMotion = useSyncExternalStore(subscribeMotion, motionSnapshot, () => true);
  const [trace, setTrace] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const selected = Math.min(trace, Math.max(0, paths.length - 1));
  const visible = paths.map((_, index) => index).filter((index) => showAll || index < 12 || index === selected);
  const currency = result.assumptions.currency;
  const ink = isDark ? '#98ceb5' : '#236d58';
  const muted = isDark ? '#b0beb3' : '#627269';
  const grid = isDark ? '#30443a' : '#e5eae5';
  const axis = { tickLine: false, axisLine: false, tick: { fill: muted, fontSize: 11 } };

  return (
    <section aria-label="Scenario results" className="scenario-results">
      <ResultNotice result={result} isDark={isDark} />
      <Statistics statistics={result.statistics} riskFreeRate={result.assumptions.risk_free_rate} isDark={isDark} />

      <ChartCard title={mode === 'single' ? 'Conditional price paths' : 'Conditional portfolio values'} isDark={isDark}>
        <div className="results-chart-toolbar">
          <p className="results-caption">{visible.length} of {paths.length} sampled traces. Statistics use all {result.assumptions.num_paths.toLocaleString()} paths.</p>
          <div className="results-chart-controls">
            <label>Focus trace
              <select aria-label="Focus trace" value={selected} onChange={(event) => setTrace(Number(event.target.value))}>
                {paths.map((_, index) => <option key={index} value={index}>{index + 1}</option>)}
              </select>
            </label>
            {paths.length > 12 && <button type="button" aria-pressed={showAll} onClick={() => setShowAll(!showAll)}>{showAll ? 'Show fewer traces' : 'Show full sample'}</button>}
          </div>
        </div>
        <div className="results-chart-legend"><span><i style={{ background: ink }} />Focused trace</span><span><i className="results-legend-sample" />Other sampled traces</span><span>{currency} · modeled periods</span></div>
        <div className="results-chart" role="group" aria-label={`Interactive sampled ${currency} paths. Select a trace or drag the range below to zoom. This sample is not a percentile band.`}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <LineChart data={chartData} margin={{ top: 16, right: 16, bottom: 8, left: 4 }} accessibilityLayer>
              <CartesianGrid vertical={false} stroke={grid} />
              <XAxis dataKey="day" {...axis} minTickGap={55} />
              <YAxis {...axis} width={76} tickCount={5} tickFormatter={(value) => new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value)} domain={['auto', 'auto']} />
              <Tooltip content={<TraceTooltip trace={selected} currency={currency} />} cursor={{ stroke: muted, strokeDasharray: '3 3' }} />
              {visible.filter((index) => index !== selected).map((index) => (
                <Line key={index} type="linear" dataKey={`path_${index}`} stroke={ink} strokeWidth={1} dot={false} activeDot={false} strokeOpacity={0.17} isAnimationActive={false} />
              ))}
              <Line type="linear" dataKey={`path_${selected}`} stroke={ink} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2 }} isAnimationActive={!reduceMotion} animationDuration={450} animationEasing="ease-out" />
              <Brush ariaLabel="Modeled-period range; use left and right arrow keys to adjust" dataKey="day" height={24} stroke={muted} fill={isDark ? '#182720' : '#f8f9f6'} travellerWidth={9} tickFormatter={(value) => String(value)} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="results-caption results-chart-footnote">Drag either range handle to inspect a period. Focus a trace to read its value. Sampled paths are illustrations, not forecasts or confidence bands.</p>
      </ChartCard>

      <div className="results-distribution-grid">
        <ChartCard title="Terminal return distribution" isDark={isDark}>
          <p className="results-caption">All simulated paths · ending return relative to initial value</p>
          <div className="results-chart results-chart-histogram" role="group" aria-label="Terminal return histogram. Bars show path counts; hover or use arrow keys for bin ranges.">
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <BarChart data={histogramData} margin={{ top: 24, right: 12, bottom: 8, left: 0 }} barCategoryGap="8%" accessibilityLayer>
                <CartesianGrid vertical={false} stroke={grid} />
                <XAxis dataKey="bin" {...axis} minTickGap={50} tickFormatter={(value) => value.split(' to ')[0]} />
                <YAxis {...axis} allowDecimals={false} width={48} tickCount={5} />
                <Tooltip content={<HistogramTooltip />} cursor={{ fill: isDark ? '#ffffff0a' : '#23372f08' }} />
                <Bar dataKey="count" radius={[2, 2, 0, 0]} isAnimationActive={!reduceMotion} animationDuration={550} animationEasing="ease-out">
                  {histogramData.map((bin, index) => <Cell key={index} fill={bin.upper <= 0 ? (isDark ? '#c98d80' : '#9a6559') : bin.lower >= 0 ? ink : muted} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="results-chart-legend"><span><i style={{ background: isDark ? '#c98d80' : '#9a6559' }} />Loss bins</span><span><i style={{ background: ink }} />Gain bins</span><span>Horizontal: return · vertical: path count</span></div>
          <p className="results-caption">Axis labels show each bin’s lower bound. Hover for the full range. A bin crossing zero is neutral.</p>
        </ChartCard>
        <PercentileTable rows={percentileRows} currency={currency} isDark={isDark} />
      </div>

      <TailRisk tailRisk={result.tail_risk} isDark={isDark} />
      {mode === 'portfolio' && <PortfolioRisk result={result} isDark={isDark} />}
      <ResponseAssumptions result={result} isDark={isDark} />
      <Diagnostics result={result} isDark={isDark} />
    </section>
  );
}

function TraceTooltip({ active, payload, label, trace, currency }) {
  if (!active || !payload?.length) return null;
  return <div className="results-tooltip"><p>Period {label} · trace {trace + 1}</p><strong>{formatCurrency(payload[0]?.payload?.[`path_${trace}`], currency)}</strong><small>Illustrative sample path</small></div>;
}

function HistogramTooltip({ active, payload }) {
  const bin = payload?.[0]?.payload;
  if (!active || !bin) return null;
  return <div className="results-tooltip"><p>{formatPercent(bin.lower, 1)} to {formatPercent(bin.upper, 1)}</p><strong>{bin.count.toLocaleString()} paths</strong><small>Terminal return interval</small></div>;
}

export function ResultNotice({ result, isDark }) {
  return (
    <div className={`rounded-2xl border p-5 ${panel(isDark)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className={`text-xl ${isDark ? 'text-white' : 'text-slate-900'}`}>Conditional scenario output</h2>
          <p className={`mt-1 text-sm font-semibold ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
            {result.ticker ? `Instrument: ${result.ticker}` : `Instruments: ${result.tickers.join(', ')}`}
          </p>
          <p className={`mt-1 text-sm ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>{result.message}</p>
          <p className={`mt-2 text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
            Estimation sample: {result.estimation_start} through {result.estimation_end} ({result.estimation_observations} valid intervals; {result.excluded_interval_count} excluded). Valuation date: {result.valuation_date}. Horizon units are modeled observation periods.
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-600'}`}>{result.assumptions.num_paths.toLocaleString()} paths</span>
      </div>
    </div>
  );
}

export function Statistics({ statistics, riskFreeRate, isDark }) {
  const calmarValue = statistics.calmar_ratio_median === null
    ? `Unavailable (${statistics.calmar_defined_paths}/${statistics.calmar_total_paths} paths defined)`
    : formatRatio(statistics.calmar_ratio_median);
  const primary = [
    ['Conditional mean return', formatSignedPercent(statistics.conditional_scenario_return_mean), 'Over the modeled horizon'],
    ['Annualized volatility', formatPercent(statistics.annualized_volatility), 'Dispersion of modeled returns'],
    ['Probability of loss', formatPercent(statistics.prob_loss), 'Ending below initial value'],
    ['P95 max drawdown', formatPercent(statistics.max_drawdown_p95), '95th percentile of path drawdowns'],
  ];
  const secondary = [
    ['Annualized median return', formatSignedPercent(statistics.annualized_return_median)],
    ['Sharpe ratio', formatRatio(statistics.sharpe_ratio)],
    ['Sortino ratio', formatRatio(statistics.sortino_ratio)],
    ['Median Calmar ratio', calmarValue],
    ['Median max drawdown', formatPercent(statistics.max_drawdown_median)],
    ['Minimum terminal return', formatSignedPercent(statistics.min_return)],
    ['Maximum terminal return', formatSignedPercent(statistics.max_return)],
  ];
  return (
    <div className={`results-panel results-summary ${panel(isDark)}`}>
      <dl className="results-key-metrics">
        {primary.map(([title, value, context]) => <div key={title}><dt>{title}</dt><dd>{value}</dd><p>{context}</p></div>)}
      </dl>
      <dl className="results-secondary-metrics">
        {secondary.map(([title, value]) => <div key={title}><dt>{title}</dt><dd>{value}</dd></div>)}
      </dl>
      <p className="results-caption results-metric-note">Sharpe and Sortino use the returned annual effective risk-free rate of {formatSignedPercent(riskFreeRate)} and {String(statistics.calmar_total_paths)} simulated paths. Median Calmar requires nonzero max drawdown on every path; otherwise its defined-path coverage is shown.</p>
    </div>
  );
}

export function PercentileTable({ rows, currency, isDark }) {
  return (
    <div className={`results-panel results-table-panel ${panel(isDark)}`}>
      <div className={`border-b p-5 ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
        <h3 className={`text-lg ${isDark ? 'text-white' : 'text-slate-900'}`}>Terminal return percentiles</h3>
        <p className={`mt-1 text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>Calculated by the server from all paths</p>
      </div>
      <table className="w-full text-sm results-data-table">
        <thead className={isDark ? 'text-slate-500' : 'text-slate-500'}>
          <tr><th className="px-5 py-3 text-left">Percentile</th><th className="px-3 py-3 text-right">Return</th><th className="px-5 py-3 text-right">Ending value</th></tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className={`${row.key === 'p50' ? 'results-median-row ' : ''}border-t ${isDark ? 'border-slate-800 text-slate-200' : 'border-slate-100 text-slate-800'}`}>
              <th className="px-5 py-3 text-left" scope="row">P{row.label}</th>
              <td className={`px-3 py-3 text-right results-value ${row.returnValue < 0 ? 'results-negative' : 'results-positive'}`}>{formatSignedPercent(row.returnValue)}</td>
              <td className="px-5 py-3 text-right results-value">{formatCurrency(row.endingValue, currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TailRisk({ tailRisk, isDark }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TailCard title="Value at Risk" metric={tailRisk.var} isDark={isDark} />
      <TailCard title="Expected Shortfall (CVaR)" metric={tailRisk.cvar} isDark={isDark} />
    </div>
  );
}

function TailCard({ title, metric, isDark }) {
  return (
    <div className={`rounded-2xl border p-5 ${panel(isDark)}`}>
      <div><h3 className={`text-lg ${isDark ? 'text-white' : 'text-slate-900'}`}>{title}</h3></div>
      <p className="results-caption mt-2">{title === 'Value at Risk' ? 'Modeled loss threshold at the selected confidence.' : 'Average loss in the modeled tail beyond the VaR threshold.'}</p>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <LabelValue label="Loss value" value={formatPercent(metric.value_pct)} isDark={isDark} />
        <LabelValue label="Currency value" value={formatCurrency(metric.value_currency, metric.currency)} isDark={isDark} />
        <LabelValue label="Confidence" value={formatPercent(metric.confidence, 1)} isDark={isDark} />
        <LabelValue label="Horizon" value={`${metric.horizon_days} modeled periods`} isDark={isDark} />
      </div>
      <p className={`mt-3 text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>Convention: loss-positive. A negative value is preserved when the relevant tail consists of gains.</p>
    </div>
  );
}

export function PortfolioRisk({ result, isDark }) {
  const decomposition = result.risk_decomposition;
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <div className={`results-panel results-table-panel ${panel(isDark)}`}>
        <div className={`border-b p-5 ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
          <h3 className={`text-lg ${isDark ? 'text-white' : 'text-slate-900'}`}>Signed volatility contribution</h3>
          <p className={`mt-1 text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>Component contributions may be negative when an asset reduces portfolio volatility.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm results-data-table">
            <thead className={isDark ? 'text-slate-500' : 'text-slate-500'}>
              <tr><th className="px-5 py-3 text-left">Asset</th><th className="px-3 py-3 text-right">Weight</th><th className="px-3 py-3 text-right">Marginal</th><th className="px-3 py-3 text-right">Component vol.</th><th className="px-5 py-3 text-right">Risk share</th></tr>
            </thead>
            <tbody>
              {result.asset_stats.map((asset) => (
                <tr key={asset.ticker} className={`border-t ${isDark ? 'border-slate-800 text-slate-200' : 'border-slate-100 text-slate-800'}`}>
                  <td className="px-5 py-3 font-bold">{asset.ticker}</td>
                  <td className="px-3 py-3 text-right results-value">{formatSignedPercent(asset.weight)}</td>
                  <td className="px-3 py-3 text-right results-value">{formatSignedPercent(asset.marginal_risk_contribution)}</td>
                  <td className="px-3 py-3 text-right results-value">{formatSignedPercent(asset.component_risk_contribution)}</td>
                  <td className="px-5 py-3 text-right results-value">{formatSignedPercent(asset.risk_contribution_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={`border-t p-4 text-xs ${isDark ? 'border-slate-700 text-slate-500' : 'border-slate-100 text-slate-500'}`}>
          Annualized volatility: {formatPercent(decomposition.annualized_volatility)} · Basis: historical simple-return covariance at initial weights · Estimator: {decomposition.covariance_estimator} · Shrinkage: {formatRatio(decomposition.shrinkage)}
        </div>
      </div>
      <CorrelationTable matrix={result.correlation_matrix} tickers={result.tickers} isDark={isDark} />
    </div>
  );
}

function CorrelationTable({ matrix, tickers, isDark }) {
  return (
    <div className={`overflow-x-auto rounded-3xl border p-5 ${panel(isDark)}`}>
      <h3 className={`mb-4 text-lg ${isDark ? 'text-white' : 'text-slate-900'}`}>Historical correlation matrix</h3>
      <p className="results-caption mb-3">Green: positive · blue: negative · intensity: magnitude. Values range from −1 to +1.</p>
      <table className="w-full text-sm results-data-table">
        <thead>
          <tr><th />{tickers.map((ticker) => <th key={ticker} className="px-3 py-3 text-right">{ticker}</th>)}</tr>
        </thead>
        <tbody>
          {tickers.map((ticker) => (
            <tr key={ticker} className={`border-t ${isDark ? 'border-slate-800 text-slate-200' : 'border-slate-100 text-slate-800'}`}>
              <th className="px-3 py-3 text-left">{ticker}</th>
              {tickers.map((other) => <td key={other} className="px-3 py-3 text-right results-value" style={{ backgroundColor: matrix[ticker][other] == null ? 'transparent' : `rgba(${matrix[ticker][other] < 0 ? '86, 119, 148' : '52, 138, 112'}, ${Math.abs(matrix[ticker][other]) * (isDark ? 0.35 : 0.16)})` }}>{formatRatio(matrix[ticker][other])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ResponseAssumptions({ result, isDark }) {
  const assumptions = result.assumptions;
  const modelOption = MODEL_OPTIONS.find((option) => option.value === result.model);
  const entries = [
    ['Model', modelOption ? result.ticker ? modelOption.singleLabel : modelOption.label : result.model],
    ['Forward return assumption', driftModelLabel(assumptions.drift_model)],
    ['History', `${assumptions.years} years`],
    ['Horizon', `${assumptions.horizon} modeled periods`],
    ['Paths', assumptions.num_paths],
    ['Seed', assumptions.random_seed],
    ['Risk-free rate', formatPercent(assumptions.risk_free_rate)],
    ['Periods/year', assumptions.periods_per_year],
    ['Confidence', formatPercent(assumptions.confidence, 1)],
    ['Initial value', formatCurrency(assumptions.initial_value, assumptions.currency)],
    ['Currency', assumptions.currency],
    ...(result.tickers ? [['Covariance request', assumptions.covariance_estimator?.replaceAll('_', ' ')]] : []),
    ...(result.tickers ? [['Rebalancing', assumptions.rebalance === 'buy_and_hold' ? 'Buy and hold' : assumptions.rebalance === 'constant_weight' ? 'Constant weights' : assumptions.rebalance]] : []),
    ...(result.model === 'gmm' ? [['GMM components', assumptions.gmm_components], ['GMM regularizer', assumptions.gmm_reg_covar]] : []),
    ...(result.model === 'ewma' ? [['EWMA lambda', assumptions.ewma_lambda]] : []),
  ];
  return (
    <div className={`rounded-3xl border p-6 ${panel(isDark)}`}>
      <div className="mb-4 flex items-center gap-3"><h3 className={`text-lg ${isDark ? 'text-white' : 'text-slate-900'}`}>Assumptions used by this result</h3></div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {entries.map(([label, value]) => <LabelValue key={label} label={label} value={value ?? 'Not applicable'} isDark={isDark} />)}
      </div>
      <div className={`mt-4 rounded-xl p-4 text-sm ${isDark ? 'bg-slate-900 text-slate-300' : 'bg-slate-100 text-slate-700'}`}>
        <p>{describeDriftModel(assumptions.drift_model)}</p>
        <p className="mt-1">Values are denominated in {assumptions.currency}; no foreign-exchange conversion is performed.</p>
      </div>
    </div>
  );
}

function Diagnostics({ result, isDark }) {
  return (
    <details className={`rounded-3xl border p-6 ${panel(isDark)}`}>
      <summary className={`flex cursor-pointer items-center gap-3 font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Model and data diagnostics</summary>
      <p className={`mt-3 text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
        The applied simulation covariance estimator may differ from the requested historical risk estimator for GMM and EWMA. The returned diagnostics identify the estimator actually applied.
      </p>
      <div className="mt-5 grid gap-6 xl:grid-cols-2">
        <div>
          <h4 className={`mb-2 text-sm font-bold ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Model diagnostics</h4>
          <pre className={`max-h-96 overflow-auto rounded-xl p-4 text-xs ${isDark ? 'bg-[#0B1120] text-slate-300' : 'bg-slate-100 text-slate-700'}`}>{JSON.stringify(result.model_diagnostics, null, 2)}</pre>
        </div>
        <div>
          <h4 className={`mb-2 text-sm font-bold ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Data diagnostics</h4>
          <pre className={`max-h-96 overflow-auto rounded-xl p-4 text-xs ${isDark ? 'bg-[#0B1120] text-slate-300' : 'bg-slate-100 text-slate-700'}`}>{JSON.stringify(result.data_diagnostics, null, 2)}</pre>
        </div>
      </div>
    </details>
  );
}

function LabelValue({ label, value, isDark }) {
  return <div><p className={`text-xs uppercase tracking-wide ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>{label}</p><p className={`mt-1 break-words results-value text-sm ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>{String(value)}</p></div>;
}

function ChartCard({ title, children, isDark }) {
  return (
    <div className={`results-panel results-chart-panel ${panel(isDark)}`}>
      <h3>{title}</h3>
      {children}
    </div>
  );
}
