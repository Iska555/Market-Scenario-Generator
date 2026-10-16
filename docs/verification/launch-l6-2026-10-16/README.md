# Production evidence — 2026-10-16

Supports the immutable [production progress record](../../LAUNCH_L6_PROGRESS_2026-10-16.md).
Final saved-production-browser-file acceptance is still pending at this record.

`gate-*` are fresh 2026-10-16 results: 788 backend / 174 frontend, zero skips,
97.24% coverage, ten exits 0. `deployment-identity.json` verifies the pinned image,
one 512 MiB machine and preservation of 440 earlier records. Browser screenshots,
DOM and checks refer to the actual production URL. Sanitized API summaries retain
statuses/cache policy without private portfolio paths or credentials.

`production-public.json` and history are public allowlisted records. The pg_dump,
private raw reports, owner preview and keys stay in ignored `.verification/`.
`production-restore.json` contains table hashes/counts and measured local recovery
only. Restored report replay logs are retained; the working source was unchanged.

`candidate-source.zip` retains 201 explicitly selected application/build/replay
files, with a per-file manifest. It excludes Git history, database/private reports,
server secrets, environment files, installed dependencies, backend tests/provider
fixtures and docs; it is not a database backup or complete CI checkout. Exact
runtime reproduction uses the pinned registry image and L5 image archive/runtime
freeze, not a claim that mutable base tags will rebuild identically later.

Do not rewrite these progress files after later acceptance; retain new evidence
and a new final audit instead. No hosted CI or complete master-plan claim.
