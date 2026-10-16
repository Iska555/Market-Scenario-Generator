import { useState, useSyncExternalStore } from 'react';
import { useWorkspaceConnection } from '../workspace/sessionContext.js';
import { createPublicationWorkspace, publicationRequest } from './publication.js';
import { PublicSnapshotView } from './PublicDemoPage.jsx';

const button = 'rounded-xl border border-slate-400/40 px-4 py-3 text-sm font-semibold disabled:opacity-40';
export default function PublicationControls({ apiUrl, portfolioId }) {
  const [workspace] = useState(() => createPublicationWorkspace((path, body, key) => publicationRequest(apiUrl, key, path, body), portfolioId));
  useWorkspaceConnection(workspace);
  const state = useSyncExternalStore(workspace.subscribe, workspace.getSnapshot, workspace.getSnapshot);
  if (!state.connected) return null;
  const previous = [...(state.history?.events || [])].reverse().find(event => event.action === 'publish');
  const available = state.history?.events.at(-1)?.action === 'publish';
  return <section className="space-y-4 rounded-2xl border border-slate-400/30 p-5" aria-label="Owner demonstration publication">
    <h3 className="text-lg font-semibold">Publish the isolated synthetic demonstration</h3>
    <p className="text-sm">Review the complete public preview, then deliberately publish its immutable version. Research selection does not remove closed losses or performance. Only original unchanged demo evidence is eligible.</p>
    <fieldset disabled={state.busy || state.uncertain} className="flex flex-wrap gap-5"><legend className="mb-2 text-sm font-semibold">Original fictional research to include</legend>{[['harbor','Harbor Workshop'],['orchard','Orchard Systems · closed loser']].map(([key,label]) => <label className="flex items-center gap-2 text-sm" key={key}><input type="checkbox" checked={state.selection.includes(key)} onChange={event => workspace.editSelection(event.target.checked ? [...state.selection,key] : state.selection.filter(value => value !== key))} />{label}</label>)}</fieldset>
    <label className="block text-sm">Public correction / withdrawal reason<textarea className="mt-2 w-full rounded-xl border border-slate-400/40 bg-transparent p-3" rows="3" maxLength="500" value={state.reason} disabled={state.busy || state.uncertain} onChange={event=>workspace.editReason(event.target.value)} /></label>
    <p className="text-xs opacity-75">This reason will be public. Withdrawal hides version pages/downloads, retains private audit records and public lifecycle metadata, and cannot recall copies already saved by visitors.</p>
    <div className="flex flex-wrap gap-3"><button className={button} disabled={state.busy || state.uncertain || !state.history} onClick={workspace.preview}>Prepare owner preview</button><button className={`${button} bg-emerald-800 text-white`} disabled={state.busy || state.uncertain || !state.preview || (previous && !state.reason.trim())} onClick={workspace.publish}>{previous ? 'Publish disclosed new version' : 'Publish reviewed demo version'}</button><button className={button} disabled={state.busy || state.uncertain || !available || !state.reason.trim()} onClick={workspace.withdraw}>Withdraw public availability</button><button className={button} disabled={state.busy || state.uncertain} onClick={workspace.reload}>Reload publication history</button>{state.uncertain && <button className={button} disabled={state.busy} onClick={workspace.retry}>Retry same captured action</button>}</div>
    {state.busy && <p role="status">Working with owner publication…</p>}{state.error && <p role="alert">{state.error}</p>}
    {state.result && <p role="status">Published version <a className="underline" href={`/demo/${state.result.version}`} target="_blank" rel="noreferrer">{state.result.version}</a> · content SHA-256 <span className="break-all">{state.result.content_sha256}</span></p>}
    {state.history && <p className="text-sm">Publication sequence {state.history.sequence} · {available ? 'Public version available' : 'No public version currently available'}. <a className="underline" href="/demo" target="_blank" rel="noreferrer">Open anonymous public page</a></p>}
    {state.preview && <details open><summary className="font-semibold">Review captured public preview · sequence {state.preview.expected_sequence}</summary><div className="mt-4"><PublicSnapshotView envelope={state.preview.envelope} /></div></details>}
  </section>;
}
