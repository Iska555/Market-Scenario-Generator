# Phase 5 valuation implementation plan

**Goal:** Complete the owner's Phase 5 request and stop before Phase 6.

**Authority:** Owner continuation request and the canonical master brief, with the
approved Phase 5 addendum. The owner explicitly directs autonomous execution;
ordinary design choices do not require another approval. Preserve all pre-existing
changes and historical audits; leave work uncommitted for review.

**Architecture:** `valuation/contracts.py` defines semantics and assumption sets;
`valuation/models.py` provides fundamental/scenario/reverse calculations;
`views/expected_return.py` provides user views, CAPM and historical diagnostics;
`valuation/service.py` validates stored evidence and builds replay manifests;
`valuation/routes.py` provides private transport. Frontend valuation components
only collect inputs and render server calculations. No Phase 6 coupling.

- [x] Audit current boundaries before major implementation (`PHASE_5_AUDIT.md`).
- [x] Adopt approved permanent guidance in forward-looking documentation.
- [x] Define typed context, return/uncertainty, assumptions, model results, views,
  scenarios and manifest contracts. Add invalid-domain tests before implementation.
- [x] Implement user views, then historical diagnostics and CAPM with explicit
  frequencies, interval alignment, rf/ERP and regression quality. Test known cases.
- [x] Implement fundamental forward product/wealth identities, optional probability
  weighting of terminal wealth, and reverse terminal-multiple inversion. Test
  round trips, impossible cases and numerical failure.
- [x] Validate security/evidence/thesis IDs, availability and currency; return
  evidence snapshots and replay metadata. Add API and PostgreSQL checks.
- [x] Build focused security/thesis/assumption/model workspace with stale-response,
  exact-input, null, horizon, provenance and presentation tests.
- [x] Run pytest (95% branch gate), ruff/format, mypy, frontend tests/lint/build.
- [x] Independent code review, resolve material findings, update methodology and
  final audit with observed results and unsupported functionality. Stop.

Implementation uses the subagent-driven-development skill for independently
bounded documentation/UI work and the requesting-code-review skill for review.
Shared interface is `valuation/contracts.py`; frontend changes only after it is
defined. No task rewrites another task's files. Documentation records formulas
from implemented contracts; verification claims are added only after checks.
