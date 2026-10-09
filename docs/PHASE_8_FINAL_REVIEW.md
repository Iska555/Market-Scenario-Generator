# Phase 8 scoped independent review

Date: 2026-09-16. This is a review record, **not a phase acceptance claim**.
The implementation owner retains responsibility for repairing findings and final
whole-project verification. Existing review records remain unchanged.

## Scope

Reviewed `frontend/src/features/performance/`, its `App.jsx` and
`PlatformShell.jsx` integration, the shared private-session attachment lifecycle,
the actual backend request/response contracts, and the two backend repairs
identified by the earlier metrics review. No implementation files were edited by
this reviewer.

## Actionable finding

**P1 — recovered pre-flow value can still resurrect a total-loss segment when a
full withdrawal bypasses the new closing-value guard.**

Location: `backend/src/performance/engine.py`, `build_report`, external-flow
unit-value calculation and closing valuation.

Reproduction using existing analytical fixtures:

1. Deposit 100 and buy one equity at 100 before the opening close.
2. Supply opening price 100 and the next closing price 0.
3. On the third day, sell the equity at 110, then withdraw all 110.
4. The final account is base-currency cash only with zero balance; no final quote
   is required.

Observed: final TWR is **+10%**, although the final daily return is undefined as
`zero_prior_unit_value`. The withdrawal shows `units_delta=-100` and no reason.
At the flow boundary, the code sets unit value to 1.1 and redeems all units. The
new closing guard only checks `loss_to_zero` inside `units > 0`, so it is skipped.

Expected: continuous TWR is undefined because recovery from a zero unit value
requires a separate segment. Validate `loss_to_zero` before issuing or redeeming
units at a recovered pre-flow valuation. Retain the independently observable flow
amount and NAV for XIRR, but do not label invalid unit issuance/redemption as
complete. Add this sell/full-withdrawal regression in addition to the existing
positive closing-value recovery test.

This finding was reproduced against the current implementation and sent to the
root implementer. Repair verification should be recorded separately below rather
than deleting the finding.

## Checked behavior

- The prior UTC-day age issue is repaired at both daily/pre-flow valuation and
  foreign-flow conversion checks; cutoff and observed dates normalize to UTC.
- Ordinary positive-value recovery after total loss is now rejected by the
  closing-value guard. The flow-boundary bypass above remains a distinct case.
- Performance is attached to the shared private session. Lock clears controller
  state and the app's epoch remount clears private component state. The secret
  remains outside snapshots; no new durable browser persistence is introduced.
- Generation checks discard stale account, template, report and imported-file
  results after state changes or disconnect. Report runs clear previous results
  before validation/request errors. Account switches clear evidence and use the
  newly loaded ledger version.
- Template history pagination verifies current ledger versions, uses the
  backend's historical active transaction IDs, and passes the selected knowledge
  cutoff to the historical state request. The report endpoint independently
  enforces the current version and ledger semantics.
- `evidenceTemplate` uses millisecond JavaScript dates for membership, but its
  day-end comparison correctly excludes all microseconds of the opening day and
  includes all microseconds of the final day. An executed boundary probe checked
  opening `23:59:59.999998` and `.999999`, next-day midnight, final-day
  `23:59:59.999999`, the following midnight, and an equivalent `+04:00` timestamp.
  Only the three within-window records were included. Sub-millisecond ordering
  of flow template entries is not financially authoritative: the backend maps
  flow evidence by ID and orders actual transactions itself. The backend's active
  IDs also protect the precise historical knowledge boundary.
- Supplied decimal prices and FX remain strings; displayed money and units use
  returned exact decimal strings. Calculations remain in the backend. UI outputs
  distinguish finite metrics, missing reasons and partial calendar periods.
- No concrete additional security or contract correctness defect was found in
  the reviewed frontend files. This is not a browser visual/accessibility audit.

## Scoped checks

- Frontend performance controller and component tests: **10 passed**, 0 failed.
- Backend performance engine/API tests: **29 passed**, 0 failed (12.58 seconds).
- The adversarial total-loss/full-withdrawal reproduction above was outside the
  existing passing suite and demonstrates its missing regression.

This review does not assert complete coverage, production readiness, PostgreSQL
concurrency validation, or later-phase functionality.

## Finding disposition — independent repair check, 2026-09-16

The residual P1 above is **repaired in the reviewed implementation**. The external
flow branch now checks a previously zero unit value against recovered pre-flow NAV
before changing unit value or issuing/redeeming units. The same sell-at-110 and
full-withdrawal reproduction now returns:

- TWR: undefined, `zero_unit_value_recovery_requires_new_segment`.
- Withdrawal units delta: undefined with the same reason.
- Observed withdrawal amount/base amount and pre-flow NAV: retained as -110/-110
  and 110 respectively, allowing the separate dated cash-flow calculation.

The focused regression selection passed **5 tests** (22 deselected, 2.03 seconds),
covering zero-value funding, persistent zero value, ordinary recovery, the
full-withdrawal bypass and FX conversion with fees. The new conversion fixture
reconciles NAV 98 and TWR -2% after converting 80 GBP to 100 USD at 0.8 GBP/USD and
paying a 2 GBP fee, with no external flow. No concern introduced by this focused
repair was found. This disposition resolves the actionable finding in this review;
the implementation owner still owns final acceptance and broader verification.
