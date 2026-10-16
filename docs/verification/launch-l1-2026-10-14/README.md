# Launch L1 local acceptance evidence

Accepted 2026-10-14 Europe/London. Scope and qualifications:
[audit](../../LAUNCH_L1_AUDIT.md), [identity contract](../../PORTFOLIO_IDENTITY.md).

- `checks.json` and ten logs: actual final configured gate, all exit codes zero.
  `backend.txt`: 759 passed, zero skips, 97.92% coverage. `frontend.txt`: 160 passed.
- `resolved-python.txt`: compatible Python 3.12.14 profile. Disposable PostgreSQL
  17.11, separate test schemas; no production database was touched.
- `historical-replay.txt`: retained Phase 9A corrected report verified with the
  independently extracted original 74-file source/runtime, not changed source.
- `preservation.json`: 253 starting records checked; original suggestions/README
  remain prefixes. `starting-PLAN.md` preserves the original handoff while the
  root plan's current status is intentionally updated. Historical source/evidence
  archives remain byte-identical.
- `demo-overview.jpg`: actual isolated demo in the production frontend at measured
  714×660 viewport. `ledger-demo.txt`: actual final UI snapshot, including synthetic
  source defaults. Viewport override calls were ineffective; no mobile/1280-pixel
  acceptance is claimed. Screenshots named desktop during development were not
  retained as such evidence. No private owner key is included.

L1 demonstrates deliberate empty demo creation and legacy separation, persistence,
mode labels and private lock/refresh clearing. Report downloads, full fixture
reproducibility, public projection/publication, restore, staging and deployment
remain later acceptance gates. Failed/stopped diagnostic runs are described in the
audit and are not counted as passing verification.
