// Secrets live only in this closure, never in snapshots or browser persistence.
export function createPrivateSession(validate) {
  let key = '';
  let generation = 0;
  let state = { connected: false, busy: false, error: '', epoch: 0, accessOpen: false };
  const controllers = new Set();
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const session = {
    getSnapshot: () => state,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    requestAccess() { update({ accessOpen: true }); },
    dismissAccess() { update({ accessOpen: false }); },
    lock() {
      ++generation; key = '';
      controllers.forEach(controller => controller.disconnect());
      update({ connected: false, busy: false, error: '', epoch: state.epoch + 1, accessOpen: false });
    },
    async unlock(candidate) {
      if (state.connected) session.lock();
      else { ++generation; key = ''; controllers.forEach(controller => controller.disconnect()); update({ busy: false, error: '' }); }
      if (!candidate) { update({ error: 'Enter your private workspace key.' }); return; }
      const token = generation;
      update({ busy: true });
      try {
        await validate(candidate);
        if (token !== generation) return;
        key = candidate;
        update({ connected: true, busy: false, accessOpen: false });
        controllers.forEach(controller => { void controller.connect(key); });
      } catch (error) {
        if (token !== generation) return;
        key = '';
        update({ busy: false, error: error.status === 401 ? 'Private workspace key was not accepted.' : 'Private workspace is unavailable. Check that the service is configured and reachable, then retry.' });
      }
    },
    attach(controller) {
      controllers.add(controller);
      if (state.connected) void controller.connect(key);
      return () => { controllers.delete(controller); controller.disconnect(); };
    },
    reconnect(controller) { if (state.connected && controllers.has(controller)) void controller.connect(key); },
    authorize(action) { return action(state.connected ? key : ''); },
  };
  return session;
}
