export const sourceUrl = 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Developed_5_Factors_Daily_CSV.zip';
export const emptySource = () => ({ csv: '', retrieved: '', published: '', publicationNote: '', note: '' });

export function sourceBody(source, draft) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.start) || !/^\d{4}-\d{2}-\d{2}$/.test(draft.end) || draft.end < draft.start) throw new Error('Choose the source review window using the reporting dates.');
  if (!source.csv.trim() || new TextEncoder().encode(source.csv).length > 2000000) throw new Error('Supply the developed five-factor daily CSV, at most 2 MB.');
  for (const timestamp of [source.retrieved, ...(source.published ? [source.published] : [])]) if (!/(Z|[+-]\d{2}:\d{2})$/.test(timestamp) || !Number.isFinite(Date.parse(timestamp))) throw new Error('Source timestamps need an ISO date and time with a UTC offset.');
  if (!source.note.trim() || (source.published && !source.publicationNote.trim())) throw new Error('Add a review note and evidence for any declared publication time.');
  return { csv_text: source.csv, start: draft.start, end: draft.end, metadata: { source_url: sourceUrl, retrieved_at: source.retrieved, published_at: source.published || null, publication_note: source.publicationNote, review_note: source.note } };
}

export async function sourceReviewRequest(base, key, id, body, fetcher = fetch) {
  let response;
  try { response = await fetcher(`${base.replace(/\/$/, '')}/api/factors/portfolios/${encodeURIComponent(id)}/source-review`, { method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Research-Key': key }, body: JSON.stringify(body) }); }
  catch { throw new Error('The private source review service could not be reached.'); }
  if (!response.ok) throw Object.assign(new Error('Source review failed.'), { status: response.status });
  return response.json();
}
