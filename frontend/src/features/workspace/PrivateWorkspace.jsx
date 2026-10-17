import { useEffect, useRef, useState } from 'react';
import { LockKeyhole, UnlockKeyhole } from 'lucide-react';
import { researchRequest } from '../thesis/thesis.js';
import { createPrivateSession } from './session.js';
import { SessionContext, usePrivateSession } from './sessionContext.js';

export function PrivateWorkspaceProvider({ apiUrl, children }) {
  const [session] = useState(() => createPrivateSession(key => researchRequest(apiUrl, key, '/securities?limit=1&offset=0')));
  useEffect(() => () => session.lock(), [session]);
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export default function PrivateWorkspaceControl() {
  const { session, connected, busy, error, accessOpen } = usePrivateSession();
  const [draft, setDraft] = useState('');
  const keyInput = useRef(null);
  useEffect(() => { if (accessOpen) keyInput.current?.focus(); }, [accessOpen]);
  const lock = () => { setDraft(''); session?.lock(); };
  return <section className="workspace-access" aria-label="Private workspace access">
    <div className="workspace-access-status"><span className="workspace-access-label">{connected ? <UnlockKeyhole size={15} aria-hidden="true" /> : <LockKeyhole size={15} aria-hidden="true" />}<strong>{connected ? 'Workspace connected' : 'Private workspace'}</strong></span>
      <div className="workspace-access-actions"><a href="/demo">View demonstration ↗</a>{connected || busy ? <button type="button" onClick={lock}>Lock workspace</button> : <button type="button" aria-expanded={Boolean(accessOpen)} onClick={() => { setDraft(''); if (accessOpen) session?.dismissAccess(); else session?.requestAccess(); }}>Unlock private workspace</button>}</div>
    </div>
    {!connected && accessOpen && <form className="workspace-unlock-form" onSubmit={event => { event.preventDefault(); const candidate = draft.trim(); setDraft(''); void session?.unlock(candidate); }}>
      <label>Private workspace key<input ref={keyInput} type="password" autoComplete="off" autoCapitalize="none" spellCheck={false} required value={draft} disabled={busy} onChange={event => setDraft(event.target.value)} aria-describedby="workspace-key-help" /></label>
      <button disabled={busy || !session}>{busy ? 'Unlocking…' : 'Unlock workspace'}</button>
      <p id="workspace-key-help">Use the owner access key, not a broker password. It stays in this tab until you lock or refresh.</p>
      <details className="workspace-key-help"><summary>Where do I get a key?</summary><p>The site operator holds the private key. There is no public sign-up. Visitors can use <a href="/demo">the demonstration portfolio</a> without a key. If you own this deployment, follow the private-access instructions in the project README.</p></details>
    </form>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

export function WorkspaceConnectionNotice({ workspace }) {
  const { session, connected } = usePrivateSession();
  return <p className="mt-4 text-sm opacity-75">{connected ? <>Opening private records. <button type="button" className="underline" onClick={() => session.reconnect(workspace)}>Retry loading</button></> : <button type="button" className="font-semibold underline underline-offset-4" onClick={() => session?.requestAccess()}>Unlock private workspace to continue →</button>}</p>;
}
