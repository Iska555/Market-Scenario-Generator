# Proposed additions to the permanent master brief

These are proposals for owner review. They do not amend the preserved original
brief or authorize later phases.

1. **Define the return and annualization contract.** Distinguish log drift,
   arithmetic expected simple return, and compound growth. Specify whether a
   risk-free rate is annual effective, nominal, or continuously compounded.
   Specify trading periods/year by asset universe and valuation calendar.
   Zero log drift does not mean zero expected simple return or risk neutrality.

2. **Make every report replayable from a run manifest.** Record resolved inputs,
   code/build identity, library versions, provider retrieval time, observation
   dates, corporate-action adjustment policy, and hashes of the exact data used.
   Hashes identify a dataset; they do not replace storing the dataset. Define
   retention and licensing policies before persistent provider snapshots.

3. **Give missing and undefined metrics explicit semantics.** Never coerce
   undefined Sharpe, Sortino, Calmar or risk-share ratios to zero. Report a reason
   and effective observation/path counts. Use distribution summaries only when
   the treatment of undefined paths is stated and visible.

4. **Specify tail-estimator and uncertainty conventions.** Define quantile
   interpolation and fractional tail atoms at finite sample sizes. Later show
   effective tail counts and Monte Carlo uncertainty separately from model and
   parameter uncertainty. A 99th percentile is not a best/worst outcome bound.

5. **Treat calendar, currency and corporate-action reconciliation as prerequisites.**
   Matching return dates is insufficient if intervals start on different dates.
   Before multi-currency portfolios, require explicit FX series, valuation
   cutoffs and adjustment conventions. Split-like moves, zero volume and repeated
   prices alone should trigger investigation rather than automatic deletion.

6. **Separate ex-ante risk from simulated and realized volatility.** Initial-weight
   historical covariance risk is a different quantity from pooled scenario
   volatility and from the realized ledger's volatility. Label each estimator,
   period and weight basis. Contributions can legitimately be negative.

7. **Add acceptance gates per phase.** Each phase should have analytical
   reconciliation identities, failure cases, API compatibility policy,
   reproducible checks, and a short record of what is still unsupported. Require
   provider contract tests and representative memory/load tests before deployment.

Two clarifications already needed for Phase 1: Sharpe uses arithmetic mean excess
period return with matching annualization; CAGR is reported separately. Calmar is
calculated per path, not from a ratio of separately averaged numerator and
denominator. These refine ambiguous choices without changing the philosophy.
