import { useWorkspaceConnection } from '../workspace/sessionContext.js';
import { WorkspaceConnectionNotice } from '../workspace/PrivateWorkspace.jsx';
import { useState, useSyncExternalStore } from 'react';
import { createStressWorkspace } from './stress.js';
import { valuationRequest } from '../valuation/valuation.js';

const button = 'rounded-xl border border-teal-600/40 px-4 py-2 text-sm font-semibold hover:bg-teal-500/10 disabled:cursor-not-allowed disabled:opacity-40';
const input = 'mt-1 w-full rounded-xl border border-slate-400/40 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500';
const names = { historical_replay: 'Historical replay', block_bootstrap: 'Joint block bootstrap', deterministic_shock: 'Explicit security shocks' };
const labels = { scenario_name: 'Scenario name', rationale: 'Scenario rationale and evidence', currency: 'Portfolio currency', valuation_date: 'Valuation date', valuation_calendar: 'Valuation calendar / market-close convention', as_of: 'Publication cutoff (ISO timestamp with timezone)', known_at: 'Knowledge cutoff (ISO timestamp with timezone)', initial_value: 'Initial portfolio value (currency units)', risk_free_rate: 'Annual-effective risk-free rate (fraction)', horizon_periods: 'Horizon (observation periods)', path_count: 'Number of paths', block_length: 'Block length (observations)', seed: 'Random seed (explicit integer, 0 allowed)', confidence: 'Tail confidence (fraction, e.g. 0.95)', shock_horizon_label: 'Shock horizon / timing description' };
const pct = value => value == null ? 'Undefined' : `${new Intl.NumberFormat('en', { maximumFractionDigits: 3, signDisplay: 'auto' }).format(value * 100).replace('-', '−')}%`;
function Field({ name, value, onChange, type = 'text' }) {
  return <label className="block text-sm">{labels[name] || name}<input className={input} type={type} value={value} onChange={event => onChange(event.target.value)} required /></label>;
}
function Details({ title, value }) {
  return <details className="mt-4 rounded-xl border border-slate-400/30 p-3"><summary className="cursor-pointer text-sm font-medium">{title}</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(value, null, 2)}</pre></details>;
}
function Metric({ label, value, rate = true }) {
  return <div className="rounded-xl border border-slate-400/25 p-4"><dt className="text-xs opacity-75">{label}</dt><dd className="mt-2 text-lg font-semibold">{value?.value == null ? 'Undefined' : rate ? pct(value.value) : Number(value.value).toFixed(3)}</dd>{value?.reason && <p className="mt-2 text-xs">{value.reason}</p>}</div>;
}
export function StressResults({ output }) {
  if (!output) return null;
  const r = output.result;
  return <section aria-label="Stress scenario results" className="mt-6 rounded-2xl border border-slate-400/30 p-5">
    <h3 className="text-xl font-semibold">{r.scenario_name}</h3><p className="mt-2 text-sm">{r.interpretation}</p>
    <p className="mt-3 text-sm">{r.currency} · {r.horizon_label} · {r.population_size} scenario paths · nominal total simple returns</p>
    <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <Metric label="Scenario mean terminal return" value={{ value: r.scenario_mean_terminal_return }} />
      <Metric label={`Scenario mean terminal value (${r.currency})`} value={{ value: r.scenario_mean_terminal_value }} rate={false} />
      <Metric label="Scenario median maximum drawdown" value={{ value: r.scenario_max_drawdown_median }} />
      <Metric label="Scenario maximum drawdown p95" value={{ value: r.scenario_max_drawdown_p95 }} />
      <Metric label="Scenario annualized period volatility" value={r.scenario_annualized_volatility} />
      <Metric label="Scenario terminal VaR (loss positive)" value={r.scenario_var} />
      <Metric label="Scenario expected shortfall (loss positive)" value={r.scenario_expected_shortfall} />
      <Metric label="Scenario Sharpe ratio" value={r.scenario_sharpe_ratio} rate={false} />
      <Metric label="Scenario Sortino ratio" value={r.scenario_sortino_ratio} rate={false} />
      <Metric label="Scenario median Calmar ratio" value={r.scenario_calmar_ratio_median} rate={false} />
    </dl>
    <p className="mt-4 text-xs">Tail confidence: {r.tail_confidence == null ? 'Not applicable' : pct(r.tail_confidence)} · Effective tail observations: {r.tail_effective_count == null ? 'Not applicable' : new Intl.NumberFormat('en', { maximumFractionDigits: 4 }).format(r.tail_effective_count)} · Calmar defined paths: {r.calmar_defined_paths} / {r.calmar_total_paths}</p>
    <p className="mt-3 text-sm">{r.uncertainty}</p>
    <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">{r.methodology.map(item => <li key={item}>{item}</li>)}</ul>
    {r.terminal_return_percentiles && <Details title="Terminal return percentiles — complete population" value={r.terminal_return_percentiles} />}
    <Details title="Run manifest — resolved inputs, securities and reproducibility" value={output.manifest} />
    <Details title="Complete server output and chart-only path sample" value={r} />
  </section>;
}
export default function StressWorkspace({ apiUrl, isDark }) {
  const [workspace] = useState(() => createStressWorkspace((path, options, key) => valuationRequest(apiUrl, key, path, options)));
  const state = useSyncExternalStore(workspace.subscribe, workspace.getSnapshot, workspace.getSnapshot);
  useWorkspaceConnection(workspace);
  const d = state.draft;
  const shock = d.method === 'deterministic_shock';
  const field = name => <Field key={name} name={name} value={d[name]} onChange={value => workspace.edit(name, value)} type={name === 'valuation_date' ? 'date' : 'text'} />;
  return <section className={`rounded-2xl border p-5 md:p-7 ${isDark ? 'border-slate-700 bg-slate-900 text-slate-100' : 'border-slate-200 bg-white text-slate-800'}`}>
    <h2 className="text-2xl font-semibold tracking-tight">Risk &amp; Scenario Lab</h2><p className="mt-2 text-xs opacity-70">Inputs and results stay in memory only and clear on page navigation, workspace lock, or refresh.</p>
    <p className="mt-2 max-w-3xl text-sm opacity-80">Apply supplied historical sequences, resample joint blocks, or declare explicit security shocks. These are conditional scenarios; historical returns are evidence and do not become investor expected-return views.</p>
    {!state.connected ? <WorkspaceConnectionNotice workspace={workspace} /> : <>
      <form onSubmit={event => { event.preventDefault(); void workspace.evaluate(); }}>
        <fieldset className="mt-6"><legend className="font-semibold">1. Declare the portfolio</legend><p className="mt-2 text-sm opacity-75">Select registered securities in one currency. Supply long-only fractional weights summing to one. Current weights are owner-declared, not ledger holdings.</p>
          <div className="mt-3 flex max-h-52 flex-wrap gap-2 overflow-auto">{state.securities.map(security => <label key={security.id} className="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-400/30 p-3 text-sm"><input type="checkbox" checked={d.assets.some(asset => asset.security_id === security.id)} onChange={() => workspace.toggleSecurity(security.id)} />{security.ticker} · {security.currency}</label>)}</div>
          {!state.securities.length && <p className="mt-3 text-sm">No registered securities. Create securities in Research before evaluating.</p>}
          {state.more && <button type="button" className={`${button} mt-3`} disabled={state.busy} onClick={() => void workspace.loadMore()}>Load more securities</button>}
          {!!d.assets.length && <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><caption className="mb-2 text-left text-xs">History columns and shock order must match this exact selection order.</caption><thead><tr><th className="p-2">Security / stable ID</th><th className="p-2">Weight (fraction)</th>{shock && <th className="p-2">Security shock (simple return)</th>}</tr></thead><tbody>{d.assets.map(asset => <tr key={asset.security_id} className="border-t border-slate-400/25"><td className="p-2">{state.securities.find(s => s.id === asset.security_id)?.ticker}<span className="block text-xs opacity-70">{asset.security_id}</span></td><td className="p-2"><input aria-label={`Weight ${asset.security_id}`} className={input} value={asset.weight} onChange={event => workspace.editAsset(asset.security_id, 'weight', event.target.value)} required /></td>{shock && <td className="p-2"><input aria-label={`Shock ${asset.security_id}`} className={input} value={asset.shock} onChange={event => workspace.editAsset(asset.security_id, 'shock', event.target.value)} required /></td>}</tr>)}</tbody></table></div>}
        </fieldset>
        <fieldset className="mt-7"><legend className="font-semibold">2. State the scenario assumptions</legend><label className="mt-3 block text-sm">Scenario method<select className={input} value={d.method} onChange={event => workspace.edit('method', event.target.value)}>{Object.entries(names).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <div className="mt-4 grid gap-4 md:grid-cols-2">{['scenario_name', 'rationale', 'currency', 'initial_value', 'valuation_date', 'valuation_calendar', 'as_of', 'known_at'].map(field)}</div>
          {shock ? <div className="mt-4">{field('shock_horizon_label')}<p className="mt-2 text-xs">Use security simple-return fractions (−1 = complete loss). Specify rationale for each shock; macro-factor mappings are not inferred.</p></div> : <>
            <div className="mt-4 grid gap-4 md:grid-cols-2"><label className="block text-sm">Rebalancing<select className={input} value={d.rebalance} onChange={event => workspace.edit('rebalance', event.target.value)}><option value="per_observation">Rebalance after every observation</option><option value="buy_and_hold">Buy and hold; let weights drift</option></select></label>{field('risk_free_rate')}</div>
            <label className="mt-4 block text-sm">Supplied joint history JSON<textarea className={`${input} min-h-52 font-mono`} value={d.history} onChange={event => workspace.edit('history', event.target.value)} required /></label>
            <p className="mt-2 text-xs">Use actual aligned total simple returns. No observations are fetched or filled automatically. Historical complete losses are explicitly unsupported by the positive-path engine; they are never silently removed.</p>
            <Details title="Required history structure and provenance" value={{ security_ids: d.assets.map(asset => asset.security_id), observations: 'Array of {start: YYYY-MM-DD, end: YYYY-MM-DD, returns: [one simple return per selected security]} — at least two actual joint rows', frequency: 'daily | weekly | monthly | annual', periods_per_year: 'explicit integer consistent with frequency', source: 'owner-supplied source reference', retrieved_at: 'ISO timestamp with timezone', adjustment_policy: 'distributions, splits, calendar gaps and corporate-action treatment', interval_alignment: 'identical_start_end_and_valuation_cutoff', return_basis: 'total', money_basis: 'nominal' }} />
            {d.method === 'block_bootstrap' && <><div className="mt-4 grid gap-4 md:grid-cols-2">{field('horizon_periods')}</div><details className="mt-4 rounded-xl border border-slate-400/30 p-4"><summary>Advanced settings — resampling &amp; reproducibility</summary><div className="mt-4 grid gap-4 md:grid-cols-2">{['path_count', 'block_length', 'seed', 'confidence'].map(field)}</div></details><label className="mt-4 flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1" checked={d.acceptEmpirical} onChange={event => workspace.edit('acceptEmpirical', event.target.checked)} required />I explicitly choose to resample observed empirical returns unchanged. No recentering is applied. Block endpoint weights and random sampling can change the sample mean; this is not my forward expected-return assumption.</label><p className="mt-2 text-xs">Moving blocks retain joint rows and within-block order. Horizon × paths × securities is bounded to 2,000,000 cells.</p></>}
          </>}
        </fieldset>
        <button className={`${button} mt-6 bg-teal-600 text-white hover:bg-teal-700`} disabled={state.busy || !d.assets.length}>{state.busy ? 'Evaluating…' : 'Evaluate conditional scenario'}</button>
      </form>
    </>}
    {state.error && <p role="alert" className="mt-4 rounded-xl border border-rose-400/40 p-3 text-sm">{state.error}</p>}
    <StressResults output={state.output} />
  </section>;
}
