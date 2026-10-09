const initial = () => ({ connected: false, busy: false, error: '', portfolios: [], selectedId: '', ledger: null, securities: {} });
export function createOverview(request, readSecurity) {
  let state = initial();
  let key = '';
  let generation = 0;
  const listeners = new Set();
  const update = patch => { state = { ...state, ...patch }; listeners.forEach(listener => listener()); };
  const store = {
    getSnapshot: () => state,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    disconnect() { ++generation; key = ''; state = initial(); listeners.forEach(listener => listener()); },
    async connect(candidate) {
      store.disconnect(); key = candidate;
      const token = generation;
      update({ busy: true });
      try {
        const portfolios = await request('/portfolios', {}, key);
        if (token !== generation) return;
        update({ connected: true, busy: false, portfolios });
        if (portfolios.length) await store.select(portfolios[0].id);
      } catch { if (token === generation) update({ busy: false, error: 'Account records are unavailable. Retry when the private accounting service is ready.' }); }
    },
    async select(id) {
      if (!state.connected || !state.portfolios.some(portfolio => portfolio.id === id)) return;
      const token = ++generation;
      const sessionKey = key;
      update({ selectedId: id, busy: true, error: '', ledger: null, securities: {} });
      try {
        const ledger = await request(`/portfolios/${encodeURIComponent(id)}/state`, {}, sessionKey);
        if (token !== generation) return;
        update({ ledger });
        const entries = await Promise.all((ledger.positions || []).map(async position => {
          try { return [position.security_id, await readSecurity(position.security_id, sessionKey)]; }
          catch { return [position.security_id, null]; }
        }));
        if (token === generation) update({ securities: Object.fromEntries(entries), busy: false });
      } catch { if (token === generation) update({ busy: false, error: 'Holdings are unavailable. Reload the recorded account.' }); }
    },
  };
  return store;
}
