# Deliberate synthetic publication

Owner `/api/publication` commands require the private key and a configured database.
Preview takes a fresh UUID, an explicit demo portfolio UUID and original research
keys. It captures the allowlisted snapshot and channel event sequence; it does not
publish. Publish takes an idempotent intent UUID and captured preview UUID. The
server checks unchanged original evidence, calculation code, content and sequence.
Changed identities/payloads with the same UUID conflict. No client-supplied financial
snapshot is accepted. The public channel remains bound to one isolated demo.

Publication uses additive immutable database rows and append-only events. Channel
row locking serializes owners; portfolio locking followed by SHARE source-table
locks prevents a mixed ledger/research snapshot. This coarse fence is proportionate
to one small owner-managed demo; it briefly blocks source writes and is not a
multi-user publishing architecture. Original receipt checks prohibit changes to
the bounded fixture; arbitrary edited research/ledger publication is deferred.

Each subsequent version identifies the immediately previous public version and a
public reason. Selected research can change; complete performance/closed losses
remain. Public reasons are explicitly authored public material; never enter secrets.
Withdrawal requires the current sequence and a public reason. It removes all earlier
content from public reads/downloads; lifecycle metadata stays visible. A fresh later
version restores only its own content. Private retry/audit reads retain prior content.
Copies already saved or retained by third parties cannot be recalled.

Anonymous `/api/public/demo`, `/history`, `/versions/{public-version}` and its
`/download` expose the allowlist/lifecycle only, with no-store responses. Draft IDs
do not resolve as public versions. Downloads carry mode, original synthetic label,
disclosures and hashes. Database errors are generic; private draft/source metadata
never goes into public envelopes. Owner controls clear on lock/navigation/refresh;
uncertain retries retain the exact action/body/UUID in memory.

Production must enable `PUBLIC_RELEASE_MODE=1`, disable the optional fixed local
preview, configure owner secrets server-side and route public HTML to its generated
synthetic metadata. Release mode gates legacy simulation endpoints with owner access.
The existing private workspace remains usable with its in-memory owner session.
See [L4 audit](LAUNCH_L4_AUDIT.md); localhost evidence is not hosted acceptance.
