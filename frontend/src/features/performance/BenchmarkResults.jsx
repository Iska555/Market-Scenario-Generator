const human = value => String(value || 'unavailable').replaceAll('_', ' ');
export function BenchmarkMetric({ metric, percent = true, points = false, decimals = 2 }) {
  if (typeof metric?.value !== 'number' || !Number.isFinite(metric.value)) return <span>Not defined<span className="mt-1 block text-xs opacity-70">{human(metric?.reason)}</span></span>;
  return <span>{(metric.value * (percent ? 100 : 1)).toFixed(decimals)}{points ? ' pp' : percent ? '%' : ''}</span>;
}
const statistics = {
  mean_daily_active_return: ['Mean daily active return', true, true],
  annualized_arithmetic_active_return: ['Annualized arithmetic active return', true, true],
  annualized_tracking_error: ['Annualized realized tracking error', true, false],
  information_ratio: ['Information ratio', false, false],
  beta: ['Beta to selected benchmark', false, false],
  correlation: ['Portfolio / benchmark correlation', false, false],
};
export default function BenchmarkResults({ result }) {
  const identity = result.benchmark.identity;
  return <section aria-label="Benchmark and realized active risk" className="space-y-5 rounded-xl border border-slate-400/30 p-4 sm:p-5">
    <div><h4 className="text-lg font-semibold">How your portfolio compares</h4><p className="mt-2 text-sm opacity-75">{identity.name} · {identity.currency} · {human(identity.return_basis)} · {human(identity.hedging)}</p><p className="mt-1 break-all text-xs opacity-65">Benchmark {identity.benchmark_id} · revision {identity.revision} · effective {identity.effective_from} → {identity.effective_to}</p></div>
    <p role="status" className="rounded-lg bg-slate-500/5 p-3 text-sm">{result.paired_intervals} of {result.expected_intervals} aligned daily intervals available. {result.paired_intervals === result.expected_intervals ? 'Complete paired coverage.' : 'Whole-window active statistics are withheld.'}</p>
    <dl className="grid gap-4 sm:grid-cols-3">{[['Benchmark total return', result.benchmark_return, false], ['Portfolio minus benchmark', result.cumulative_active_return, true], ['Relative wealth return', result.cumulative_relative_return, false]].map(([title, metric, points]) => <div key={title}><dt className="text-sm opacity-70">{title}</dt><dd className="mt-2 text-xl font-semibold"><BenchmarkMetric metric={metric} points={points} /></dd></div>)}</dl>
    <p className="text-xs opacity-70">The return difference is portfolio TWR minus benchmark return in percentage points. Relative wealth divides their compounded growth. Daily differences do not compound into the return difference.</p>
    <p className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs">These are descriptive sample estimates. Annualization is a mathematical scaling convention, not a forecast of one-year returns. {result.paired_intervals < 365 && 'This short sample can produce extreme and unstable ratios, beta and annualized values; it does not establish persistent skill.'}</p>
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(statistics).map(([key, [label, percent, points]]) => <div key={key} className="rounded-lg bg-slate-500/5 p-3"><dt className="text-sm opacity-75">{label}</dt><dd className="mt-2 font-semibold"><BenchmarkMetric metric={result.statistics[key]} percent={percent} points={points} /></dd><dd className="mt-1 text-xs opacity-65">{result.statistics[key]?.observations ?? 0} paired observations</dd></div>)}</dl>
    <details className="rounded-lg border border-slate-400/20 p-3"><summary className="text-sm font-semibold">Review aligned daily intervals</summary><div className="mt-3 max-h-96 overflow-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead><tr>{['UTC interval', 'Portfolio return', 'Benchmark return', 'Arithmetic active return', 'Relative wealth return'].map(label => <th key={label} className="p-3">{label}</th>)}</tr></thead><tbody>{result.daily.map(row => <tr key={row.end} className="border-t border-slate-400/20"><th className="p-3 font-normal">{row.start} → {row.end}</th>{['portfolio_return', 'benchmark_return', 'active_return', 'relative_return'].map(key => <td key={key} className="p-3"><BenchmarkMetric metric={row[key]} points={key === 'active_return'} /></td>)}</tr>)}</tbody></table></div></details>
    <details className="rounded-lg border border-slate-400/20 p-3"><summary className="text-sm font-semibold">Review benchmark identity and evidence</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(result.benchmark, null, 2)}</pre><p className="mt-2 break-all font-mono text-xs">Evidence SHA-256: {result.benchmark_sha256}</p></details>
    <details open className="rounded-lg border border-slate-400/20 p-3"><summary className="text-sm font-semibold">Comparison conventions and limitations</summary><ul className="mt-2 list-disc space-y-1 pl-5 text-xs opacity-75">{result.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>
  </section>;
}
