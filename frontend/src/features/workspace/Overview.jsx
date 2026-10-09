import { useState, useSyncExternalStore } from 'react';
import { accountingRequest } from '../ledger/ledger.js';
import { researchRequest } from '../thesis/thesis.js';
import { createOverview } from './overview.js';
import { useWorkspaceConnection } from './sessionContext.js';
import { WorkspaceConnectionNotice } from './PrivateWorkspace.jsx';

export function OverviewRecords({ state }) {
  const account = state.portfolios.find(item => item.id === state.selectedId);
  const ledger = state.ledger;
  return <>
    {account && <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
      <div><dt className="opacity-65">Recorded account</dt><dd className="mt-1 font-semibold">{account.name}</dd></div>
      <div><dt className="opacity-65">Base currency</dt><dd className="mt-1 font-semibold">{account.base_currency}</dd></div>
      <div><dt className="opacity-65">Account label</dt><dd className="mt-1 font-semibold">{[account.broker, account.account_label].filter(Boolean).join(' · ') || 'Not recorded'}</dd></div>
    </dl>}
    {ledger && <>
      <p className="mt-5 text-xs opacity-70">Ledger version {ledger.version} · economic cutoff {ledger.as_of || 'Current server cutoff'} · knowledge cutoff {ledger.known_at || 'Current server cutoff'}</p>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[430px] text-left text-sm"><caption className="pb-3 text-left font-semibold">Current recorded holdings</caption><thead><tr><th className="p-3">Equity</th><th className="p-3">Quantity</th><th className="p-3">Local currency</th></tr></thead><tbody>
        {ledger.positions.length ? ledger.positions.map(position => <tr className="border-t border-slate-400/25" key={position.security_id}><th className="p-3 font-medium">{state.securities[position.security_id]?.ticker || 'Equity record'}<details className="mt-1 text-xs font-normal opacity-70"><summary>Security details</summary><p>{state.securities[position.security_id]?.name || 'Name unavailable'}</p><p className="break-all">{position.security_id}</p></details></th><td className="p-3 font-mono">{position.quantity}</td><td className="p-3">{position.currency}</td></tr>) : <tr><td colSpan="3" className="border-t border-slate-400/25 p-4">No open positions recorded in this ledger.</td></tr>}
      </tbody></table></div>
      <h3 className="mt-6 text-sm font-semibold">Recorded cash by currency</h3>
      <ul className="mt-2 flex flex-wrap gap-3 text-sm">{ledger.cash.length ? ledger.cash.map(row => <li className="rounded-lg border border-slate-400/25 px-3 py-2" key={row.currency}>{row.currency} <span className="font-mono">{row.amount}</span></li>) : <li>No cash balances recorded.</li>}</ul>
      <p className="mt-4 text-xs opacity-70">Quantities and trade-date economic cash come from ledger transactions. They are not broker-reconciled holdings or available-to-withdraw cash. Portfolio weights require dated prices and FX; they are not inferred from cost.</p>
    </>}
  </>;
}

export default function Overview({ apiUrl, isDark, onNavigate }) {
  const [workspace] = useState(() => createOverview((path, options, key) => accountingRequest(apiUrl, key, path, options), (id, key) => researchRequest(apiUrl, key, `/securities/${encodeURIComponent(id)}`)));
  useWorkspaceConnection(workspace);
  const state = useSyncExternalStore(workspace.subscribe, workspace.getSnapshot, workspace.getSnapshot);
  const panel = `rounded-2xl border p-5 md:p-6 ${isDark ? 'border-slate-700 bg-[#151e32]' : 'border-slate-200 bg-white'}`;
  return <section className="space-y-6" aria-label="Portfolio overview">
    <div className={panel}><h2 className="text-xl font-semibold">Your portfolio record</h2>
      <p className="mt-2 text-sm opacity-75">Lightyear Stocks &amp; Shares ISA is the intended broker/account. No broker account is connected. The ledger uses manual entries and reviewed canonical CSV.</p>
      {!state.connected && <WorkspaceConnectionNotice workspace={workspace} />}
      {state.busy && <p className="mt-4 text-sm" role="status">Loading recorded accounts and holdings…</p>}
      {state.error && <p className="mt-4 text-sm" role="alert">{state.error}</p>}
      {state.connected && !state.portfolios.length && <div className="mt-5 rounded-xl bg-slate-500/5 p-5"><h3 className="font-semibold">No portfolio account recorded</h3><p className="mt-2 text-sm">Create your account record in Ledger, then record reviewed transactions to establish holdings.</p><button className="mt-4 text-sm font-semibold underline" onClick={() => onNavigate('ledger')}>Open Ledger</button></div>}
      {state.connected && !!state.portfolios.length && <><div className="mt-5 flex flex-wrap items-end gap-4"><label className="text-sm">Portfolio account<select className="mt-1 block max-w-full rounded-lg border border-slate-400/40 bg-transparent p-2" value={state.selectedId} onChange={event => workspace.select(event.target.value)}>{state.portfolios.map(portfolio => <option key={portfolio.id} value={portfolio.id}>{portfolio.name}</option>)}</select></label><button className="rounded-lg border border-slate-400/40 px-3 py-2 text-sm" disabled={state.busy} onClick={() => workspace.select(state.selectedId)}>Reload holdings</button></div><OverviewRecords state={state} /></>}
    </div>
    <div className="grid gap-4 md:grid-cols-3">{[
      ['thesis', 'Review your reasoning', 'Record evidence and review whether your investment thesis still holds.'],
      ['valuation', 'Inspect return views', 'Compare assumption-dependent estimates before choosing an investor view.'],
      ['portfolio', 'Explore portfolio risk', 'Examine conditional volatility, tails and drawdowns with explicit assumptions.'],
    ].map(([id, title, description]) => <button key={id} onClick={() => onNavigate(id)} className={`${panel} text-left`}><span className="block font-semibold">{title} →</span><span className="mt-2 block text-sm opacity-70">{description}</span></button>)}</div>
    <p className="text-sm opacity-70">Historical returns are evidence and do not become investor expected-return views. Investment decisions remain yours.</p>
  </section>;
}
