# Phase 9A — reconciled position contribution

Authorized 2026-10-09, after Phase 8 local acceptance. Preserve the master brief,
historical audits and Phase 8 evidence. No benchmark, regression, Brinson,
publication, provider connection or instrument-model extension in this stage.

1. Define endpoint accounting identities: change in marked equity value less
   signed trade principal, net booked dividends, explicit fees, security/cash FX
   effects and conversion effects. Use actual corrected ledger quantities and
   executed prices, never today's weights applied to an older return series.
2. Segment at every supplied daily close and immediately before/after each external
   flow, preserving ledger sequence at equal timestamps. Use Phase 8's actual
   units and flow deltas. Divide segment P&L by the constant outstanding units
   to obtain increments of normalized wealth; sum these to geometrically linked
   TWR. This is a specified forward wealth-linking convention, not unique causal
   attribution or benchmark-relative geometric attribution.
3. Define local-price/FX cross-effect allocation explicitly: translate local
   capital P&L, booked income and costs at segment-end FX; opening marked equity
   and opening cash receive the FX-rate change. Conversion principal is a separate
   effect at end FX, with fees distinct. This endpoint convention reconciles without
   pretending to know transaction-time market FX not present in the evidence.
4. Add typed pure attribution contracts and engine, retaining closed securities,
   top/bottom ranked equity contributors, cash and account effects, segment opening
   exposures, exact decimals, undefined reasons, reconciliation residual/tolerance
   and offline replay. Additional end FX can be needed for spent/sold currencies
   even when Phase 8 can value a zero balance without it.
5. Add a read-only private attribution endpoint returning the Phase 8 report from
   the same locked snapshot. Integrate an explicit contribution option in Performance,
   clear results on edits/lock/stale versions and provide a private replay download.
6. Verify analytical buys/sells, dividends (including alternate payout currency),
   fee allocation, currency conversion, multiple flows, same-timestamp ordering,
   corrections/knowledge cutoffs, loss/withdrawal/empty/missing/stale coverage and
   linking/cancellation cases. Actual PostgreSQL tests must verify no table changes,
   coherent locks and stale-version rejection. Frontend tests cover privacy/staleness
   and typed undefined results; inspect complete/missing/corrected responsive browser cases.
7. Run full PostgreSQL-enabled pytest and coverage, Ruff/format/mypy/hooks,
   frontend tests/lint/build. Write the methodology and a new dated Phase 9A audit;
   append suggestions/build-plan status. Verify task-entry hashes and create a local
   reviewed checkpoint. Stop before the next major stage.

Acceptance: all complete reports reconcile to Phase 8 TWR within fixed
`1e-12 + 1e-12 * abs(TWR)` decimal return tolerance; residual is never assigned
to a security to force a match. Missing contribution evidence leaves the entire
window breakdown undefined while retaining the independently computed Phase 8
report. Historical classifications are not inferred from current security metadata.
Security UUIDs remain authoritative; sector aggregation needs point-in-time inputs.
