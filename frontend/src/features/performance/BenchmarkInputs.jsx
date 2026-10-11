export default function BenchmarkInputs({ state, workspace, button, input }) {
  const busy = !!state.busy;
  return <div className="mt-5 space-y-3">
    <label className="flex items-center gap-3 text-sm font-semibold"><input type="checkbox" disabled={busy} checked={state.draft.include_benchmark} onChange={event => workspace.edit({ include_benchmark: event.target.checked })} />Compare with a reviewed benchmark</label>
    <p className="text-xs opacity-65">Choose your benchmark explicitly for this account and reporting window. Supply total-return levels already expressed in the account currency; no index or market data is selected automatically.</p>
    {state.draft.include_benchmark && <div className="rounded-xl border border-slate-400/30 p-4">
      <h4 className="text-sm font-semibold">Benchmark selection and evidence</h4><p className="mt-2 text-xs opacity-75">Identify the benchmark and revision, gross or net total-return basis, hedging policy, effective dates, source and publication/retrieval times. Use the same UTC daily intervals as your portfolio. Missing levels remain gaps; the maximum level age is an explicit calendar-day allowance.</p>
      <div className="mt-3 flex flex-wrap gap-3"><label className={`${button} max-w-full`}>Import benchmark JSON<input type="file" accept=".json,application/json" disabled={busy} className="mt-2 block w-full max-w-sm text-xs" onChange={event => { const file = event.target.files?.[0]; if (file) void workspace.importBenchmark(file.size > 16000000 ? Promise.reject(new Error('File too large')) : file.text()); event.target.value = ''; }} /></label><button className={button} disabled={busy || !state.draft.start || !state.draft.end} onClick={workspace.makeBenchmarkTemplate}>Prepare empty benchmark template</button></div>
      <p className="mt-3 text-xs opacity-65">The template contains no benchmark choice or invented level. Fill the identity, total-return convention, timestamps and reviewed values. Amounts must be decimal strings; null or omitted dates remain unavailable.</p>
      <label className="mt-3 block text-sm">Supplied benchmark evidence JSON<textarea rows="12" spellCheck="false" className={`${input} font-mono text-xs`} disabled={busy} value={state.benchmarkEvidence} onChange={event => workspace.editBenchmark(event.target.value)} /></label>
    </div>}
  </div>;
}
