# Production launch progress — 2026-10-16

**Production is deployed and the synthetic demonstration is public. Final L6
acceptance remains open solely for inspection of the browser-saved production
snapshot.** Preserve this dated progress record after later acceptance.

Public URL: https://stochastic-market-simulator.fly.dev/demo

Production version: `51b34ac3-3c73-43b6-b4f8-253eb70ba7a5`.
Publication: `2026-10-16T15:53:15.775651Z`.
Content SHA-256: `54f4a29668a7cc4a0478414c8c134ef262376615c7a393d3129f334442801e69`.
Calculation source SHA-256:
`5b6a3e874c3abf945d6a3c1fcbde6dba6cb72067d76a6f742dfa7bd9120a1afe`.
Pinned deployed image:
`registry.fly.io/stochastic-market-simulator@sha256:e551fec3da3af812a9cc5fbdc92a365b87e506364d9b39a800f1af3ff310efd4`.

The L5-accepted image was promoted without rebuilding. Explicit additive Alembic
migrations initialized the separate production Neon branch at `20261014_07`.
Owner API created a new `demo` identity in that empty database, loaded the original
fixture with exact retry, captured/reviewed both fictional research histories and
deliberately published the first immutable version. Production has one publication
event; its private portfolio/intent identities differ from staging. No staging,
paper, legacy or future real history was imported or spliced into this release.

Fresh final gate on **2026-10-16**, run1: **788 backend / 174 frontend tests, zero
skips, 97.24% coverage, all ten configured checks exited 0**, with real disposable
PostgreSQL and project-local dependencies. Hosted CI/full alternate Python matrix
were not run. Existing Starlette deprecation/large frontend bundle warnings remain.
The new local build is verification output; production remains the pinned accepted
same-origin image, rather than the local build's default API URL.

Actual public browser checks passed without entering owner credentials: synthetic
labels and metadata, current publication/fixture/creation dates, negative TWR,
complete closed loser, both research histories, correction journal, methodology,
desktop 1280×900 and mobile 390×844 with document widths 1265/375, keyboard research
link and deep-version metadata. Production has no staging banner. The download
link was exercised, but the in-app browser has not delivered a saved production
file. The HTTP download payload exactly equals the typed immutable public envelope,
with no-store and private fields excluded. The previously accepted normal-browser
saved **staging** file remains distinct evidence; it is not relabelled as production.

Production anonymous private/read/write/calculation checks reject access. Owner
access works, while resource-heavy provider simulations explicitly return 503 in
this 512 MiB profile. A production restart returned healthy and retained the same
public version/hash and access protections. No history was deleted or downgraded.

An actual custom-format production pg_dump, containing only this newly generated
original synthetic database, is retained privately under ignored `.verification/`:
53,532 bytes; SHA-256
`6ca58fb08e00039b32fa5425e01edb991791879e875e9304aa7f49080f44ddcc`.
It restored into a new separate local database with **every table's values,
counts and identities matching**. Backup took 9.656 s; verified local restore /
comparison took 0.672 s. Regenerated performance/contribution/comparison reports
all replay from the working code and an independently extracted 201-file source /
build/replay bundle. Exact-image replay and the 115-file deployed code/assets /
runtime archive remain under accepted L5 evidence. These tiny-data observations
are not an availability or capacity SLA. Neither dump nor private raw reports/keys
are copied into shareable evidence.

Only one permanent Fly shared-CPU 512 MiB machine remains for this release, with
min-running 0, auto-stop/start and shared IPv4. This task's builder/cache and
temporary staging Fly app were removed after archiving/restoration. Neon staging
history and all historical audits/private archives remain preserved. Other account
apps/projects were untouched. Estimated continuous compute is about $3.69/month
before egress/tax/temporary usage; no guaranteed hard dollar cap is established.
Operating backup, manual monitoring and cost-suspension instructions remain in
[the dated runbook](RELEASE_OPERATIONS.md); this record supplies current deployment
state beyond that runbook's pre-promotion qualification.

**440 pre-L6 records preserved**, including the original brief, L1–L5 acceptance,
earlier progress records and replay archives. Living README/architecture/suggestions
retain previous byte prefixes. The existing working tree remains uncommitted;
no Git push, hosted CI or externally attested personal track record is claimed.

Next unfinished step: **L6.2 production browser-saved JSON inspection**, then write
the final acceptance record and close the bounded launch checklist. Owner was asked
to save `synthetic-demo-51b34ac3-3c73-43b6-b4f8-253eb70ba7a5.json` in Downloads.
Verify that actual file against the public typed envelope/content hash before
claiming this last check passed. Advanced analytics, paper operation and real-broker
integration remain deferred under PLAN.md.

[Production evidence](verification/launch-l6-2026-10-16/README.md).
