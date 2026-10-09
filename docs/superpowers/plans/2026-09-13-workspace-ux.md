# Investment Management Workspace refinement plan

**Goal:** Apply the owner's 2026-09-13 UX specification within Phase 7, preserving formulas, security boundaries and historical records.

**Architecture:** A single memory-only session owns authentication and registers active private controllers for clearing. Child modules reuse their existing guarded API clients. Overview reads existing accounting records; no frontend financial calculations. Risk controls disclose technical settings progressively while retaining API values.

**Ruling:** Continue in the supplied dirty checkout because it contains the authorized Phase 4–7 implementation. Preserve all pre-existing edits. The user's detailed specification authorizes this implementation; no repeated design approval is needed. No publishing, commits or phase advancement.

- [x] Session and navigation: add session store/context and global control; connect children through it, remove local password forms, clear controllers on lock and prevent stale responses. Add controller and rendered regression tests before implementation.
- [x] Risk controls: extract SimulationConfig, group normal/advanced controls, use buy-and-hold frontend default, preserve precise requests, remove single-asset selectors, explain models and history windows. Add contract/render regression tests first.
- [x] Overview and Construction: show real account records and derived quantities from existing endpoints; explicit empty/unavailable states; hypothetical source only until a reviewed ledger-to-construction valuation contract exists.
- [x] Current documentation/branding: update shell, title, README and API identity, add methodology conventions and future typed asset architecture. Preserve MASTER_BRIEF and historical audits.
- [x] Verify: targeted tests, full pytest/ruff/mypy/frontend tests/lint/build, independent review, browser inspection of all eight screens at desktop/mobile sizes. Record evidence and deliberate deferrals in a new refinement report.

**Acceptance:** User's 24 sections and acceptance criteria are the binding specification. Saved investor-view drift and future asset types must not appear functional unless contracts already implement them. No formula changes planned.
