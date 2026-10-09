# Phase 8 closeout evidence — 2026-10-09

These are fresh local checks for [the Phase 8 audit](../../PHASE_8_AUDIT.md).
Earlier phase records and saved historical logs remain separate.

- `backend.txt`: initial full PostgreSQL-enabled pytest, 542 passed, no skips, 97.84%
  statement/branch coverage.
- `backend-final.txt`: final full suite after the methodology/conventions replay
  guard and two additional regressions: 544 passed, no skips, 97.84% coverage.
- `dependencies.txt`, `ruff.txt`, `format.txt`, `mypy.txt`, `hooks.txt`:
  dependency and configured quality checks from the full verification runner.
- `hooks-final.txt`: configured hooks passed after staging the complete checkpoint.
- `benchmark.txt`: offline engine timings; excludes network and rendering.
- `checks-before-lockfile-refresh.json`: successful complete runner before the
  compatible npm dependency update. Final frontend logs below supersede its
  frontend installation profile.
- `frontend-clean-install.txt`, `lint-clean-install.txt`, `build-clean-install.txt`:
  frontend checks after the updated lockfile was installed with `npm ci`.
- `npm-audit-final.json`: fresh npm advisory response, zero vulnerabilities.
- `preservation-checkpoint.json`: retained historical-document byte identities;
  the task-entry temporary baseline was unavailable at final collection. This
  artifact does not claim a recovered before/after checksum comparison.
- `synthetic-downloaded-report.json`: actual UI download containing only the
  disposable synthetic account and supplied quotes. No workspace key is included.
- `synthetic-regenerated-report.json` and `replay-regeneration.json`: explicit
  regeneration after the final replay guard changed source identity. Every
  financial output equals the original download; that original remains intact.
- `acceptance-summary.json`: final environment, result and cleanup summary.
- `performance-results.jpg`: complete synthetic report before fee reversal,
  15% TWR and NAV 230; `performance-mobile.jpg`: corrected report at mobile width,
  20% TWR with explicit undefined XIRR root bounds.

The actual bootstrap script executed successfully with Python 3.12.14 and the
full resolved constraints. Clean-install frontend checks initially encountered
the tool sandbox's Node `realpath` EPERM restriction; the host-authorized rerun
passed. This was an execution-permission boundary, not an application repair.
The actual new PostgreSQL tests were included in the full suite. The synthetic
browser schema was removed, no disposable schemas remained, and the temporary
database/API/frontend services were stopped afterward. No production data was used.
The final test rerun also needed a corrected temporary PostgreSQL restart: its
initial restart omitted port 55439. That waiting attempt was stopped, the explicit
loopback/port settings restored, and the complete suite rerun with `connect_timeout=5`.

Replay the retained synthetic download from the repository root:

```powershell
backend/.venv/Scripts/python.exe scripts/replay_performance.py docs/verification/phase8-closeout-2026-10-09/synthetic-regenerated-report.json
```

This passed against the source/runtime captured at closeout. Retain compatible
source bytes and Python/library versions; future source or line-ending changes
correctly invalidate exact replay. The fixture demonstrates internal consistency,
not quote authenticity, broker reconciliation or external certification.

For repeatable project verification, run `scripts/bootstrap.ps1`, supply an
isolated `TEST_DATABASE_URL`, then run `scripts/verify.ps1`. The PostgreSQL
17.11 ZIP used for these disposable checks had SHA-256
`80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f`.
The resolved Python profile is in `backend/constraints-py312-windows.txt`.
