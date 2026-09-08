# Phase 2 methodology and tests implementation plan

**Goal:** Execute the owner's 2026-09-08 authorization for Phase 2 of
`docs/MASTER_BRIEF.md`, preserving the completed Phase 1 working tree.

**Architecture:** Retain the typed API, data boundary, portfolio functions and
risk domain. Strengthen their analytical contracts and reproducible verification.
No new investment features or Phase 3 packages.

**Tech stack:** Existing Python/FastAPI/NumPy/sklearn, pytest-cov, Ruff, mypy,
pre-commit, React/Vite and GitHub Actions. Retain pinned dependency versions.

## Execution checklist

- [x] Read the canonical brief, Phase 1 audit, active source, tests and tooling.
  Baseline: 65 tests pass; domain branch coverage 92%; Ruff/format/mypy/pip check pass.
- [x] Add independently derived model moments, deterministic integration cases,
  tail boundaries, and rejected-input tests under `backend/tests/`. A histogram
  must reject an empty/nonfinite/non-vector population rather than report invented
  zero-count bins. Observe its regression fail before changing implementation.
- [x] Repair only defects demonstrated by new tests; keep API v3 and formulas.
- [x] Configure branch coverage for `src` and `main`, a 95% aggregate floor, and
  terminal/XML reports. Include no source exclusions to inflate coverage.
- [x] Align local pre-commit and CI checks across backend, scripts and tooling
  changes. Run formatting, lint, typing, coverage tests, dependency consistency,
  frontend tests/lint/build, and the offline benchmark. Save CI coverage and
  resolved-environment artifacts without claiming bitwise cross-platform replay.
- [x] Add methodology details and a function/test traceability inventory; document
  estimation versus scenario windows, failure policies and residual gaps. Update
  architecture, README, build plan and Phase 2 audit. Preserve the master brief.
- [x] Review all Phase 2 changes and acceptance criteria, record actual results,
  then stop for owner review before Phase 3. Do not merge or deploy.

## Validation rationale

Use exact answers for covariance, wealth paths, histogram boundaries and empirical
tail mass. Use fixed seeds and conservative sampling-error tolerances for sampler
moments, not serialized stochastic snapshots. Existing concurrent API regressions
continue to check seed isolation. Coverage is a regression alarm, not proof of
mathematical correctness; the function inventory provides the semantic evidence.
