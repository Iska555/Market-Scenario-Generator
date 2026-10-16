# Launch L5 progress record — 2026-10-16

**L5 remains in progress. Production has not been promoted.** This dated record
preserves completed operations/staging evidence while the hosted saved-browser-
download gate remains open. It does not replace any earlier audit or accept L6.

Implemented release transport in `backend/src/release.py`: bounded bodies and
absolute read timeout, fixed public request budget and active-request cap,
secret-free application request logs, no-store responses, liveness/readiness,
startup validation and same-origin static/deep-version hosting. The root multi-
stage Dockerfile builds the existing React/FastAPI stack, runs non-root, uses one
worker/thread profile and disables heavy private provider simulations on the
512 MiB hosted instance. Those local/offline features remain available separately.
No financial calculation or historical report contract was changed for hosting.

Actual target: Fly app `market-scenario-demo-staging` in iad, one shared CPU /
512 MiB, HTTPS, min-running 0 and auto-stop/start. Neon Free project
`market-scenario-synthetic-demo` has distinct staging and production branches.
Only the staging branch has been migrated/loaded/published. The existing production
Fly app remains on its historical stopped image; new server secrets/origin are
staged for future deployment. Other account projects/apps were untouched.

Exact candidate:
`registry.fly.io/stochastic-market-simulator@sha256:e551fec3da3af812a9cc5fbdc92a365b87e506364d9b39a800f1af3ff310efd4`.
Backend source SHA-256:
`5b6a3e874c3abf945d6a3c1fcbde6dba6cb72067d76a6f742dfa7bd9120a1afe`.
Deployed Python 3.12.15 / PostgreSQL 17.11. The source/assets archive extracted
from that image has 115 explicit files, matching checkout backend code, plus its
runtime freeze. Its SHA-256 is
`f54cb3fbe0dcb2af42b929eb57256db581b2fa7c9034cfa526ef7b6dc4def724`.
It excludes OS image layers, secrets, database backups, logs and private reports.
The pinned OCI image supplies the complete deployed runtime; do not infer a future
rebuild of mutable base tags will be byte-identical.

Verification completed:

- Final implementation gate actually ran **2026-10-14**, run4: **788 backend /
  174 frontend tests, zero skips, 97.24% coverage, all ten exits 0**. No subsequent
  application-code change is claimed. Hosted CI was not run. Code/assets retained
  on 2026-10-16 match this candidate and checkout.
- Hosted owner API deliberately created/loaded the isolated original demo;
  identical retry, preview/publication, stale-preview rejection, correction,
  withdrawal and republication passed. All earlier withdrawn version/download
  routes remain 410. Public mode/allowlist/hash/NAV £10,516, negative TWR, 48 closes
  and complete −US$400 closed loser agree with original calculations. Independent
  production history has not been created.
- Anonymous private/read/write/calculation probes reject access; hosted owner
  provider simulations return explicit 503. HTTPS, readiness, no-store and exact
  sanitized HTTP download payload passed. Public UI shows the staging banner,
  synthetic metadata/claims, period dates, negative values, closed loss, research,
  methodology and disclosed history. Desktop 1280×900 and mobile 390×844 had document
  widths 1265/375; keyboard research navigation and old-version unavailable view
  were exercised. The final restored deep URL rendered correctly after recovery.
- Three hosted raw reports replayed **inside the exact deployed image**, with no
  database/provider access during replay. Local replay first correctly rejected
  the 3.12.15 versus 3.12.14 patch-version mismatch; reports/guards were not edited.
- Local synthetic backup restoration on 2026-10-14 compared all table values,
  counts/identities, receipt and public envelope and regenerated/replayed three
  reports. A second **actual hosted staging pg_dump**, explicitly approved by the
  owner, was downloaded privately on 2026-10-15 and restored into a new separate
  local database on 2026-10-16. All table fingerprints/counts match in UTC.
  Dump: 54,815 bytes, SHA-256
  `52af6bb5f759dd83bf0cb1d756b31f8213ce93acd5abb83a5ed0e11c856d34f3`.
  Verified local restore/comparison took **0.469 seconds**; backup-transfer duration
  was not retained. Regenerated restored performance, contribution and comparison
  reports all replay. This tiny local rehearsal is not a production SLA.
- Reversible staging-only fault injection set a missing frontend directory. The
  server failed with a visible RuntimeError; an external probe timed out rather
  than returning the initially expected 503. A finally block redeployed the pinned
  candidate/configuration. Fly healthy startup/checks returned; all before/after
  database fingerprints are identical. No schema downgrade/history deletion.
  Retained logs show failure at 16:42:50Z and health passing at 16:43:23Z on
  2026-10-15; that 33-second logged interval is not a measured full recovery time.
- Actual staging body limit returned 413; 12 reads at concurrency three all
  succeeded (0.156/0.328/1.219 s min/median/max). The fixed public budget returned
  429 with Retry-After 60. This is bounded representative use, not a capacity/load
  guarantee. Observed Uvicorn RSS/high-water was 242,288 kB on the 512 MiB machine.
- Image code/assets scan found neither server owner key nor database URI. Shared
  acceptance logs redact Fly SSH account-email fields; app request logs contain
  category/status/elapsed only. Keys and database URI were never saved in plaintext
  evidence. Private database dumps, keys and hosted raw reports remain ignored.
- **392 pre-L5 records preserved** (living README/architecture/suggestions keep byte
  prefixes). Existing uncommitted work was preserved; no commit/push is claimed.
  The temporary builder created for this launch and its cache were removed on
  2026-10-16 to avoid ongoing storage costs; accepted registry image remains.

Observed verification defects were kept distinct from application defects: Fly's
optional `--autostop` value required `=off`; the initial flag form failed without
changing the machine. The local PostgreSQL restart initially omitted its custom
port; it now explicitly binds 127.0.0.1:55439. A new restore database's empty default
public schema had to be removed before pg_restore created the backed-up schema;
the original was never dropped. Timestamp hashes needed UTC session formatting.
The rate-probe harness needed case-insensitive HTTP-header lookup. Normal Fly
authentication and random protected keys resolved earlier approval-review issues.
Automatic approval review initially rejected hosted private-dump transfer; the
owner subsequently explicitly approved that exact local destination/restore.

Remaining acceptance gate: in-app browser download automation repeatedly stalled,
including a 1,631-second tool call despite a requested short timeout. No matching
saved hosted browser file was found. HTTP download payload verification and prior
L4 local saved-download acceptance do **not** establish this hosted delivery check.
The owner has been asked to save the public staging download in Downloads; inspect
that actual file against the immutable typed envelope/hash before accepting L5.

Cost target is one permanent 512 MiB Fly machine (about $3.69/month continuously
running before egress/tax/temporary usage) plus Neon Free. No guaranteed provider
dollar cap or whole-account cost promise is established. Provider simulations stay
disabled. See [operations](RELEASE_OPERATIONS.md) for retention, RPO/RTO targets,
manual monitoring, secret recovery, rollback and cost suspension controls.

Next unfinished step: **L5.3 hosted saved-browser-download acceptance**, then final
L5 dated acceptance and L6 evidence/promotion/smoke checks. Deferred advanced
analytics, prospective paper operation and actual broker integration remain
unfinished and are outside this bounded synthetic release.

[Retained evidence](verification/launch-l5-2026-10-16/README.md).
