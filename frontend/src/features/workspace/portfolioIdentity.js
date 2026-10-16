import { accountingRequest } from '../ledger/ledger.js';

export const DEMO_LABEL = 'Demonstration portfolio — synthetic data; no real money invested';
export async function demoRequest(base, key, id, action, fetcher = fetch) {
  const response = await fetcher(`${base.replace(/\/$/, '')}/api/portfolio-identity/portfolios/${encodeURIComponent(id)}/demo/${action}`, {
    method: action === 'load' ? 'POST' : 'GET', cache: 'no-store', headers: { 'X-Research-Key': key },
  });
  if (!response.ok) throw Object.assign(new Error('Original demo request failed. Use an empty GBP demo or reload its unchanged fixture.'), { status: response.status });
  return response.json();
}
export function modeLabel(portfolio) {
  const mode = portfolio?.identity?.mode;
  if (mode === 'demo') return DEMO_LABEL;
  if (mode === 'paper') return 'Prospective paper portfolio — hypothetical; no real money invested';
  if (mode === 'real') return 'Real-account record — broker reconciliation not verified';
  return 'Private / unclassified — no verified personal track record';
}

// Additive private adapter; legacy accounting/report contracts remain unchanged.
export async function portfolioRequest(base, key, path, options = {}, fetcher = fetch) {
  if (path !== '/portfolios' || (options.method && options.method !== 'POST' && options.method !== 'GET')) return accountingRequest(base, key, path, options, fetcher);
  const creating = options.method === 'POST';
  if (creating && options.body.mode && !['demo', 'unclassified'].includes(options.body.mode)) throw new Error('This mode requires a separately accepted creation workflow.');
  if (creating && options.body.mode !== 'demo') {
    const body = { ...options.body };
    delete body.mode;
    return accountingRequest(base, key, path, { ...options, body }, fetcher);
  }
  const body = creating ? { id: options.body.id, name: options.body.name, base_currency: options.body.base_currency, mode: options.body.mode } : null;
  let response;
  try {
    response = await fetcher(`${base.replace(/\/$/, '')}/api/portfolio-identity/portfolios`, {
      method: creating ? 'POST' : 'GET', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Research-Key': key },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch { throw new Error('Portfolio identity service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error('Portfolio identity request failed. Reload before retrying the same identity.'), { status: response.status });
  return response.json();
}
