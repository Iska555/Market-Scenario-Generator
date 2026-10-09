import { useWorkspaceConnection } from '../workspace/sessionContext.js';
import { WorkspaceConnectionNotice } from '../workspace/PrivateWorkspace.jsx';
import { useState, useSyncExternalStore } from 'react';
import { createWorkspace, researchRequest, NARRATIVES, REVIEW_NARRATIVES, DECISIONS, label, displayDecimal } from './thesis.js';

const button = 'rounded-lg border border-indigo-400/50 px-4 py-2 text-sm font-semibold hover:bg-indigo-500/10 disabled:cursor-not-allowed disabled:opacity-40';
const fieldStyle = 'mt-1 w-full rounded-lg border border-slate-400/50 bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500';
const labels = { required_return: 'Required return (annual effective fraction; 0.08 = 8%)', updated_expected_return: 'Owner-declared updated expected return (annual effective fraction; 0.08 = 8%)', target_low: 'Target low (valuation currency per share)', target_high: 'Target high (valuation currency per share)', current_price: 'Current price (valuation currency per share)', horizon_months: 'Horizon (months)', valuation_currency: 'Valuation currency (3-letter code)', thesis_still_valid: 'Is the thesis still valid?' };
function Field({ name, value, onChange, required = false, options, multiline = false, ...rest }) {
  return <label className={`block text-sm font-medium ${multiline ? 'md:col-span-2' : ''}`}>
    {labels[name] || label(name)}{required ? ' *' : ''}
    {options ? <select className={fieldStyle} value={value} onChange={event => onChange(name, event.target.value)} required={required} {...rest}>
      <option value="">Choose explicitlyâ€¦</option>
      {options.map(option => <option key={option} value={option} className="bg-white text-slate-900">{option === 'true' ? 'Yes' : option === 'false' ? 'No' : label(option)}</option>)}
    </select> : multiline ? <textarea className={fieldStyle} rows={3} maxLength={10000} value={value ?? ''} required={required} onChange={event => onChange(name, event.target.value)} {...rest} />
      : <input className={fieldStyle} value={value ?? ''} required={required} onChange={event => onChange(name, event.target.value)} {...rest} />}
  </label>;
}
function RecordDetails({ record, fields }) {
  return <dl className="grid gap-3 text-sm md:grid-cols-2">{fields.map(field => <div key={field} className={NARRATIVES.includes(field) || REVIEW_NARRATIVES.includes(field) ? 'md:col-span-2' : ''}>
    <dt className="font-semibold opacity-70">{labels[field] || label(field)}</dt>
    <dd className="mt-1 whitespace-pre-wrap break-words">{record[field] === false ? 'No' : record[field] === true ? 'Yes' : record[field] == null || record[field] === '' ? 'Not supplied' : ['target_low', 'target_high', 'required_return', 'current_price', 'updated_expected_return'].includes(field) ? displayDecimal(record[field]) : String(record[field])}</dd>
  </div>)}</dl>;
}
export function RevisionDetails({ revision }) {
  return <><RecordDetails record={revision} fields={['revision', 'created_at', 'ticker', 'exchange', 'status', 'conviction', 'horizon_months', 'valuation_currency', 'target_low', 'target_high', 'required_return', ...NARRATIVES]} /><RecordIdentifiers record={revision} fields={['id', 'thesis_id', 'security_id']} /></>;
}
export function ReviewDetails({ review }) {
  return <><RecordDetails record={review} fields={['reviewed_at', 'decision', 'thesis_still_valid', 'valuation_currency', 'current_price', 'updated_expected_return', ...REVIEW_NARRATIVES]} /><RecordIdentifiers record={review} fields={['id', 'thesis_id', 'revision_id']} /></>;
}
function RecordIdentifiers({ record, fields }) {
  return <details className="mt-4 border-t border-slate-400/30 pt-3"><summary className="cursor-pointer text-xs opacity-70">Record identifiers</summary><div className="mt-3"><RecordDetails record={record} fields={fields} /></div></details>;
}

export default function ThesisWorkspace({ apiUrl, isDark }) {
  const [workspace] = useState(() => createWorkspace((path, options, key) => researchRequest(apiUrl, key, path, options)));
  const state = useSyncExternalStore(workspace.subscribe, workspace.getSnapshot, workspace.getSnapshot);
  const [security, setSecurity] = useState({ ticker: '', name: '', exchange: '', currency: '', country: '' });
  useWorkspaceConnection(workspace);
  const panel = `rounded-2xl border p-5 md:p-6 ${isDark ? 'border-slate-700 bg-[#151e32]' : 'border-slate-200 bg-white shadow-sm'}`;
  const lockedNavigation = state.busy || state.dirty || state.reviewDirty;
  return <section className={`space-y-6 ${isDark ? 'text-slate-100' : 'text-slate-900'}`} aria-label="Thesis workspace">
    <div className={panel}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-bold uppercase tracking-widest text-indigo-500">Private research</p><h2 className="mt-1 text-2xl font-bold">Investment theses</h2><p className="mt-2 max-w-3xl text-sm opacity-75">Record your reasoning, inspect timestamped revisions, and review what changed. Targets and return assumptions are your declared judgments.</p></div>

      </div>
      {!state.connected && <WorkspaceConnectionNotice workspace={workspace} />}
      <p className="mt-3 text-xs opacity-65">Unsaved drafts stay in memory only and clear when you leave this page, lock the workspace, or refresh. Save drafts before leaving.</p>
    </div>
    {state.busy && <p role="status" className="text-sm">Working with the research serviceâ€¦</p>}
    {state.error && <p role="alert" className="rounded-xl border border-red-400/50 bg-red-500/10 p-4 text-sm">{state.error}</p>}
    {state.notice && <p role="status" className="rounded-xl border border-green-400/50 bg-green-500/10 p-4 text-sm">{state.notice}</p>}
    {state.connected && <>
      <aside className={`${panel} border-indigo-400/40`}><h3 className="font-bold">Questions before a decision</h3><ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">{state.prompts.map(prompt => <li key={prompt}>{prompt}</li>)}</ol></aside>
      <section className={panel}>
        <h3 className="text-lg font-bold">Select a security</h3>
        <label className="mt-3 block text-sm">Research security<select className={fieldStyle} value={state.securityId} disabled={lockedNavigation} onChange={event => workspace.selectSecurity(event.target.value)}><option value="">Choose a securityâ€¦</option>{state.securities.map(item => <option key={item.id} value={item.id} className="bg-white text-slate-900">{item.ticker} Â· {item.exchange} Â· {item.name}</option>)}</select></label>
        <div className="mt-3 flex flex-wrap items-center gap-3"><button className={button} disabled={lockedNavigation || state.securitiesOffset === 0} onClick={() => workspace.securityPage(Math.max(0, state.securitiesOffset - 100))}>Previous securities</button><span className="text-xs">Page {Math.floor(state.securitiesOffset / 100) + 1} Â· up to 100 securities</span><button className={button} disabled={lockedNavigation || !state.securitiesMore} onClick={() => workspace.securityPage(state.securitiesOffset + 100)}>Next securities</button></div>
        {!state.securities.length && <p className="mt-3 text-sm opacity-70">No securities on this page. Add an equity below or return to the previous page.</p>}
        <details className="mt-5"><summary className="cursor-pointer text-sm font-semibold">Add an equity security</summary><form className="mt-4" onSubmit={event => { event.preventDefault(); workspace.createSecurity(Object.fromEntries(Object.entries(security).map(([field, value]) => [field, ['currency', 'country'].includes(field) ? value.trim().toUpperCase() : value.trim()]))); }}><fieldset disabled={lockedNavigation} className="grid gap-4 md:grid-cols-2">{Object.keys(security).map(field => <Field key={field} name={field} value={security[field]} onChange={(name, value) => setSecurity(current => ({ ...current, [name]: value }))} required maxLength={field === 'currency' ? 3 : field === 'country' ? 2 : field === 'name' ? 200 : 32} />)}<p className="text-xs opacity-65 md:col-span-2">Currency uses a 3-letter code such as USD; country uses a 2-letter code such as US.</p><button className={`${button} justify-self-start`}>Save security</button></fieldset></form></details>
      </section>
      {state.securityId && <section className={panel}><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-lg font-bold">Theses for this security</h3><button className={button} disabled={lockedNavigation} onClick={() => workspace.newThesis()}>New thesis</button></div>
        <label className="mt-3 block text-sm">Saved thesis<select className={fieldStyle} disabled={lockedNavigation} value={state.thesisId} onChange={event => event.target.value && workspace.selectThesis(event.target.value)}><option value="">Choose a saved thesisâ€¦</option>{state.theses.map(item => <option key={item.id} value={item.id} className="bg-white text-slate-900">{item.latest?.status} Â· revision {item.latest?.revision} Â· {item.created_at}</option>)}</select></label>
        {!state.theses.length && !state.busy && <p className="mt-3 text-sm opacity-70">No saved theses for this security yet.</p>}
        {state.thesesMore && <button className={`${button} mt-3`} disabled={state.busy} onClick={() => workspace.loadMore('theses')}>Load more theses</button>}
        {(state.dirty || state.reviewDirty) && <div className="mt-4 flex flex-wrap items-center gap-3 text-sm"><span>You have unsaved edits. Save or discard before switching records.</span><button className={button} disabled={state.busy} onClick={() => workspace.discardEdits()}>Discard unsaved edits</button></div>}
      </section>}
      {state.draft && <section className={panel}>
        <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-lg font-bold">{state.thesisId ? `Edit thesis Â· based on revision ${state.expectedRevision}` : 'Create thesis'}</h3>{state.thesisId && <button className={button} disabled={state.busy || state.reviewDirty} onClick={() => workspace.reloadThesis()}>Reload latest (discard draft)</button>}</div>
        <p className="mt-2 text-sm opacity-70">Saving appends an immutable revision. {state.dirty ? 'Unsaved draft.' : 'Matches the loaded saved revision.'} Active theses require all narrative sections except notes. Draft narratives may be blank.</p>
        <form className="mt-5" onSubmit={event => { event.preventDefault(); workspace.saveThesis(); }}><fieldset className="grid gap-4 md:grid-cols-2" disabled={state.busy || state.conflict}>
          <Field name="status" value={state.draft.status} onChange={workspace.editThesis} options={['draft', 'active', 'invalidated', 'closed']} required />
          <Field name="conviction" value={state.draft.conviction} onChange={workspace.editThesis} options={['low', 'medium', 'high']} required />
          <Field name="horizon_months" value={state.draft.horizon_months} onChange={workspace.editThesis} type="number" min="1" max="1200" step="1" required />
          <Field name="valuation_currency" value={state.draft.valuation_currency} onChange={workspace.editThesis} maxLength={3} pattern="[A-Za-z]{3}" required />
          {['target_low', 'target_high', 'required_return'].map(field => <Field key={field} name={field} value={state.draft[field]} onChange={workspace.editThesis} type="number" step="any" />)}
          <p className="self-end text-xs opacity-65">Targets are a positive low/high pair in the declared currency. Optional annual returns are effective decimal fractions greater than âˆ’1. No return is calculated here.</p>
          {NARRATIVES.map(field => <Field key={field} name={field} value={state.draft[field]} onChange={workspace.editThesis} multiline required={state.draft.status === 'active' && field !== 'notes'} />)}
          <button className={`${button} justify-self-start`} disabled={!state.dirty}>Save {state.thesisId ? 'new revision' : 'thesis'}</button>
        </fieldset></form>
      </section>}
      {state.latest && <>
        <section className={panel}><h3 className="text-lg font-bold">Saved revision history</h3><p className="mt-2 text-sm opacity-70">Browsing history does not change the editor above. A review is attached to the revision selected here.</p>
          <label className="mt-4 block text-sm">Revision to inspect and review<select className={fieldStyle} value={state.viewed?.id || ''} disabled={state.busy || state.reviewDirty} onChange={event => workspace.viewRevision(state.revisions.find(item => item.id === event.target.value))}>{state.revisions.map(revision => <option key={revision.id} value={revision.id} className="bg-white text-slate-900">Revision {revision.revision} Â· {revision.status} Â· {revision.created_at}</option>)}</select></label>
          {state.revisionsMore && <button className={`${button} mt-3`} disabled={state.busy} onClick={() => workspace.loadMore('revisions')}>Load older revisions</button>}
          {state.viewed && <div className="mt-5 border-t border-slate-400/30 pt-5"><RevisionDetails revision={state.viewed} /></div>}
        </section>
        <section className={panel}><h3 className="text-lg font-bold">Review revision {state.viewed.revision}</h3><p className="mt-2 text-sm opacity-70">Your decision records your judgment. Saving a review neither changes thesis status nor places a trade.</p><form className="mt-5" onSubmit={event => { event.preventDefault(); workspace.saveReview(); }}><fieldset disabled={state.busy} className="grid gap-4 md:grid-cols-2">
          <Field name="decision" value={state.review.decision} onChange={workspace.editReview} options={DECISIONS} required />
          <Field name="thesis_still_valid" value={state.review.thesis_still_valid} onChange={workspace.editReview} options={['true', 'false']} required />
          <Field name="valuation_currency" value={state.review.valuation_currency} onChange={workspace.editReview} maxLength={3} pattern="[A-Za-z]{3}" required />
          {['current_price', 'updated_expected_return'].map(field => <Field key={field} name={field} value={state.review[field]} onChange={workspace.editReview} type="number" step="any" />)}
          {REVIEW_NARRATIVES.map(field => <Field key={field} name={field} value={state.review[field]} onChange={workspace.editReview} multiline />)}
          <button className={`${button} justify-self-start`}>Save review for revision {state.viewed.revision}</button>
        </fieldset></form></section>
        <section className={panel}><h3 className="text-lg font-bold">Review history</h3><p className="mt-2 text-sm opacity-70">All reviews for this thesis, newest first. Revision numbers are shown when loaded; exact record identifiers remain available.</p>{!state.reviews.length && <p className="mt-4 text-sm">No reviews yet.</p>}{state.reviews.map(review => <details key={review.id} className="mt-4 rounded-xl border border-slate-400/30 p-4"><summary className="cursor-pointer text-sm font-semibold">{review.decision} Â· {review.reviewed_at} Â· {state.revisions.find(item => item.id === review.revision_id) ? `Revision ${state.revisions.find(item => item.id === review.revision_id).revision}` : 'Earlier revision (see identifiers)'}</summary><div className="mt-4"><ReviewDetails review={review} /></div></details>)}{state.reviewsMore && <button className={`${button} mt-4`} disabled={state.busy} onClick={() => workspace.loadMore('reviews')}>Load older reviews</button>}</section>
      </>}
    </>}
  </section>;
}
