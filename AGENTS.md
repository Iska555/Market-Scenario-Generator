# Investment Management Workspace project rules

Read `docs/MASTER_BRIEF.md` before planning or implementation. It is the owner's
permanent, canonical brief, dated 2026-09-06, with the approved 2026-09-09 addendum,
and supersedes the older documents in `docs/superpowers/` wherever they conflict.
Preserve the original brief and historical audits; record proposed additions
separately in `docs/BRIEF_SUGGESTIONS.md`.

Correctness, auditability, and intellectual honesty take priority over features.
Historical returns are evidence, never an implicit expected-return assumption.
Simulations are conditional scenarios. Financial calculations belong in tested
backend domain functions, with visible assumptions and matching methodology.

Follow the canonical phase order. The owner considers Phases 1–6 approved for
continuation, explicitly authorized Phase 7 (transaction ledger) on 2026-09-12,
and Phase 8 (TWR/XIRR performance measurement) on 2026-09-15. Read
`docs/PERFORMANCE.md` and `docs/PHASE_8_AUDIT.md` for current scope and evidence.
Stop for owner review before Phase 9. Do not create attribution or publishing
features in this phase. Lightyear Stocks & Shares ISA
is the intended broker/account, not an existing connected account. Native imports
require a verified statement fixture; manual entry and reviewed canonical CSV
are the current boundary. Preserve the equity-only security registry semantics.
Do not automatically generate investment
decisions or promote model outputs into portfolio expected-return views.

On 2026-10-09 the owner approved the recommended proceeding sequence and selected
Phase 8 acceptance/reproducibility closeout as the current task. The approved
sequence and integration priorities are appended in docs/BRIEF_SUGGESTIONS.md.
Complete this bounded closeout before subsequent attribution work; the older
phase gates above retain their original context. Record fresh acceptance in
docs/PHASE_8_AUDIT.md without editing any historical audit or master-brief text.

The owner explicitly authorized Phase 9A reconciled position contribution on
2026-10-09 after Phase 8 acceptance. This supersedes the earlier stop-before-9
gate for this bounded scope. Implement ledger-derived contribution, explicit
cash/dividend/fee/FX effects and geometric linking; require reconciliation to
Phase 8 TWR and visible residuals. Preserve all existing audits, including Phase 8.
Benchmark, factor regression, Brinson and publishing remain separate subsequent
stages. Record current scope and evidence in docs/PHASE_9A_AUDIT.md.

On 2026-10-11 the owner instructed continuation of the approved plan after Phase
9A acceptance, authorizing Phase 9B benchmark/active-risk analysis. Use an explicit
versioned, report-scoped benchmark selection for the chosen account, reviewed
same-currency total-return levels and aligned UTC daily intervals. No hardcoded
benchmark or automatic provider call. Record fresh evidence in PHASE_9B_AUDIT.md;
preserve every existing audit and evidence file. Factor regression, alpha, rolling
analytics, Brinson, publication and durable benchmark-default settings remain later.

The owner's next 2026-10-11 continuation authorizes bounded Phase 9C historical
factor regression. Use reviewed dated factor/risk-free evidence and matching
funded portfolio excess-return intervals; report coefficients with HC3 standard
errors/t-statistics, fit diagnostics and sample context. Preserve all historical
records and write PHASE_9C_AUDIT.md. No implied expected return, persistent skill,
automatic data/FX, rolling models, Brinson or publication. Plan: the separate
2026-10-11-phase-9c-factors.md execution record.

The owner's further continuation after Phase 9C authorizes bounded Phase 9D:
append-only portfolio benchmark settings with explicit report selection receipts,
private settings workflows and real-factor currency/calendar readiness documentation.
Preserve every previous audit/evidence file and append fresh suggestions. Record
PHASE_9D_AUDIT.md. No automatic provider/FX/calendar transformations, HAC/rolling,
Brinson or publishing. Use the separate 2026-10-11-phase-9d-settings.md plan.

Apply the approved seven suggestions and permanent rules A–D in the master brief:
explicit return/horizon/currency conventions; proportionate replay manifests;
typed undefined values; distinct uncertainty and risk meanings; calendar/FX/data
adjustment provenance; phase acceptance gates; separate assumptions, model
outputs and investor views; optional explicit scenario probabilities; human
investment decisions. Phase 5 uses explicit supplied inputs and existing private
research evidence, with no new provider-data archive or automatic provider calls.

Apply the 2026-09-10 frontend direction: soft corners and restrained surfaces,
modern and useful portfolio-management workflows, clear typography/navigation,
no AI branding or decorative AI-demo motifs, accessible responsive controls and
tables. Never fabricate portfolio data to populate an unfinished dashboard.

Use offline analytical/regression tests for quantitative changes. Run pytest,
ruff, mypy, frontend tests, lint, and build. Document defects by original file and
function, repair status, assumptions, and remaining limitations. Do not describe
unverified or merely planned behavior as implemented.
