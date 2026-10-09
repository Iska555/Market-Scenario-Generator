import { createContext, useContext, useEffect, useSyncExternalStore } from 'react';

export const SessionContext = createContext(null);
const locked = { connected: false, busy: false, error: '', epoch: 0 };
const snapshot = () => locked;
const subscribe = () => () => {};
export function usePrivateSession() {
  const session = useContext(SessionContext);
  const state = useSyncExternalStore(session?.subscribe || subscribe, session?.getSnapshot || snapshot, session?.getSnapshot || snapshot);
  return { session, ...state };
}
export function useWorkspaceConnection(controller) {
  const { session } = usePrivateSession();
  useEffect(() => session ? session.attach(controller) : () => controller.disconnect(), [session, controller]);
}
