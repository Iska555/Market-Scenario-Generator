# Portfolio Simulations project rules

Read `docs/MASTER_BRIEF.md` before planning or implementation. It is the owner's
permanent, canonical brief, dated 2026-09-06, and supersedes the older documents in
`docs/superpowers/` wherever they conflict. Preserve the original brief; record
proposed additions separately in `docs/BRIEF_SUGGESTIONS.md`.

Correctness, auditability, and intellectual honesty take priority over features.
Historical returns are evidence, never an implicit expected-return assumption.
Simulations are conditional scenarios. Financial calculations belong in tested
backend domain functions, with visible assumptions and matching methodology.

Follow the canonical phase order. The owner explicitly authorized Phase 3
(fundamental research data model) on 2026-09-08 after Phase 2. Stop for
owner review before Phase 4. Do not create thesis, ledger,
performance-accounting, attribution, or publishing features in this phase.

Use offline analytical/regression tests for quantitative changes. Run pytest,
ruff, mypy, frontend tests, lint, and build. Document defects by original file and
function, repair status, assumptions, and remaining limitations. Do not describe
unverified or merely planned behavior as implemented.
