import { assertV3Response } from './scenarioContract.js';

// Deployed builds use the site's /api proxy. No browser-to-cloud CORS dependency.
export function apiBase(dev, configured) {
  return dev ? (configured?.replace(/\/$/, '') ?? 'http://localhost:8000') : '';
}

export async function postScenario(base, path, body, { signal, fetcher = fetch, timeoutMs = 60000 } = {}) {
  const timeout = AbortSignal.timeout(timeoutMs);
  try {
    const response = await fetcher(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      if (response.status === 401) throw new Error('The public Risk Lab is misconfigured. Please contact the site operator.');
      const detail = typeof error.detail === 'string' ? error.detail : Array.isArray(error.detail) ? error.detail.map(item => item.msg).join('; ') : '';
      throw new Error(detail || `Simulation unavailable (${response.status}). Please retry.`);
    }
    return assertV3Response(await response.json());
  } catch (error) {
    if (timeout.aborted) throw new Error('The simulation timed out. Try fewer assets or a shorter history, then retry.');
    if (error instanceof TypeError) throw new Error('Cannot reach the simulation service. Check your connection and retry.');
    throw error;
  }
}
