const labels = {
  source_dates_have_no_verified_utc_valuation_boundaries: 'Provider date labels need verified portfolio valuation boundaries.',
  source_currency_differs_from_account_currency: 'USD source returns differ from the account currency.',
  historical_publication_availability_unknown: 'Historical publication availability is unknown.',
  declared_publication_requires_independent_review: 'The declared publication time needs independent evidence review.',
  risk_free_and_spread_funding_alignment_not_accepted: 'Risk-free accrual and spread funding need an accepted alignment policy.',
  no_rows_in_selected_window: 'The selected window has no source rows.',
  selected_window_exceeds_source_range: 'The selected window extends beyond the source dates.',
  missing_source_values: 'The selected rows contain declared missing values.',
};

export default function FactorSourceReview({ state, workspace, button, input }) {
  const source = state.sourceDraft, result = state.sourceReview, busy = !!state.busy;
  return <details className="mt-5 rounded-xl border border-slate-400/30 p-4">
    <summary className="font-semibold">Review a public factor source</summary>
    <p className="mt-3 text-sm opacity-75">Import the French developed five-factor daily CSV for source review. This keeps its USD returns and provider date labels. Alignment is required before regression; reviewing a file does not enable factor analysis.</p>
    <p className="mt-2 text-xs opacity-65">Uses the selected reporting dates as an inclusive source-date window. Unzip the provider download first. Publication time may stay unknown; enter the actual retrieval time.</p>
    <label className="mt-3 block text-sm">Developed daily source CSV<input type="file" accept=".csv,text/csv" disabled={busy} className="mt-2 block w-full max-w-sm text-xs" onChange={event => { const file = event.target.files?.[0]; if (file) void workspace.importSource(file.size > 2000000 ? Promise.reject(new Error()) : file.text()); event.target.value = ''; }} /></label>
    <label className="mt-3 block text-sm">Source CSV text<textarea className={`${input} font-mono text-xs`} rows="5" value={source.csv} disabled={busy} spellCheck="false" onChange={event => workspace.editSource({ csv: event.target.value })} /></label>
    <div className="mt-3 grid gap-3 sm:grid-cols-2">{[['retrieved', 'Actual retrieval timestamp'], ['published', 'Publication timestamp (optional)']].map(([key, label]) => <label key={key} className="min-w-0 text-sm">{label}<input className={input} value={source[key]} disabled={busy} placeholder="ISO timestamp with UTC offset" onChange={event => workspace.editSource({ [key]: event.target.value })} /></label>)}</div>
    <label className="mt-3 block text-sm">Publication evidence (if time supplied)<input className={input} value={source.publicationNote} maxLength="2000" disabled={busy} onChange={event => workspace.editSource({ publicationNote: event.target.value })} /></label>
    <label className="mt-3 block text-sm">Source review note<input className={input} value={source.note} maxLength="200" disabled={busy} onChange={event => workspace.editSource({ note: event.target.value })} /></label>
    <button type="button" className={`${button} mt-3`} disabled={busy || !source.csv} onClick={workspace.reviewSource}>Review native source</button>
    {result && <section aria-label="Factor source review results" className="mt-5 space-y-3">
      <h4 className="font-semibold">Source parsed · alignment required</h4>
      <p className="text-sm">{result.selected_rows} selected rows of {result.total_source_rows} · {result.native_currency} · database vintage {result.database_vintage} · {result.missing_cells} missing cells</p>
      <p className="text-xs">Source dates {result.source_first} to {result.source_last}. {result.calendar_gaps.length} gaps between selected date labels; these are not confirmed missing trading observations.</p>
      <ul className="list-disc space-y-1 pl-5 text-sm">{result.blockers.map(value => <li key={value}>{labels[value] || value}</li>)}</ul>
      <div className="overflow-x-auto"><table className="w-full min-w-[510px] text-left text-xs"><caption className="py-2 text-left">First six selected rows · decimal returns</caption><thead><tr>{['Source date', 'Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF'].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead><tbody>{result.rows.slice(0, 6).map(row => <tr key={row.date}>{[row.date, ...['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF'].map(name => row.returns[name] ?? 'Missing')].map((value, index) => <td key={index} className="p-2">{value}</td>)}</tr>)}</tbody></table></div>
      <p className="break-all text-xs opacity-65">Submitted-text SHA-256: {result.submitted_text_sha256}</p>
      <p className="text-xs opacity-75">Origin is user-declared. This receipt checks internal consistency, not provider authenticity or suitability. It cannot be used as the daily factor-evidence JSON.</p>
      <button type="button" className={button} onClick={() => { const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'factor-source-review.json'; anchor.click(); URL.revokeObjectURL(url); }}>Download source review</button>
    </section>}
  </details>;
}
