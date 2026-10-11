# Phase 9C — historical factor regression

The owner's 2026-10-11 continuation authorizes the next bounded stage after Phase
9B. Preserve the permanent master and all previous audits/evidence. Record fresh
acceptance in PHASE_9C_AUDIT.md and append prospective suggestions.

1. Define explicit model/revision/provider/currency/calendar, factor definitions,
   units and period-effective risk-free evidence. Support one to six reviewed
   excess-market or long-short research factors. Require dated publication and
   retrieval provenance, exact decimal strings and no automatic provider/FX/fill.
2. Regress actual daily portfolio simple excess returns on an intercept and
   supplied factors. Require the complete selected window, funded opening
   intervals and at least 30 observations. Fit centered/scaled SVD OLS; diagnose
   constant, rank-deficient and ill-conditioned designs. Publish coefficients,
   HC3 standard errors and t-statistics, R²/adjusted R², residuals, sample period,
   counts and degrees of freedom. Exact-fit/high-leverage inference is undefined.
   State estimator, serial-dependence and specification uncertainty; no annual
   alpha/forecast, causal or persistent-skill claim.
3. Add a private read-only route retaining the existing locked performance snapshot,
   optional position contribution and optional benchmark comparison in one response.
   Add source/runtime/evidence/output-checked offline replay and private JSON export.
4. Extend Performance with opt-in factor evidence/template/results. Clear all
   results on edits/account/import/lock/navigation/refresh and ignore late responses.
5. Verify hand-derived single/multiple factor fits and HC3 inference, signs,
   residual identities, gaps/funding/zero variance/rank/conditioning/overflow,
   strict provenance/units, replay tampering, private API and actual PostgreSQL
   all-table immutability/row locking/stale correction. Inspect populated/missing/
   corrected responsive browser workflows and private clearing.
6. Run the full PostgreSQL-enabled backend/coverage, quality/hooks, client tests/
   lint/build and scenario benchmark. Retain synthetic exports, exact accepted
   replay source and historical preservation proof; update current documentation,
   append suggestions, stop services and create a local checkpoint.

Boundaries: supplied reviewed UTC daily data only. Public research trading-day,
percentage or USD series need deliberate review/transformation before this contract;
no automatic conversion, weekend invention, download or licensed archive. HC3
handles heteroskedasticity, not serial correlation; HAC/bootstrap/rolling models,
factor covariance risk, geometric attribution, Brinson, saved benchmark defaults,
fund/broker integrations and publication remain later stages.
