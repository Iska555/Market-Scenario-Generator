# Synthetic demonstration operations — 2026-10-15

This is the bounded synthetic demonstration release under PLAN.md. Production
promotion and final resource cleanup must be evidenced in a subsequent launch
record; this document alone does not establish that they happened.

## Topology and access

One Fly shared-CPU 512 MiB machine serves the compiled React frontend and FastAPI
on the same HTTPS origin. The explicit public entry is `/demo`; `/` is the private
workspace. UUID version URLs have the same synthetic title/description metadata.
Only `/api/public/demo` and its history/version/download adapters expose reviewed
allowlisted snapshots. Anonymous private requests require the owner key; provider
simulations are disabled in this small hosted profile. Existing offline/local
analytics remain available. This is not a multi-user hosted service.

| Resource | Release target |
| --- | --- |
| Production Fly app | `stochastic-market-simulator`, `iad` |
| Temporary staging Fly app | `market-scenario-demo-staging`, `iad`, visible staging banner |
| Database | Neon Free project `market-scenario-synthetic-demo`, PostgreSQL 17, AWS us-east-1 |
| Production branch | `br-nameless-paper-b7uis4a8` |
| Isolated staging branch | `br-gentle-mountain-b79p7vir` |
| Schema head | `20261014_07` |

The branches and owner keys are separate. No staging publication IDs/history are
imported into production. No other Fly app or Neon project is part of this release.
`DATABASE_URL` and independent random `RESEARCH_API_KEY` values belong in Fly
server secrets only. Never use `VITE_` variables for credentials. Local protected
key recovery files are Windows CurrentUser DPAPI, ignored, and not portable
backups; losing the Windows identity requires an explicit server-key rotation.
Keep an owner-controlled secure credential recovery method outside Git.

## Candidate and deployment

Accepted-candidate identity pending final staging checks:

```
registry.fly.io/stochastic-market-simulator@sha256:e551fec3da3af812a9cc5fbdc92a365b87e506364d9b39a800f1af3ff310efd4
```

Calculation source SHA-256:
`5b6a3e874c3abf945d6a3c1fcbde6dba6cb72067d76a6f742dfa7bd9120a1afe`.
Image Python 3.12.15 differs from local acceptance Python 3.12.14; replay with the
image or the matching exact runtime. Never edit a report's declared runtime/hash.

From the repository root, with the authenticated official Fly CLI on PATH:

```powershell
$candidate = 'registry.fly.io/stochastic-market-simulator@sha256:e551fec3da3af812a9cc5fbdc92a365b87e506364d9b39a800f1af3ff310efd4'
fly deploy --image $candidate --config deploy/fly.staging.toml --ha=false --strategy immediate
fly ssh console -a market-scenario-demo-staging -C 'python -m alembic upgrade head'
```

For production use `deploy/fly.demo.toml` and the production app explicitly.
Provision the correct branch URL/key/origin first. Migrations are an explicit
operator action, never application startup. First deployment has an empty public
channel until an authenticated owner deliberately creates/loads an isolated demo,
captures the reviewed allowlist and publishes it. Publication intent IDs must be
retained for safe exact retries. Never create another portfolio after a network
timeout without checking the original intent.

## Limits, monitoring and incident response

One worker, numerical-library threads limited to one; Fly concurrency soft 4/hard
8, application active request cap 8, Uvicorn cap 16. Public API requests share a
fixed rolling process-wide budget of 120/minute, independent of IP headers; 429
includes Retry-After 60. This trades availability during a burst for bounded
resources; it is not a distributed DDoS or billing protection. API writes have a
1 MiB body limit and absolute 10 second body-read timeout. Public/private HTML/API
responses use no-store; hashed assets alone get immutable caching.

Fly's 60 second `/api/health` check is liveness and does not wake Neon.
`/api/ready` checks database/schema readiness on demand. Check it and the public
version/hash after each deployment, publication, restart and incident. Review Fly
health, restarts/OOM, CPU/memory and request logs during operation. Application
request logs retain only category, status and elapsed time; no URL/query, owner
header, payload or portfolio IDs. Fly infrastructure can log the account email
for SSH sessions: redact those fields before retaining shareable evidence.

Repeated 5xx, failed readiness, an unexpected content hash or a missing history
event is an incident: stop new publication, preserve logs/state, verify branch and
schema, and redeploy the known image/configuration. A frontend/configuration fault
can fail independently of a previously healthy process. No external alert delivery
or unattended monitoring schedule is claimed by this release.

## Backup, retention and restoration

The fixture/source ZIP is reproducibility evidence; it does not replace a database
backup. Keep a private PostgreSQL custom-format `pg_dump` of the demo database
after every accepted publication/lifecycle change and before a migration, together
with exact table fingerprints, immutable public envelopes/history, original fixture,
three raw reports, matching source, migrations, lockfiles and runtime/image manifest.
Retain dated accepted backups and evidence without overwriting prior versions.
Keep private dumps and keys out of public downloads and committed browser evidence.
The original synthetic accepted evidence is retained indefinitely; a future real
account requires its own privacy/retention policy and separate backup boundary.

Neon Free's short recovery window (currently up to 6 hours/1 GB) is useful for
recent mistakes, not durable archival retention. The operating RPO target is the
last accepted publication: freeze changes until its backup is verified. Target
recovery within one hour for this tiny demo, subject to operator/provider access;
measured rehearsals are observations, not an availability SLA. No daily backup job
or off-device disaster-recovery copy is claimed.

Restore into a **new separate database/branch**, using `pg_restore --exit-on-error
--no-owner --no-privileges`; never restore over the only original. Compare every
table's sorted canonical row hash/count, ledger/publication identities, fixture
receipt and public envelope. Regenerate selected reports against the restored data
and replay with compatible source/runtime. Do not expose a recovered branch until
its branch/key isolation and full public/private checks pass. Local restoration of
the accepted synthetic history was measured on 2026-10-14; hosted restoration must
be separately evidenced, not inferred from that result.

## Rollback

Preserve the database and immutable publication history. Restore the known pinned
image **and** its saved configuration/origins/secret references. Use the same
`fly deploy --image ... --ha=false --strategy immediate` command. Verify readiness,
all table fingerprints, public version/hash/history and anonymous private rejection.
Do not downgrade the schema, delete a correction or relabel the portfolio to make
old code boot. The historical pre-launch Fly v3 image predates the accepted public
boundary and is not an approved public rollback target. If the known candidate is
unsafe, keep it unavailable while repairing the fault instead of exposing old code.

## Cost boundary

The owner authorized this release at at most US$5/month, preferably free. Neon
remains on Free; never enable a paid plan/managed Fly database/dedicated IPv4.
Use one permanent 512 MiB shared Fly machine, min-running 0, auto-stop/start,
shared IPv4 and no volume. Remove this task's temporary builder/staging compute
after archiving evidence. Do not alter unrelated apps to reduce this release bill.

Under Fly's effective 2026-10-01 rates, 256 MiB shared compute is about $2.19/month
and an additional 256 MiB about $1.50/month: approximately **$3.69/month** if the
512 MiB machine runs continuously, plus egress, any stopped rootfs storage,
temporary build/staging usage and applicable taxes. North America/Europe egress
is currently $0.02/GB. Neon Free currently includes 100 CU-hours/project/month,
1 GB storage and 5 GB egress with scale-to-zero. Verify pricing and actual usage
before changing topology: [Fly rate update](https://fly.io/pricing-update/),
[Fly billing](https://fly.io/docs/about/billing/), [Neon pricing](https://neon.com/pricing).

This estimate is **not a guaranteed hard billing cap**, and it excludes unrelated
account projects. Review attributed month-to-date usage and projected month-end
cost at launch and during operation; stop this release's machine if its projected
total approaches $5, allowing margin for storage/egress/tax. Stop is reversible
but may auto-start from traffic: disable auto-start or remove public service routing
for a deliberate spending suspension. Preserve its database/evidence. Never claim
that an application rate limiter or auto-stop enforces the provider's dollar cap.
