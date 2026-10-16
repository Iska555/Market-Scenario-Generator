export const DEMO_LABEL = 'Demonstration portfolio — synthetic data; no real money invested';
export async function readPublicPreview(base, signal, fetcher = fetch) {
  const response = await fetcher(`${base.replace(/\/$/, '')}/api/public-preview/original`, { cache: 'no-store', signal });
  if (!response.ok) throw new Error(response.status === 404 ? 'Local preview is not enabled.' : 'The original demonstration preview is unavailable.');
  const data = await response.json();
  if (data?.status !== 'local_preview' || data?.snapshot?.mode !== 'demo' || data?.snapshot?.schema_version !== 'demo_snapshot_v1' || data.snapshot.label !== DEMO_LABEL || data.published_at !== null) throw new Error('The demonstration identity could not be verified.');
  return data;
}
export const formatPercent = metric => metric?.value == null || !Number.isFinite(metric.value) ? `Unavailable · ${(metric?.reason || 'not supplied').replaceAll('_', ' ')}` : `${(metric.value * 100).toFixed(2)}%`;
export const formatMoney = (value, currency = 'GBP') => value == null || value === '' || !Number.isFinite(Number(value)) ? 'Unavailable' : new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(value));
