# Approved public research launch plan

Approved by the owner: **2026-10-13**. Initial planning baseline: **`fb11200`**.
Status: **L1–L5 accepted; production deployed/published; L6 final saved-download check open (2026-10-16)**.
Next task: **L6.2 — inspect the browser-saved production JSON, then record final launch acceptance**.

## Handoff for every continuing agent

Continue `Iska555/Market-Scenario-Generator` as a personal portfolio-management
research platform. The owner has **no Lightyear account or broker statement**.
The approved first public release uses an isolated, explicitly labelled
demonstration portfolio with reproducible synthetic inputs. Real-account evidence
is not a blocker for this release. The private foundation is accepted through
bounded Phase 9E; the broader master plan and Phase 9 are not complete. Read
`AGENTS.md`, this plan, `docs/MASTER_BRIEF.md`, the latest dated audit and the
2026-10-13 launch entry in `docs/BRIEF_SUGGESTIONS.md`. Inspect the actual checkout
and the status table below, then implement the first unfinished step. Preserve
the master brief, historical audits, reviews, evidence and archived replay source.
Complete and verify each stage before advancing; do not repeatedly ask for approval
of this already approved sequence. Record actual evidence and unresolved limits.

## Authority and scope decision

The owner approved the remaining launch work in the conversation and requested
this durable handoff. This is a **prospective release-scope amendment** to the
canonical sequence, not a rewrite of the master brief or a retroactive acceptance.
It authorizes the bounded Phase 10 public research/demo work below while leaving
unfinished advanced Phase 9 work explicitly deferred. Earlier instructions to
implement common-boundary factor measurement next, or to stop before publication,
retain their historical context; they no longer define this release's next task.
All unaffected correctness, methodology, auditability and design rules still apply.

Options considered:

| Approach | Decision and reason |
| --- | --- |
| Wait for a funded broker account | Deferred: it is necessary for a verified real-account record, but needlessly blocks demonstrating the existing platform. |
| Launch a prospective paper portfolio first | Optional later: useful for observing a decision process, but requires owner decisions, explicit fill/cost policy and elapsed history. Do not invent those decisions now. |
| Launch a labelled, reproducible research demonstration | **Approved first release**: usable without broker access, exercises the accepted engine, and makes the evidence boundary visible. |

This approval covers implementation, verification and preparation for public launch.
It does not identify a hosting account, domain, spending limit or production secret.
Resolve missing deployment details when the concrete release is ready for them;
continue independent local work meanwhile. Never infer permission to spend money,
publish private records or overwrite an unrelated existing deployment. Do not
create another approval gate for routine reversible work within this plan.

## Verified starting point and limitations

These are recorded historical results, **not fresh tests run for this plan**:

- [Phase 8](docs/PHASE_8_AUDIT.md): ledger-based performance and offline replay.
- [Phase 9A](docs/PHASE_9A_AUDIT.md): reconciled position contributions.
- [Phase 9B](docs/PHASE_9B_AUDIT.md): supplied benchmark and active-risk comparison.
- [Phase 9C](docs/PHASE_9C_AUDIT.md): regression on reviewed supplied daily inputs.
- [Phase 9D](docs/PHASE_9D_AUDIT.md): immutable benchmark choices and receipts.
- [Phase 9E](docs/PHASE_9E_AUDIT.md): native factor CSV review and source receipts;
  **733 backend tests**, **153 frontend tests**, **97.93% coverage** recorded.

Native factor import does not establish portfolio/currency/calendar alignment.
`docs/FACTOR_ALIGNMENT.md` is prospective, not an accepted implementation.
The equity registry and ledger have bounded instrument support; consult
[ACCOUNTING.md](docs/ACCOUNTING.md) and [ASSET_TYPE_ROADMAP.md](docs/ASSET_TYPE_ROADMAP.md).
Construction is hypothetical; the live-ledger handoff is not accepted.
The existing owner-key workflow is private access, not a public multi-user service.
No public publishing module, production acceptance or verified broker record is
established by these audits. Existing Fly configuration and older hosting references
are configuration/history, not evidence of a currently verified deployment.
Earlier performance/comparison browser-download qualifications remain unchanged;
Phase 9E verified delivery of its source-review receipt only.

## Release contract

### Portfolio identity and claims

| Mode | Meaning | Initial release treatment |
| --- | --- | --- |
| `demo` | Synthetic example transactions, prices, FX and benchmark levels, with an explicit fixture period and provenance. | The only mode eligible for this release's public publishing path. |
| `paper` | Hypothetical decisions recorded prospectively under a declared execution, price, fee and dividend policy. | Reserve the distinction; creating a paper investment programme is deferred. |
| `real` | Actual funded transactions, with separate evidence of reconciliation. A type flag is not verification. | Deferred until actual account data and acceptance exist. |

Existing records with no reviewed mode remain private/unclassified. Never migrate
them to `real` or automatically publish them. Prevent relabelling a demo/paper
history into a real history. Later real and paper portfolios get distinct identities,
start dates and performance series. Do not splice their returns together.

Use original fictional equity identities and synthetic dated inputs for the default
demo; label both clearly. This is a deliberately isolated example, not fabricated
content inserted into an empty personal dashboard. No real investment decisions,
broker logos, claimed connection or synthetic Lightyear statements are needed.
Keep fixture effective dates, actual creation timestamps and actual publication
timestamps distinct. Example thesis dates never become claims about what the owner
knew or decided at that historical date.

### Public experience and data boundaries

- Public visitors can read published snapshots, methodology and sanitized downloads.
  They cannot edit portfolios, unlock owner tools, trigger unrestricted calculations
  or access private drafts. The existing private workspace continues to work.
- Display **Demonstration portfolio — synthetic data; no real money invested**
  prominently and include the mode in chart context, downloads and share metadata.
  Show sample period, base currency, valuation convention and snapshot/data dates.
- Publish portfolio TWR, an explicitly labelled synthetic comparison series,
  since-inception growth, drawdown, monthly/annual returns and complete closed-position
  history. Distinguish full periods from partial periods. Never extrapolate an
  unfinished year into an annual result or fill missing history with zero returns.
- Holdings show dated values/weights, entry-date convention, thesis links and risk
  contribution only when matching inputs and a validated calculation are available.
  If a metric is unsupported, explain why it is unavailable. Do not substitute
  performance contribution for prospective volatility contribution.
- Publish selected fictional research, versioned reviews and decision-journal examples.
  Performance includes all example positions and losses even when research is selected.
- Financial calculations stay in tested backend functions. Public formatting must
  not introduce new return calculations from sampled chart data.
- Public payloads use an explicit allowlist. Do not expose owner keys, account/broker
  identifiers, private notes, raw private reports, local paths or diagnostic secrets.
  A private replay export is not automatically suitable as a public download.
- Retain the master brief's personal-research, not-advice, no-solicitation and
  past-performance presentation requirements. Conditional scenarios remain labelled
  as such. These statements are not a claim of legal review or approval.
- Default to wholly synthetic data and original example research. Before publishing
  third-party data, verify the specific source's permitted public use and attribution;
  a local test fixture or source hash does not establish redistribution rights.

## Stage status

Update this table as work proceeds. A completion entry must link to dated evidence.

| Stage | Status | Visible endpoint | Evidence |
| --- | --- | --- | --- |
| L1 — modes and isolation | Accepted locally 2026-10-14 | Deliberate isolated demo creation; legacy stays private/unclassified. | [L1 audit](docs/LAUNCH_L1_AUDIT.md) |
| L2 — reproducible demonstration | Accepted locally 2026-10-14 | Deliberate original synthetic fixture, exact private replay, responsive browser setup/report workflow. | [L2 audit](docs/LAUNCH_L2_AUDIT.md) |
| L3 — public presentation | Accepted locally 2026-10-14 | Allowlisted synthetic preview, performance, holdings, closed loss and research. | [L3 audit](docs/LAUNCH_L3_AUDIT.md) |
| L4 — controlled publication | Accepted locally 2026-10-14 | Deliberate preview, immutable versions, disclosed correction/withdrawal and actual public download. | [L4 audit](docs/LAUNCH_L4_AUDIT.md) |
| L5 — operations and staging | Accepted 2026-10-16 | Actual saved staging download closes hosted replay/restore/rollback/privacy and bounded-controls gates. | [L5 audit](docs/LAUNCH_L5_AUDIT.md) |
| L6 — release acceptance | Production live; final saved-browser-file check open | Separate production demo, fresh full gate, HTTPS/privacy/browser/restart/backup/replay and temporary compute cleanup passed. | [Production progress](docs/LAUNCH_L6_PROGRESS_2026-10-16.md) |

Stages are ordered. L3 uses safe fixture-backed previews until L4's publication
boundary is accepted; it must not expose the private database to anonymous readers.
No external deployment is needed to complete L1-L4. At each stage, work in small
steps below; inspect existing implementation before choosing exact new filenames.

## L1 — publication modes and isolation

### L1.1 — define and persist the mode safely

**Accepted 2026-10-14**; additive registry, actual PostgreSQL migration/API/concurrency
checks and retained archived replay. See the L1 audit.

- **Goal:** introduce explicit portfolio/publication identity and public eligibility
  while preserving accepted accounting contracts and historical replay.
- **Where:** inspect `backend/src/accounting/{contracts,tables,repository,routes}.py`,
  `backend/src/performance/identity.py` and `backend/migrations/`. Plan the new
  `backend/src/public_track_record/` module. Prefer additive metadata or a separate
  registry if modifying existing contracts would break old reports.
- **Verify:** run backend contract and actual PostgreSQL tests for valid modes,
  unclassified legacy rows, rejected history relabelling, private defaults and
  migrations on both an empty database and a pre-change test database. Replay a
  retained historical report using its matching archived source/runtime.
- **Fence:** do not rewrite old migrations, audits or replay hashes. Do not infer
  brokerage verification from a mode, name or account label. No publishing yet.

### L1.2 — make the distinction visible

**Accepted 2026-10-14**; production-artifact local browser creation/reload/selection,
private identity labels, lock/refresh clearing and final full gate. Default-width
browser only; viewport overrides did not take effect and are not mobile evidence.

- **Goal:** let an owner intentionally create/select a demo and see its status in
  private overview, ledger and report context.
- **Where:** `frontend/src/features/workspace/`, existing ledger/performance feature
  directories and their transport/controller tests; backend response adapters.
- **Verify:** browser flow: create demo, reload/select it, view its label, then switch
  to a legacy record and confirm it remains private/unclassified. Test lock, refresh
  and late responses so prior account data does not reappear under a new label.
- **Fence:** do not add a public signup service, paper trading strategy or automatic
  sample holdings in real/legacy records. Run the stage verification gate below.

## L2 — reproducible demonstration portfolio

### L2.1 — build the fixture and isolated loader

**Accepted locally 2026-10-14**; see the L2 audit for actual numerical, database,
replay and browser evidence and its saved-download qualifications.

- **Goal:** create a deterministic original example covering deposits, withdrawal,
  buys/sells, fees, dividends, FX, cash, a closed loser and a recorded correction.
- **Where:** new versioned demo fixtures under `backend/tests/fixtures/` or a dedicated
  demo directory; a documented loader in `scripts/`; existing accounting/research
  repositories. Keep publication data separable from test-only negative cases.
- **Verify:** load into a fresh isolated database, load again, and prove idempotency
  with unchanged counts/holdings. Refuse a target that is not explicitly demo.
  Hand-check cash, quantities, valuations and selected return intervals independently.
- **Fence:** supported long-only equities/cash only; no fabricated broker statement,
  no external fetch or trading, no resetting an existing personal account. Choose
  fixture dates/values for coverage, not attractive performance; document the choice.

### L2.2 — generate and replay reports

**Accepted locally 2026-10-14**; see the L2 audit for actual numerical, database,
replay and browser evidence and its saved-download qualifications.

- **Goal:** generate performance, contribution and comparison using existing engines
  and coherent ledger versions, marks, FX, cutoffs and synthetic benchmark identity.
- **Where:** `backend/src/performance/`, `attribution/`, `benchmark/`, existing
  replay scripts and a new demo manifest tying inputs to source/runtime identities.
- **Verify:** run `scripts/replay_performance.py`, `scripts/replay_contribution.py`
  and `scripts/replay_comparison.py` against fresh corresponding JSON reports with
  the compatible Python environment. Reconcile linked contributions to TWR using
  the documented tolerance. Test missing marks, invalid FX and incomplete benchmark
  coverage separately; failures must remain visible, not silently reduced samples.
- **Fence:** no new factor integration or altered accounting formula merely to make
  the example pass. Record supplied assumptions and typed unavailable outcomes.

### L2.3 — demonstrate the complete example

**Accepted locally 2026-10-14**; see the L2 audit for actual numerical, database,
replay and browser evidence and its saved-download qualifications.

- **Goal:** show a labelled private demo overview, performance reports and fictional
  thesis/review records ready for deliberate selection into a public preview.
- **Where:** current private workspaces, example content and demo setup documentation.
- **Verify:** browser-run the example from setup to report download; inspect the
  actual saved file and replay it. Compare displayed values against backend reports.
  Record desktop/mobile evidence and complete the stage verification gate.
- **Fence:** example research is not an investment recommendation or the owner's
  historical belief. A fixture period is not elapsed paper-trading history.

## L3 — public pages and honest presentation

### L3.1 — define a public snapshot contract and local preview

- **Goal:** introduce a versioned allowlisted projection carrying demo mode,
  portfolio/data period, calculation provenance and only approved presentation data.
- **Where:** new `backend/src/public_track_record/`; new frontend public feature
  directory and routing in `frontend/src/App.jsx`; existing performance contracts.
- **Verify:** serialization tests inject private identifiers, notes and secret-like
  values and confirm exclusion. Invalid/unclassified/non-demo candidates fail.
  Browser-open a safe fixture-backed preview without an owner key.
- **Fence:** no anonymous proxy to private reports or arbitrary account IDs. A local
  preview is not a published version. Keep old replay contracts compatible.

### L3.2 — build performance, holdings and methodology views

- **Goal:** display the release-contract charts/tables, sample benchmark, clear dates,
  assumptions and unavailable states with the established restrained visual style.
- **Where:** public frontend components, snapshot projection and tested backend
  aggregation for monthly/annual periods or drawdown if not already available.
- **Verify:** independently check period aggregation and drawdown on small analytical
  examples; compare preview values with L2 reports. Test partial years, empty history,
  missing values, negative performance, keyboard access and mobile table scrolling.
- **Fence:** no frontend financial recomputation, invented risk metrics, factor alpha,
  rolling analytics or data silently filled to improve the chart.

### L3.3 — add research, closed positions and journal

- **Goal:** show selected example thesis versions/reviews, all closed positions and
  a timestamped example decision journal alongside methodology and disclosures.
- **Where:** public snapshot content selection and public pages; existing private
  thesis/review models as source, never their entire raw private objects.
- **Verify:** show a closed loser and a corrected example; follow version links and
  confirm fixture dates differ from actual record/publication timestamps. Download
  the public example and check it contains only allowlisted content. Run stage gates.
- **Fence:** no selective removal of losing performance; do not imply synthetic
  journal entries were contemporaneous personal investment decisions.

## L4 — controlled publication and immutable versions

### L4.1 — owner preview and deliberate publish

**Accepted locally 2026-10-14**; see [L4 audit](docs/LAUNCH_L4_AUDIT.md).

- **Goal:** implement explicit draft/preview/publish using a coherent source snapshot,
  authenticated owner actions, immutable published content and a version identity.
- **Where:** public module repository/routes, additive migration(s), owner publication
  controls and public read-only routes. Choose minimal storage after inspecting
  current immutable repository patterns; document the choice in architecture.
- **Verify:** actual database/API tests for coherent versions, stale preview rejection,
  retries, concurrent publication and unauthorized writes. Private source edits
  after publication must not change the published version or its content hash.
- **Fence:** no automatic publication when a ledger/thesis changes. Content hashes
  establish consistency, not external timestamps, market authenticity or broker proof.

### L4.2 — corrections, withdrawal and public boundary

**Accepted locally 2026-10-14**; see [L4 audit](docs/LAUNCH_L4_AUDIT.md).

- **Goal:** publish corrections as new versions with visible reasons; withdraw public
  availability without silently rewriting history. Preserve private audit records.
- **Where:** publication lifecycle, public route/cache behavior, frontend history
  and download transport; release documentation for redaction/withdrawal behavior.
- **Verify:** anonymous requests cannot enumerate drafts, read arbitrary portfolios,
  mutate records or obtain owner secrets. Check published, corrected and withdrawn
  URLs, download delivery, caching and sanitized error responses in a browser.
  Re-run private lock/refresh flows and the full stage gate.
- **Fence:** do not promise already downloaded/cached public information can be
  recalled. Raw private replay bundles must never become public exports by default.

## L5 — deployment, restoration and staging

### L5.1 — resolve the actual deployment target

- **Goal:** document a concrete frontend/backend/database topology, domain/origin
  settings, cost envelope and secret provisioning using available owner resources.
- **Where:** inspect `backend/Dockerfile`, `backend/fly.toml`, `.github/workflows/ci.yml`
  and frontend build settings; create a deployment/runbook document.
- **Verify:** build the production artifact/container and boot against an isolated
  database with migrations. Probe public and private routes from a clean browser.
  Record the actual target and resource limits, not inherited hosting assumptions.
- **Fence:** obtain missing target/budget/access information before provisioning;
  never embed private keys in frontend environment variables or built assets.
  Reuse the existing stack; no hosting migration merely for preference.

### L5.2 — prove recovery and operational controls

- **Goal:** establish backups, retention/recovery objectives, monitoring, deployment
  migrations and an explicit rollback procedure suitable for the selected target.
- **Where:** deployment config, operational scripts and runbook; include database,
  publication artifacts and whatever data is necessary to reproduce the release.
- **Verify:** restore a backup into a separate database, compare ledger/publication
  counts and identities, and regenerate/replay selected reports. Rehearse rollback
  without discarding immutable history. Test error monitoring, bounded request sizes,
  anonymous endpoint limits and representative resource use on the chosen host.
- **Fence:** a source archive is not a database backup; a backup file is not restore
  evidence. Do not exercise destructive recovery against the only original database.

### L5.3 — accept staging

- **Goal:** serve the actual release candidate with production-like settings and a
  clearly identified staging demo, retaining owner-only publication actions.
- **Where:** selected staging environment and dated deployment evidence.
- **Verify:** test fresh-browser public access, blocked private access, owner publish,
  correction/withdrawal, downloads, mobile/keyboard flows, HTTPS/origins and absence
  of secrets from client bundles, response payloads and logs. Record deployed source
  and artifact identity, hosted CI results if available, and remaining warnings.
- **Fence:** localhost success is not staging or capacity evidence. Keep credentials
  and personal material out of screenshots and committed acceptance logs.

## L6 — release acceptance and public launch

### L6.1 — assemble the release evidence

- **Goal:** accept one exact candidate against the checklist below, documenting
  open limitations, release scope and the deferred master-plan work.
- **Where:** a new dated launch audit/evidence directory, this plan's status table,
  `README.md`, `docs/ARCHITECTURE.md`, relevant methodology and suggestions entries.
- **Verify:** run full configured checks with real isolated PostgreSQL; record all
  exits/skips. Independently rebuild/replay the permitted demo with compatible
  source/runtime. Complete browser acceptance and confirm historical preservation.
- **Fence:** no weakening tests/coverage to declare success, no unsupported hosted
  claims, and no rewriting earlier audit findings or treating deferred items as done.

### L6.2 — publish the accepted release and smoke-test it

- **Goal:** promote the accepted candidate to the confirmed public destination and
  publish only its reviewed demonstration snapshot.
- **Where:** confirmed deployment target, release runbook and new acceptance evidence.
- **Verify:** open the actual public URL without credentials; inspect labels, charts,
  closed investments, methodology and saved downloads. Confirm private routes reject
  access, monitoring works and the deployed artifact matches the accepted candidate.
- **Fence:** resolve any outstanding destination/spending authorization before the
  external action. If unavailable, report **release candidate ready; not deployed**,
  list the exact missing input and retain completed local/staging evidence.

## Verification workflow and evidence rules

Inspect `scripts/bootstrap.ps1`, `scripts/verify.ps1`, `pyproject.toml` and
`.github/workflows/ci.yml` before running them. Current CI specifies Python 3.12/3.14,
Node 22 and PostgreSQL 17.6; the Phase 9E local evidence used Python 3.12.14.
Use project-local dependencies, not an inherited unrelated environment.

From the repository root on Windows, after configuring `TEST_DATABASE_URL` for an
**isolated** test database and installing dependencies when needed:

```powershell
# Replace the evidence suffix with this stage's actual date and a unique run ID.
./scripts/verify.ps1 -EvidenceDirectory '.verification/launch-l1-YYYY-MM-DD-run1'
```

The runner checks dependencies, pytest/PostgreSQL, Ruff/format, mypy, hooks,
the existing benchmark, frontend tests/lint/build and records the environment.
`-AllowDatabaseSkips` is diagnostic only, never an acceptance pass. Use targeted
tests while developing, then this gate at implementation stage acceptance; broaden
or repeat only when changes or unresolved failures justify it. A docs-only update
needs link/status/diff and preservation checks, not a claim of fresh application tests.

For fresh compatible demo reports, existing replay commands take a report filename:

```powershell
backend/.venv/Scripts/python.exe scripts/replay_performance.py <performance-json>
backend/.venv/Scripts/python.exe scripts/replay_contribution.py <contribution-json>
backend/.venv/Scripts/python.exe scripts/replay_comparison.py <comparison-json>
```

Angle-bracket paths above are placeholders, not existing artifacts. Old reports
must retain their matching archived source/runtime; do not change historical hashes
to make them replay with a new implementation. Preserve a proportionate compatible
source/environment bundle for the new public demo; specify what it does not include.

Create a fresh dated audit/evidence location per accepted stage, such as
`docs/LAUNCH_L1_AUDIT.md` and `docs/verification/launch-l1-<actual-date>/` (proposed
paths, not existing evidence). Record actual commands, results, original defects,
repairs, numerical assumptions, browser checks, unresolved warnings and remaining
scope. Never overwrite a prior accepted audit; add a new correction/addendum record
when needed. Append to `docs/BRIEF_SUGGESTIONS.md`; preserve its previous bytes.
Preserve all pre-existing master/audit/review/evidence files and earlier execution
plans. Check their hashes or compare with the recorded starting Git revision.

## Final launch checklist

- [ ] L1-L4 have dated acceptance and the current full test gate passes.
- [ ] Demo, paper and real meanings cannot be conflated; legacy records stay private.
- [ ] The entire demo is reproducible and its contributions reconcile to performance.
- [ ] Synthetic transactions, market inputs, comparison and research are labelled.
- [ ] Partial periods, unavailable values, currency and data/snapshot dates are clear.
- [ ] Closed losers and correction history are visible; no selectively omitted returns.
- [ ] Public responses/downloads contain only permitted fields and source material.
- [ ] Owner controls/private records remain inaccessible to anonymous visitors.
- [ ] Published versions are stable and corrections require new disclosed versions.
- [ ] Desktop/mobile, keyboard, empty/error states and actual downloads are verified.
- [ ] Hosting target and resource/cost limits are confirmed; secrets are server-side.
- [ ] Restore and rollback work, with measured recovery evidence and monitoring.
- [ ] Staging and the exact release candidate are accepted; remaining warnings stated.
- [ ] Actual public URL and deployed source/artifact identity pass post-launch checks.
- [ ] README, current plan/status, runbook and new audit agree about what is live.

## Deferred work and conditions for resuming it

These are not initial demo launch blockers and remain **unfinished**:

| Work | Resume when |
| --- | --- |
| Real-account reconciliation and native Lightyear import | An actual account and reviewed redacted statement fixture exist; reconcile positions, cash, flows and performance before claiming verification. |
| Prospective paper portfolio | The owner supplies/chooses policy and decisions; establish actual start date and explicit execution/cost/dividend assumptions. Never backfill a supposed contemporaneous record. |
| Common-boundary factor alignment, real-factor integration | Reviewed valuation/FX/funding/publication evidence satisfies `docs/FACTOR_ALIGNMENT.md`; synthetic acceptance is not real-market validation. |
| HAC/bootstrap and rolling beta/capture | Alignment and estimator/window/sample policies are separately specified and verified. These outputs are excluded from this public release. |
| Brinson attribution | Appropriate historical classifications and benchmark weights exist. |
| ETF/fund/corporate-action and additional asset support | A concrete required instrument/use case is scoped under `docs/ASSET_TYPE_ROADMAP.md`; never represent funds as equities. |
| General ledger-to-construction handoff | A coherent dated valuation/FX/cash/eligibility contract is implemented; any demo risk panel must independently satisfy its narrower input contract. |
| External timestamping / chained daily public snapshots | A separate implementation and operating policy is accepted; current snapshot hashes alone are not external attestation. |
| Advanced optimizers, hedging, macro timing, order execution | Separately scoped later work; do not enlarge this launch to include them. |

## Risks, early checks and fallbacks

| Risk | Early warning / check | Response |
| --- | --- | --- |
| Existing history is reclassified or replay breaks | L1 migration/archived-replay tests fail; fields default legacy accounts to real/demo. | Use additive publication metadata, leave old accounts private and preserve compatible archives. |
| Demo leaks private content or looks like a real record | L3 projection tests or L4 anonymous browser checks expose owner fields, ambiguous dates or missing labels. | Block that payload/version; use only the isolated original fixture until it passes. |
| Hosting or source-data access is unavailable | L5 target inventory is incomplete, or L2/L3 content needs unverified redistribution permission. | Complete the local release candidate; use original synthetic data; request only the specific missing hosting detail at the relevant step. Never claim deployment. |

## Continuation and change log

- **2026-10-13:** owner approved the demo-first remaining launch work and requested
  this durable plan and new-chat prompt. Planning only; no application change,
  fresh numerical acceptance, database mutation or deployment is claimed.
  Documentation verification resolved all eight local plan links, checked all
  15 steps for goal/location/verification/scope, and confirmed 232 protected files
  unchanged against the Git baseline. Existing agent/build/suggestions text was
  retained as a prefix, accounting for Git/Windows line-ending differences.
- **2026-10-14:** implemented and accepted L1.1/L1.2. New immutable identity registry
  and owner-only adapters preserve old accounting/report contracts. Legacy stays
  private/unclassified; only deliberately created demo is a future publication
  candidate. Final gate: 759 backend / 160 frontend tests, zero skips, 97.92%
  coverage, all ten checks passed; retained archived contribution replay passed.
  Actual production-artifact local browser flow accepted at measured 714×660.
  No mobile/restore/deployment claim. Evidence: docs/LAUNCH_L1_AUDIT.md.
- **2026-10-14:** accepted L2. Original fixture covers 13 events, two fictional
  equities, closed loss, FX, funding and a correcting reversal. Exact retry and
  three working/extracted-source replays pass. Final full gate: 770 backend /
  165 frontend cases, zero skips, 97.89% coverage; all ten checks pass. Actual
  performance browser download replay and measured desktop/mobile/keyboard
  workflow pass; contribution/comparison browser delivery remains unverified.
  Repaired observed legacy thesis punctuation and reverified frontend. No public
  publication/restore/deployment claim. Next L3.1; docs/LAUNCH_L2_AUDIT.md.
- **2026-10-14:** accepted L3. Strict allowlisted fixed preview; backend-derived charts, complete closed loss, research/journal and actual sanitized browser download. 775 backend / 169 frontend tests, zero skips, 97.81% coverage; ten checks passed. Working/extracted three-report replay and 311-record preservation passed. Local only; publication, restore and deployment unfinished. Next L4.1; docs/LAUNCH_L3_AUDIT.md.
- **2026-10-14:** accepted L4 locally. 783 backend / 174 frontend, no skips, 97.62%, ten checks passed. Actual PostgreSQL/publication/browser/download/correction/withdrawal and three extracted-source replays passed; preserved 352 prior records. Owner confirmed Fly.io/Neon, total US$5/month ceiling, free preferred. Both dashboard sessions require login; no provisioning or deployment yet. Continue independent recovery/production preparation under L5.1.
- **2026-10-16:** L5 candidate is deployed only to isolated labelled staging. Hosted exact-image three-report replay, actual staging backup restored into a new local database, identical before/after rollback fingerprints and bounded hosted controls passed. Final unchanged application gate was 788 backend / 174 frontend, zero skips, 97.24%, ten exits 0 on 2026-10-14. Temporary builder/cache removed. Saved hosted browser download remains unverified because automation stalls; owner asked for the actual saved file. Production is still its historical stopped image; secrets/origin staged only. See dated L5 progress and operations runbook. Corrected stale L3 status/next-step text without changing historical audits.
- **2026-10-16:** accepted L5 after the owner saved the actual staging browser JSON; strict typed envelope and immutable content/file hashes match. Preserved earlier progress records. Continue L6 with the same pinned image and a separately created production synthetic identity/history.
- **2026-10-16:** production now serves the accepted pinned image and its own first synthetic version 51b34ac3-3c73-43b6-b4f8-253eb70ba7a5. Fresh L6 gate: 788 backend / 174 frontend, zero skips, 97.24%, ten exits 0. Production backup/local restore/replays, restart, public/private and responsive browser checks passed; temporary Fly staging compute removed after archival. L6 saved-production-browser-file inspection remains open. See LAUNCH_L6_PROGRESS_2026-10-16.md; do not repeat creation/publication or rewrite prior records.
- **2026-10-16:** owner requested public GitHub source publication. Repository already public; prepared a fast-forward main update with credential/history/archive review and private artifact exclusions. See docs/GITHUB_PUBLICATION_2026-10-16.md. The L6.2 saved-production-browser-file check remains the next unfinished release acceptance step.
- On each continuation, inspect Git status and the latest audit first. Update the
  stage table, record the next exact step and append a dated change-log entry.
  Preserve existing uncommitted work, including these planning files. Do not
  reinterpret old acceptance records to fit the new release scope.

## Copyable new-chat prompt

```text
Continue Iska555/Market-Scenario-Generator in:
C:\Users\Don\Desktop\Portfolio Management\market_scenario-generator

Read AGENTS.md and PLAN.md first, then docs/MASTER_BRIEF.md, the latest phase/launch
audit and the approved 2026-10-13 launch entry in docs/BRIEF_SUGGESTIONS.md.

I approve the staged public research/demo launch plan in PLAN.md. I do not have a
Lightyear account. Launch with an isolated, clearly labelled synthetic demonstration
portfolio. Keep paper and future real portfolios separate; do not invent broker
data or claim a verified personal track record. The advanced analytics and real-
account items listed as deferred are not blockers for this bounded first release.

Inspect the current branch, working tree, stage table and implementation. Resume
the first unfinished step; at the initial handoff it is L1.1. Implement and verify
the work, rather than only proposing another plan. Proceed through the approved
stages as their acceptance checks pass, without asking again for routine approval.
Ask only for genuinely missing information or external access needed for the next
dependent action, and continue independent work while waiting.

Preserve the master brief and every historical audit, review, evidence file and
replay archive. Write fresh dated acceptance records, append suggestions, and keep
PLAN.md's status and next step current. Follow the repository's correctness,
privacy, replay and design requirements. Do not claim that a test, restore, hosted
check or deployment passed unless it was actually verified. Report what changed,
the evidence, remaining limitations and the next unfinished step.
```
