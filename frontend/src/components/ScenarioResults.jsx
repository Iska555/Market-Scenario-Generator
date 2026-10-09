import { useMemo } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  Shield,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
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
  : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50';

export default function ScenarioResults({ result, mode, isDark }) {
  const paths = useMemo(
    () => (mode === 'single' ? result.paths_chart_sample : result.portfolio_paths_chart_sample) || [],
    [mode, result],
  );
  const chartData = useMemo(() => buildChartData(paths), [paths]);
  const histogramData = useMemo(() => buildHistogramData(result.histogram), [result.histogram]);
  const percentileRows = useMemo(() => buildPercentileRows(result), [result]);
  const currency = result.assumptions.currency;

  return (
    <section aria-label="Scenario results" className="space-y-6">
      <ResultNotice result={result} isDark={isDark} />
      <Statistics statistics={result.statistics} riskFreeRate={result.assumptions.risk_free_rate} isDark={isDark} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <ChartCard title={mode === 'single' ? 'Conditional price path sample' : 'Conditional portfolio-value path sample'} icon={TrendingUp} isDark={isDark}>
            <p className={`mb-4 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Visual sample only. It is not used for any statistic, histogram bin, or percentile.
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1e293b' : '#e2e8f0'} />
                <XAxis dataKey="day" stroke={isDark ? '#64748b' : '#94a3b8'} />
                <YAxis stroke={isDark ? '#64748b' : '#94a3b8'} tickFormatter={(value) => formatCurrency(value, currency)} width={92} />
                {paths.map((_, index) => (
                  <Line key={index} type="monotone" dataKey={`path_${index}`} stroke={isDark ? '#818cf8' : '#4f46e5'} strokeWidth={1.3} dot={false} strokeOpacity={0.18} isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Server terminal-return histogram" icon={BarChart3} isDark={isDark}>
            <p className={`mb-4 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              The API returns these bins and counts from the complete simulated population.
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={histogramData}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#1e293b' : '#e2e8f0'} />
                <XAxis dataKey="bin" stroke={isDark ? '#64748b' : '#94a3b8'} interval="preserveStartEnd" />
                <YAxis stroke={isDark ? '#64748b' : '#94a3b8'} allowDecimals={false} />
                <Tooltip cursor={{ fill: 'transparent' }} formatter={(value) => [value, 'Paths']} />
                <Bar dataKey="count" fill={isDark ? '#818cf8' : '#4f46e5'} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <PercentileTable rows={percentileRows} currency={currency} isDark={isDark} />
      </div>

      <TailRisk tailRisk={result.tail_risk} isDark={isDark} />
      {mode === 'portfolio' && <PortfolioRisk result={result} isDark={isDark} />}
      <ResponseAssumptions result={result} isDark={isDark} />
      <Diagnostics result={result} isDark={isDark} />
    </section>
  );
}

export function ResultNotice({ result, isDark }) {
  return (
    <div className={`rounded-2xl border p-5 ${panel(isDark)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Conditional scenario output</h2>
          <p className={`mt-1 text-sm font-semibold ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
            {result.ticker ? `Instrument: ${result.ticker}` : `Instruments: ${result.tickers.join(', ')}`}
          </p>
          <p className={`mt-1 text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{result.message}</p>
          <p className={`mt-2 text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
            Estimation sample: {result.estimation_start} through {result.estimation_end} ({result.estimation_observations} valid intervals; {result.excluded_interval_count} excluded). Valuation date: {result.valuation_date}. Horizon units are modeled observation periods.
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-600'}`}>API {result.api_version}</span>
      </div>
    </div>
  );
}

export function Statistics({ statistics, riskFreeRate, isDark }) {
  const calmarValue = statistics.calmar_ratio_median === null
    ? `Unavailable (${statistics.calmar_defined_paths}/${statistics.calmar_total_paths} paths defined)`
    : formatRatio(statistics.calmar_ratio_median);
  const items = [
    ['Conditional mean return', formatSignedPercent(statistics.conditional_scenario_return_mean), TrendingUp, 'emerald'],
    ['Annualized median return', formatSignedPercent(statistics.annualized_return_median), Target, 'blue'],
    ['Annualized volatility', formatPercent(statistics.annualized_volatility), Activity, 'violet'],
    ['Sharpe ratio', formatRatio(statistics.sharpe_ratio), Shield, 'blue'],
    ['Sortino ratio', formatRatio(statistics.sortino_ratio), TrendingDown, 'orange'],
    ['Median Calmar ratio', calmarValue, Activity, 'violet'],
    ['Probability of loss', formatPercent(statistics.prob_loss), AlertTriangle, 'amber'],
    ['Median max drawdown', formatPercent(statistics.max_drawdown_median), TrendingDown, 'rose'],
    ['P95 max drawdown', formatPercent(statistics.max_drawdown_p95), TrendingDown, 'rose'],
    ['Minimum terminal return', formatSignedPercent(statistics.min_return), TrendingDown, 'rose'],
    ['Maximum terminal return', formatSignedPercent(statistics.max_return), TrendingUp, 'emerald'],
  ];
  return (
    <div>
      <p className={`mb-3 text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
        Sharpe and Sortino use the returned annual effective risk-free rate of {formatSignedPercent(riskFreeRate)} and {String(statistics.calmar_total_paths)} simulated paths.
      </p>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        {items.map(([title, value, icon, color]) => <StatCard key={title} title={title} value={value} icon={icon} color={color} isDark={isDark} />)}
      </div>
      <p className={`mt-3 text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
        The median Calmar ratio is reported only when max drawdown is nonzero for every simulated path; the coverage count remains visible when it is unavailable.
      </p>
    </div>
  );
}

export function PercentileTable({ rows, currency, isDark }) {
  return (
    <div className={`overflow-hidden rounded-3xl border ${panel(isDark)}`}>
      <div className={`border-b p-5 ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
        <h3 className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Terminal return percentiles</h3>
        <p className={`mt-1 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Calculated by the server from all paths</p>
      </div>
      <table className="w-full text-sm">
        <thead className={isDark ? 'text-slate-500' : 'text-slate-400'}>
          <tr><th className="px-5 py-3 text-left">Percentile</th><th className="px-3 py-3 text-right">Return</th><th className="px-5 py-3 text-right">Ending value</th></tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className={`border-t ${isDark ? 'border-slate-800 text-slate-200' : 'border-slate-100 text-slate-800'}`}>
              <td className="px-5 py-3 font-semibold">P{row.label}</td>
              <td className={`px-3 py-3 text-right font-mono ${row.returnValue < 0 ? 'text-rose-500' : 'text-emerald-500'}`}>{formatSignedPercent(row.returnValue)}</td>
              <td className="px-5 py-3 text-right font-mono">{formatCurrency(row.endingValue, currency)}</td>
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
      <div className="flex items-center gap-2"><Shield className="h-5 w-5 text-rose-500" /><h3 className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{title}</h3></div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <LabelValue label="Loss value" value={formatSignedPercent(metric.value_pct)} isDark={isDark} />
        <LabelValue label="Currency value" value={formatCurrency(metric.value_currency, metric.currency)} isDark={isDark} />
        <LabelValue label="Confidence" value={formatPercent(metric.confidence, 1)} isDark={isDark} />
        <LabelValue label="Horizon" value={`${metric.horizon_days} modeled periods`} isDark={isDark} />
      </div>
      <p className={`mt-3 text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Convention: loss-positive. A negative value is preserved when the relevant tail consists of gains.</p>
    </div>
  );
}

export function PortfolioRisk({ result, isDark }) {
  const decomposition = result.risk_decomposition;
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <div className={`overflow-hidden rounded-3xl border ${panel(isDark)}`}>
        <div className={`border-b p-5 ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
          <h3 className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Signed volatility contribution</h3>
          <p className={`mt-1 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Component contributions may be negative when an asset reduces portfolio volatility.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className={isDark ? 'text-slate-500' : 'text-slate-400'}>
              <tr><th className="px-5 py-3 text-left">Asset</th><th className="px-3 py-3 text-right">Weight</th><th className="px-3 py-3 text-right">Marginal</th><th className="px-3 py-3 text-right">Component vol.</th><th className="px-5 py-3 text-right">Risk share</th></tr>
            </thead>
            <tbody>
              {result.asset_stats.map((asset) => (
                <tr key={asset.ticker} className={`border-t ${isDark ? 'border-slate-800 text-slate-200' : 'border-slate-100 text-slate-800'}`}>
                  <td className="px-5 py-3 font-bold">{asset.ticker}</td>
                  <td className="px-3 py-3 text-right font-mono">{formatSignedPercent(asset.weight)}</td>
                  <td className="px-3 py-3 text-right font-mono">{formatSignedPercent(asset.marginal_risk_contribution)}</td>
                  <td className="px-3 py-3 text-right font-mono">{formatSignedPercent(asset.component_risk_contribution)}</td>
                  <td className="px-5 py-3 text-right font-mono">{formatSignedPercent(asset.risk_contribution_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={`border-t p-4 text-xs ${isDark ? 'border-slate-700 text-slate-400' : 'border-slate-100 text-slate-500'}`}>
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
      <h3 className={`mb-4 font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Historical correlation matrix</h3>
      <table className="w-full text-sm">
        <thead>
          <tr><th />{tickers.map((ticker) => <th key={ticker} className="px-3 py-3 text-right">{ticker}</th>)}</tr>
        </thead>
        <tbody>
          {tickers.map((ticker) => (
            <tr key={ticker} className={`border-t ${isDark ? 'border-slate-800 text-slate-200' : 'border-slate-100 text-slate-800'}`}>
              <th className="px-3 py-3 text-left">{ticker}</th>
              {tickers.map((other) => <td key={other} className="px-3 py-3 text-right font-mono">{formatRatio(matrix[ticker][other])}</td>)}
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
    ['Covariance request', assumptions.covariance_estimator],
    ['Rebalancing', assumptions.rebalance],
    ['GMM components', assumptions.gmm_components],
    ['GMM regularizer', assumptions.gmm_reg_covar],
    ['EWMA lambda', assumptions.ewma_lambda],
  ];
  return (
    <div className={`rounded-3xl border p-6 ${panel(isDark)}`}>
      <div className="mb-4 flex items-center gap-3"><Target className="h-5 w-5 text-indigo-500" /><h3 className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Assumptions used by this result</h3></div>
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
      <summary className={`flex cursor-pointer items-center gap-3 font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}><Database className="h-5 w-5 text-indigo-500" />Model and data diagnostics</summary>
      <p className={`mt-3 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
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
  return <div><p className={`text-xs uppercase tracking-wide ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{label}</p><p className={`mt-1 break-words font-mono text-sm font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>{String(value)}</p></div>;
}

function StatCard({ title, value, icon, color, isDark }) {
  const IconComponent = icon;
  const colors = {
    emerald: isDark ? 'text-emerald-400 bg-emerald-500/10' : 'text-emerald-600 bg-emerald-50',
    violet: isDark ? 'text-violet-400 bg-violet-500/10' : 'text-violet-600 bg-violet-50',
    rose: isDark ? 'text-rose-400 bg-rose-500/10' : 'text-rose-600 bg-rose-50',
    orange: isDark ? 'text-orange-400 bg-orange-500/10' : 'text-orange-600 bg-orange-50',
    amber: isDark ? 'text-amber-400 bg-amber-500/10' : 'text-amber-600 bg-amber-50',
    blue: isDark ? 'text-blue-400 bg-blue-500/10' : 'text-blue-600 bg-blue-50',
  };
  return (
    <div className={`rounded-2xl border p-5 ${panel(isDark)}`}>
      <div className={`mb-4 w-fit rounded-xl p-3 ${colors[color]}`}><IconComponent className="h-5 w-5" /></div>
      <p className={`text-xs font-bold uppercase tracking-wider ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>{title}</p>
      <p className={`mt-1 break-words text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{value}</p>
    </div>
  );
}

function ChartCard({ title, icon, children, isDark }) {
  const IconComponent = icon;
  return (
    <div className={`rounded-3xl border p-6 ${panel(isDark)}`}>
      <div className="mb-2 flex items-center gap-3"><div className={`rounded-xl p-2 ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}><IconComponent className="h-5 w-5" /></div><h3 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{title}</h3></div>
      {children}
    </div>
  );
}
