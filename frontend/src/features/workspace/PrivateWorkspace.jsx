import { useEffect, useState } from 'react';
import { researchRequest } from '../thesis/thesis.js';
import { createPrivateSession } from './session.js';
import { SessionContext, usePrivateSession } from './sessionContext.js';

export function PrivateWorkspaceProvider({ apiUrl, children }) {
  const [session] = useState(() => createPrivateSession(key => researchRequest(apiUrl, key, '/securities?limit=1&offset=0')));
  useEffect(() => () => session.lock(), [session]);
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export default function PrivateWorkspaceControl() {
  const { session, connected, busy, error } = usePrivateSession();
  const [draft, setDraft] = useState('');
  const [expanded, setExpanded] = useState(false);
  const lock = () => { setDraft(''); setExpanded(false); session?.lock(); };
  return <section className="workspace-access" aria-label="Private workspace access">
    <div className="workspace-access-status"><span>Private workspace <strong>{connected ? '● Connected' : '○ Locked'}</strong></span>
      {connected || busy ? <button type="button" onClick={lock}>Lock workspace</button> : <button type="button" aria-expanded={expanded} onClick={() => { setDraft(''); setExpanded(!expanded); }}>Unlock private workspace</button>}
    </div>
    {!connected && expanded && <form className="workspace-unlock-form" onSubmit={event => { event.preventDefault(); const candidate = draft; setDraft(''); void session?.unlock(candidate); }}>
      <label>Private workspace key<input type="password" autoComplete="off" autoCapitalize="none" spellCheck={false} required value={draft} disabled={busy} onChange={event => setDraft(event.target.value)} aria-describedby="workspace-key-help" /></label>
      <button disabled={busy || !session}>{busy ? 'Unlocking…' : 'Unlock workspace'}</button>
      <p id="workspace-key-help">This key unlocks your private Investment Management Workspace. It is not your broker password or market-data credential. It stays in memory only; refresh requires unlocking again.</p>
    </form>}
    {error && <p role="alert">{error}</p>}
    {connected && <p className="workspace-access-note">All private modules share this connection. Locking clears unsaved private work; saved records remain on the server.</p>}
  </section>;
}

export function WorkspaceConnectionNotice({ workspace }) {
  const { session, connected } = usePrivateSession();
  return <p className="mt-4 text-sm opacity-75">{connected ? <>Opening private records. <button type="button" className="underline" onClick={() => session.reconnect(workspace)}>Retry loading</button></> : 'Unlock private workspace above to access this area.'}</p>;
}
