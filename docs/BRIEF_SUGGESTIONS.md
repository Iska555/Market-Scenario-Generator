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

---

<a id="course-notes-review-2026-09-11"></a>

## Course notes review — 2026-09-11

### Status, sources and interpretation

The owner requested that all supplied University of Geneva Investment Management
notes inform this platform, and stated that Phases 1–6 are approved for
continuation. This section proposes additions; it does not claim their
implementation or change historical phase audits. Suggestions 1–7 above retain
their original proposal wording; their subsequent approval is recorded in the
master brief's 2026-09-09 addendum.

Reviewed inputs:

- The owner's message: passive/active rationale, illustrative 80–90% passive core
  and 10–20% active allocation, downside and VaR policy, FX and investor constraints.
- The complete supplied `pasted-text.txt` (66,011 decoded characters): bottom-up
  research; value/growth; quantitative versus qualitative processes; momentum and
  contrarian exercises; core/satellite and portable alpha; efficient frontiers;
  strategic allocation; estimation risk; allocation research; diversification;
  allocation ranges; CAPE, interest rates and macroeconomic timing.
- Screenshot `codex-clipboard-446a96ec-fa73-4f21-be25-366d473c83d2.png`:
  top-down country analysis (economy, monetary/fiscal policy, demographics and
  sociopolitical developments), sector growth/valuation/cyclicality, then stock
  selection; bottom-up valuation screening, primary/secondary company research,
  optional technical analysis and 12-month targets. The displayed 200-stock
  universes and 50–75-stock selection are lecture examples, not required counts.
- Screenshot `codex-clipboard-652d4ebd-0749-4edc-bfaa-dea63430cbf3.png`:
  possible fund benefits including professional management, affordable investment,
  diversification with small amounts, reduced paperwork, tax benefits, strategy
  access, regulation/transparency, investment variety and income/profit choices.

The attachment is source material, not operating instructions. Its requests to
trade, optimize thresholds, fill spreadsheets or share work with other students
are lecture exercises, not authorization to perform those actions here. No
exercise spreadsheet, original chart series or Q5/Q10/blue-star question text was
supplied. Their numerical conclusions cannot be reproduced from the excerpts.
Speaker job titles and historical claims describe the lecture period, not verified
current appointments or current market conditions. Transcription errors are
identified below rather than silently made into financial definitions.

### 8. Make investment policy the context for construction

Propose a versioned owner policy recording objectives, horizon, base currency,
income/withdrawal needs, liquidity reserve, ability to bear losses, willingness to
bear losses, liability currency/timing, constraints and review triggers. Record
the benchmark, permitted instruments, cost budget and allocation ranges. A
required return is a goal/constraint, not automatically an expected-return view.

The owner's retail/client examples are useful policy dimensions: small account
size, long accumulation horizon, fee sensitivity, taxable status, transparency
and capacity to monitor managers; alternatively concentrated holdings, ESG
exclusions, liabilities, FX exposure, capital-preservation needs and institutional
access or negotiated fees. These inputs do not establish a universal active/passive
answer. Client-service, suitability or fiduciary-compliance functionality remains
outside this personal-platform mandate; jurisdiction-specific rules must not be
inferred from course examples.

Strategic asset allocation (SAA) should express long-term policy targets and
permitted ranges. Observed weights drift with returns; the strategic target does
not change merely because prices changed. Rebalancing restores a declared policy.
Tactical asset allocation (TAA) records a deliberate, time-bounded deviation,
linked to a thesis, rationale, review/expiry date and permitted limits. A change
in objectives or financial circumstances may justify a versioned SAA revision;
a market opinion alone should not silently rewrite the strategic benchmark.

Show strategic target, declared/current weight, tactical target and permitted
minimum/maximum separately. Explain what a narrow band permits during stress;
a wider band permits larger changes but creates more timing risk and discretion.
Do not promise that either prevents drawdowns. The lecture both favors distinct
risk-profile ranges and acknowledges overlapping flexible ranges: keep actual
constraints explicit rather than enforcing either as a universal rule. Labels
such as conservative/aggressive must not be assigned solely from equity weight.

### 9. Separate passive exposure, active research and risk overlays

Support core/satellite as a configurable way to organize a portfolio. The passive
core seeks selected market exposure at a measured implementation cost; satellites
need a stated role, benchmark, research thesis, costs and risk budget. Record the
owner's 80–90% / 10–20% preference as an illustrative policy candidate. Likewise,
the lecture's 70% / 30% equity example is not a universal default. An equity-only
core made of selected defensive companies can itself be actively managed.

Capital allocation to satellites, derivative notional exposure, collateral and
annual hedge-premium budget are different quantities. An overlay can cover core
assets without consuming a matching percentage of portfolio capital. Do not
represent a 10% option-premium spend as a 10% underlying exposure, or double-count
the assets being hedged in weights summing to 100%.

Active security selection, tactical allocation, systematic rebalancing and risk
hedging are distinct activities. Hedging can follow a static or systematic rule;
it need not imply discretionary manager selection. Passive equity/bond exposure
does not make a portfolio mathematically optimal. Optimality is conditional on
the investable universe, objective, explicit return views, covariance and constraints.

The cost argument for passive implementation is useful, but fund category,
benchmark, domicile, share class, horizon and fees matter. SPIVA's 2025 US report
shows different outcomes across equity and fixed-income categories; it does not
establish that every active manager fails or that any market guarantees accessible
alpha. Preserve dated evidence rather than embedding an underperformance rate as
a permanent constant. [S&P DJI, SPIVA U.S. Year-End 2025](https://www.spglobal.com/spdji/en/spiva/article/spiva-us/).

India small caps, emerging-market debt, frontier markets, distressed securities
and private assets are candidate research areas from the notes, not approved
allocations or assumed sources of alpha. Consider access, liquidity, capacity,
valuation quality, manager/operational risk and costs before assuming an advantage.
Negotiable fees and institutional access do not prove manager skill.

### 10. Combine top-down context with bottom-up research

Propose two linked research entry paths leading to the existing thesis and
valuation process:

- Top-down: dated country/macro evidence → sector exposure and cyclicality →
  security research. Record inflation, GDP, rates, monetary/fiscal policy,
  commodities, FX, demographics and political developments as evidence, with
  publication/knowledge dates and a stated transmission hypothesis.
- Bottom-up: explicit universe → sector/country-aware screens → qualitative
  company assessment → scenario valuation → owner review. A business-first
  process may start independently of macro forecasts, but portfolio country,
  sector and factor concentration still requires inspection.

Screen quality, valuation, balance-sheet vulnerability and momentum separately.
Examples include leverage, coverage, ROE/ROIC, earnings stability, cash conversion,
P/E, P/S, EV/EBITDA, dividend/earnings/cash-flow yield and operating-margin trends.
Support explicit peer membership, classification version, as-of date, data basis,
sample count, missing-data policy and a defined comparator (mean, median or
percentile). Do not silently hardcode the transcript's ten-sector taxonomy.
Low valuation multiples, high valuation yields and strong quality metrics have
different directions; define each screen's economic meaning.

Negative earnings, negative equity, inappropriate sector metrics and missing
denominators must yield explicit unavailable/not-comparable states. High ROE may
reflect leverage; high dividend yield can accompany distress; a cheap security
can remain a value trap. Quality plus attractive valuation is a research
hypothesis, not a guaranteed low-risk or superior-return label. Fama–French value
research is historical evidence, not a forecast for screened companies.
[Kenneth French, research bibliography](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/curriculum_vitae.html).

Qualitative work should cover products, regions, competitive advantages,
management strategy, margins, underperforming businesses, capital allocation,
governance and shareholder treatment. Record primary interviews/company visits
and secondary filings/analyst research with dates and evidence references.
Connect catalysts, contrary evidence and invalidation conditions to thesis reviews.
Optional technical analysis supports research; it does not become a trade command.
Twelve-month targets require an explicit valuation date, horizon, currency,
price/total-return basis and scenario assumptions under the existing contracts.

Avoid treating traditional multiples as assumption-free alternatives to DCF.
Both need economic interpretation; transparent scenarios and reverse valuation
help expose the growth, profitability and terminal-value assumptions being made.

### 11. Evaluate fund vehicles and managers explicitly

Propose a fund research record distinguishing legal vehicle, share class, active
or passive mandate, index/objective, replication method, domicile, dealing terms,
currency, hedge policy, distributions/reinvestment and dated documents. ETF does
not mean passive, and mutual fund does not mean active. Funds may provide pooling,
professional administration and accessible diversification, but concentration and
costs vary. Tax outcomes depend on account and jurisdiction; the screenshot's
tax-benefit statement is not a universal promise. [SEC investor bulletin on mutual
funds and ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/characteristics-mutual-funds-exchange-traded-funds).

Compare expense ratios, performance/management fees where applicable, sales or
redemption charges, spreads, commissions, turnover, liquidity, premium/discount
to NAV and relevant tax assumptions. Define gross/net performance and avoid
deducting expenses twice when already reflected in supplied fund returns. Index
tracking can have costs and tracking error; verify actual fees rather than assuming
all index products are cheap. [SEC introduction to index funds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-4).

Active-manager research should examine process, team changes, capacity, style
drift, benchmark fit, costs and performance evidence including unsuccessful or
closed funds. Distinguish benchmark-relative tracking error (volatility of active
returns), tracking difference (return gap) and alpha from a stated factor model.
Potential closet indexing warrants investigation rather than an automatic label.
Look-through holdings can reveal overlap across funds and direct stocks; missing
or stale holdings must make coverage and residual unknown exposure visible.

The current security registry is equity-focused. Fund, bond and derivative
semantics require a reviewed extension; entering a ticker alone does not provide
holdings look-through, bond analytics or option pricing.

### 12. Treat risk as several measurable dimensions

Retain volatility, beta and signed volatility contributions, and supplement them
with tail loss, drawdown, concentration, liquidity, credit, FX, liability mismatch
and model uncertainty where support is explicitly implemented. Beta measures
benchmark sensitivity, not total volatility; a stock with beta below one can have
substantial idiosyncratic volatility. Volatility alone cannot describe an
asymmetric or nonlinear payoff.

VaR/ES limits need loss convention, confidence, horizon, currency, loss basis,
estimator, effective tail counts and treatment of costs/rebalancing. A limit
breach should show the calculated value, limit and assumptions for human review.
VaR is not a maximum loss or a guarantee. A mean-variance efficient portfolio can
still violate a VaR/ES limit; movement to an efficient frontier alone does not
resolve a breach. Test feasibility under the actual risk constraint, and report
unavailable/infeasible results explicitly. The missing blue-star exercise cannot
justify a particular shift in weights.

For future protective puts/collars, define underlying, contract multiplier,
quantity, strikes, expiry, exercise/settlement style, premium, funding and costs.
Distinguish expiry payoff from pre-expiry valuation and full-portfolio drawdown.
Protection depends on strike, maturity and matched exposure; collars sacrifice
upside and can involve assignment. Static protection and dynamic hedging require
different models. Dynamic hedging additionally exposes gap, trading-cost,
liquidity and rebalancing assumptions. [OIC protective put](https://www.optionseducation.org/strategies/all-strategies/protective-put-married-put),
[OIC protective collar](https://prd-web.optionseducation.org/strategies/all-strategies/collar-protective-collar).

FX policy should distinguish asset currency, trading/share-class currency,
portfolio base currency and liability currency. Hedging foreign bonds is a
policy choice, not a universal requirement inferred from Maria's missing Q5.
Specify hedge ratio, instruments, roll schedule, costs/carry and residual basis
risk before calculating hedged returns. A fund's trading currency alone does
not establish its economic currency exposure.

Portable alpha is a separate future research concept: separate an intended alpha
source from unwanted beta, then combine it with a chosen market exposure. Merely
hedging the core does not make the whole portfolio beta-neutral; satellites may
also carry beta. Zero estimated beta does not imply zero risk, positive alpha or
perfect hedging. Funding, leverage, collateral and residual exposures matter.
[CFA Institute, Investing Separately in Alpha and Beta](https://rpc.cfainstitute.org/research/foundation/2009/investing-separately-in-alpha-beta-corrected).

### 13. Preserve diversification and estimation humility

Construction requires explicit compatible expected-return views and covariance,
or a risk-only objective when views are unavailable. Report sensitivity to input
perturbations, observation windows, covariance estimators and constraints before
implying robustness. More frequent sampling over the same calendar span does not
create an equally large increase in independent information about long-run means.
Long histories may mix regimes, and more data does not eliminate model error.

Moving toward a modeled frontier is conditional on its inputs. Expanding the
investable universe cannot worsen the mathematical optimum if the previous
feasible portfolios remain available, but need not improve it; real-world fees,
illiquidity and estimation error can erase apparent gains. Private-asset return
smoothing and stale valuations can understate observed volatility/correlation.
Do not assume alternatives always diversify or stock/bond correlations always
remain negative. Stress joint adverse moves and concentration by country,
sector, factor and underlying issuer when the necessary data is supported.

Diversification reduces some security-specific exposure; it does not guarantee
that every individual stock is more volatile than an index. The lecture's Swiss
stock comparisons, 15%-equity bond example, company incidents/fines and 2000–2002
equity/bond results are historical illustrations with incomplete source data,
not permanent constants or ready-to-replay fixtures. No exact returns from these
examples are claimed as reproduced.

Distinguish variation in a portfolio's returns through time, differences between
portfolios and the level of return. The often-quoted allocation percentages
(90%, or the lecture's 75%/12.5%/12.5%) are study-specific explanatory results,
not fractions of profits, causal guarantees or platform allocation rules.
[Ibbotson's CFA Institute presentation](https://rpc.cfainstitute.org/research/multimedia/2010/the-importance-of-asset-allocation)
supports this distinction. The attachment's
[ResearchGate reference](https://www.researchgate.net/publication/256006024_The_Importance_of_Asset_Allocation)
was inspected; the publisher/author presentation is preferred for interpretation.
Realized attribution remains Phase 9, after the ledger and performance foundations.

### 14. Keep signals in a research sandbox with human decisions

Quantitative and qualitative research should share traceable evidence, explicit
assumptions and recorded human judgment. The lecture's automatic signal-to-trade
description conflicts with permanent rule D and is not adopted. Momentum,
contrarian sentiment, CAPE and macro observations may inform a thesis; none should
silently generate BUY/HOLD/SELL, amend a portfolio or become an expected return.

Preserve the lecture exercises as candidate hypotheses only:

- Absolute/relative price momentum and operating momentum; define return/price
  basis, benchmark, lookback, sampling frequency and decision lag.
- Nikkei short/long moving averages, including the illustrated 3-/30-week pair;
  account for delayed entry/exit, whipsaw and trend reversals.
- Bulls/bears sentiment with illustrated 0.5/1.5 thresholds; resolve the
  transcript's inconsistent shorthand before any experiment. Specify neutral
  intervals, crossings versus levels, equality behavior, survey availability
  and zero-denominator handling. Sentiment can reflect respondent incentives.
- CAPE/valuation regimes and interest-rate relationships; investigate horizon,
  inflation/accounting definitions and regime stability instead of turning
  valuation into a precise near-term timing signal.
- The proposed consumer-confidence year-on-year -20% threshold for recession
  entry/exit; it lacks an identified series/vintage and reproducible validation
  here. Do not ship it as a recession detector or a cash/equity switching rule.

Any later experiment needs point-in-time constituent and macro data (including
release lags/revisions), delisted assets where relevant, execution after signal
availability, dividends, cash interest, costs, turnover and short-borrow/funding
constraints. Preserve all parameter trials; use chronological out-of-sample or
walk-forward evaluation and sensitivity analysis. Selecting the best threshold
on the same decade is not evidence of future performance. The course's own
warning about random patterns and separating experimental and retirement money
is central to interpretation, not an instruction to open accounts or trade.

The simple short-return exercise omits collateral, borrowing, margin, distributions
owed and potentially unbounded losses. Its sequential wealth compounding is not
a complete short-portfolio accounting model. “Missing the best days” charts
describe selected historical counterfactuals; specify whether counts refer to the
whole period or each year, and examine both missed gains and avoided losses using
an implementable rule before drawing timing conclusions.

Welch/Goyal's historical out-of-sample findings support demanding such tests,
not a claim that all forecasting is impossible. No forecasting model from the
lecture has been validated in this task. [NBER working paper and published-version
reference](https://www.nber.org/papers/w10483).

### Corrections and unresolved source details

These are source-review findings, not defects found or repaired in application
code. Original attachments and historical audits are not rewritten.

| Source location / claim | Disposition for the platform |
|---|---|
| Bottom-up lecture: beta below one means lower volatility | Correct interpretation: beta is covariance with the benchmark divided by benchmark variance; total volatility also includes residual risk. |
| Bottom-up lecture: “open sets core,” bankruptcy formula, “economic value to abitiate” | Likely transcription of a distress score and EV/EBITDA, but the precise score/formula is unverified. Do not invent a calibrated bankruptcy probability or choose a model variant silently. |
| SAA lecture: 40% equities rising 20% becomes a 48% weight | Normalize by total wealth: `0.40 * 1.20 / (0.40 * 1.20 + 0.60) = 44.444...%`, assuming other assets unchanged and no flows. 48% is equity value relative to initial portfolio value. |
| Estimation lecture: 20 assets require 490 covariance parameters | A symmetric 20-asset covariance matrix has `20 * 21 / 2 = 210` distinct entries: 20 variances and 190 covariances. Including 20 means gives 230 parameters. |
| Core/satellite: alternatives are poorly correlated; portable alpha leaves positive alpha | Treat diversification and alpha as uncertain hypotheses. Hedging one bucket does not remove all portfolio exposures or guarantee positive returns. |
| Owner summary: cannot passively hedge downside; passive equity/bond mix is optimal; frontier shift resolves VaR breach | Record policy intent, but qualify each claim as described in sections 9 and 12. No allocation or hedge is selected by this review. |
| Macro timing: -20% confidence rule; CAPE guarantees useful timing | Unvalidated hypotheses. Exact series, timestamped inputs, trading rule and out-of-sample evidence are missing. |
| Historical examples and quiz references | Dates, frequencies and transcript numbers are not sufficiently reliable for implementation fixtures; obtain original data/definitions before reproducing them. |

### Proposed delivery mapping and acceptance gates

This mapping identifies dependencies; it does not reopen approved phases or
authorize a new implementation phase. The canonical order remains in force.

| Proposed work | Existing foundation / boundary | Minimum evidence before claiming implementation |
|---|---|---|
| Policy, core/satellite labels, SAA/TAA targets and bands | Proposed construction extension; current Phase 6 accepts declared weights and common position bounds only | Version history; feasible totals/bands; explicit capital/notional/premium units; stale-results invalidation; no automatic decision or order |
| Peer-aware screens and qualitative workflows | Phases 3–5 supply equity facts, theses and valuation; screen engine and peer history are not yet implemented | Point-in-time fixtures; comparison universe; missing/negative metric cases; deterministic inclusion reasons; evidence linked to thesis |
| Fund/bond research and look-through | Reviewed security-model extension required | Distinct vehicle/share-class identity; as-of exposures; overlap reconciliation; incomplete coverage; cost-basis checks |
| Tail budgets, nonlinear hedges, FX and portable alpha | Risk Lab extension requires instrument pricing, aligned data and explicit contracts; existing Phase 6 does not implement these | Exact payoff/cost identities; expiry and pre-expiry separation; impossible constraints; tail cases; currency/hedge tests; no claimed guaranteed protection |
| Timing/robustness research | Future offline research scope; no new automatic provider calls | Known-date signal/execution tests; trial history; out-of-sample evaluation; costs and missing-data failure cases; no promotion to investor views |
| Holdings, cash, actual rebalancing records | Phase 7 only after explicit authorization | Ledger-derived positions/cash, idempotent imports and correction history |
| Net realized performance and attribution | Phase 8 then Phase 9 | Cash-flow-neutral TWR, dated XIRR, cost reconciliation, appropriate benchmarks and reconciling attribution |
| Public presentation | Phase 10 only | Prior acceptance gates and existing personal-portfolio publication rules |

For all proposed financial calculations, use typed backend domain functions,
analytical/offline tests and matching methodology. Preserve the approved
return/horizon/currency conventions, replay manifests, undefined values and
separation of evidence, assumptions, model outputs, investor views and decisions.
Show unsupported functions honestly; do not populate unfinished screens with
fabricated holdings or returns. Required engineering checks remain pytest, Ruff,
mypy, frontend tests, lint and build. Passing existing suites does not validate
the proposed strategies or establish new product functionality.

### Verification of this documentation update

On 2026-09-11, the existing offline suite completed with **407 passed, 9 skipped**
and **98.53%** statement/branch coverage. `TEST_DATABASE_URL` was not configured;
PostgreSQL integration coverage was not rerun. This result is distinct from the
historical Phase 6 audit's PostgreSQL-enabled 424-test result.

Ruff lint and formatting passed; mypy passed over 84 files. All 60 frontend tests,
ESLint and the production build passed. Existing browser-data/bundle-size build
warnings remain; the backend emitted a physical-core-detection fallback warning.
No new financial calculation, strategy validation or application feature was
implemented. This task changes only the master-brief continuation record and
this proposal document. Byte-prefix checks preserve the pre-task brief and
suggestions, and full-file hashes preserve all six historical audits. No commit,
push, database change or deployment was performed.

---

## Approved proceeding procedure — 2026-10-09

The owner approved the repository review's recommended sequence and explicitly
requested **Phase 8 acceptance and reproducibility closeout** as the current task.
This is an append-only continuation record. The master brief and all existing
phase audits/review records remain unchanged; approval is not evidence that later
features have been implemented or verified.

### Immediate approved work

- Restore a project-local Python environment from pinned dependencies, document
  portable recreation, and capture a platform-specific resolved environment.
- Complete fresh backend/PostgreSQL checks, Ruff/format/mypy/pre-commit, frontend
  tests/lint/build, and populated/missing/correction performance workflows.
- Create the previously absent PHASE_8_AUDIT.md with current dated evidence,
  original defects and repair status, acceptance gates and remaining limitations.
- Make downloaded performance reports independently replayable offline from their
  returned inputs and ledger snapshots, with actual backend-source and runtime
  identity. Reject changed evidence, incompatible environments and mismatched
  outputs; do not describe consistency checking as external attestation.
- Preserve prior records and create a reviewed source checkpoint after acceptance.
  Local verification does not establish hosted CI, real-account reconciliation,
  deployment, backup restoration or production readiness.

### Approved sequence after closeout

1. **Phase 9A: reconciled position contribution.** Start with ledger-derived,
   period-appropriate exposures. Include cash, booked dividends, fees and FX;
   specify intraday flow boundaries and geometric multi-period linking. Require
   the complete breakdown to reconcile to Phase 8 TWR within documented tolerance.
   Show any residual explicitly. Today's weights multiplied by historical returns
   are not an acceptable substitute for actual contribution accounting.
2. **Benchmark and active-risk analysis.** Use versioned benchmark identity,
   currency, total-return basis, calendar and effective dates. Align benchmark
   intervals with the portfolio before computing comparative statistics. Preserve
   the distinction between UTC calendar-day performance and trading-period risk.
3. **Factor regression.** Report coefficients, uncertainty, sample size/period and
   fit diagnostics. A statistical factor explanation is distinct from accounting
   contribution. Brinson remains conditional on historical classifications and
   appropriate benchmark weights; no automatic investment decisions are enabled.
4. **Phase 10: publication acceptance.** Require reproducible reports, deliberate
   private/public data separation, complete winning/losing position history,
   correction disclosures and operational checks including restore evidence.
   Hash chains identify continuity; they do not certify underlying broker data.

### Approved integration priorities and bounded extensions

A ledger-to-construction handoff must contain one coherent ledger version,
valuation/knowledge cutoffs, dated prices/FX, complete market-value weights and
explicit cash/instrument eligibility. Actual and hypothetical portfolios must
remain distinguishable; quantity and cost basis cannot stand in for weights.

Review the necessary fund/ETF support for the owner's eventual core/satellite
portfolio before claiming real-account readiness. Extend registry, accounting,
valuation and risk semantics deliberately under ASSET_TYPE_ROADMAP.md. Never
register funds as individual equities. Actual broker fixtures remain necessary
for a native Lightyear importer; no current connected account is assumed.

Advanced hedging, macro timing, portable alpha, more optimizers and additional
asset classes remain behind the immediate accounting/data/workflow needs. The
owner's illustrative passive-core allocation remains policy context, not an
implemented allocation default or a new expected-return assumption.

Detailed implementation and verification of later stages belong to their own
prospective plans and audits. The current closeout adds no attribution,
publication, provider integration, automated orders or fund functionality.

---

## Phase 9A authorized and locally accepted — 2026-10-09

The owner explicitly instructed: "Proceed with Phase 9A reconciled position
contribution." This prospective continuation supersedes the earlier review gate
only for this bounded stage. The master brief, previous audits/reviews and Phase 8
verification evidence remain intact. Detailed current evidence belongs to the new
[PHASE_9A_AUDIT.md](PHASE_9A_AUDIT.md); formulas and limits are specified in
[ATTRIBUTION.md](ATTRIBUTION.md).

### Implemented and verified scope

- Actual corrected ledger quantities, executed trades and period-appropriate
  opening exposures, including closed equities and within-segment round trips.
- Separate cash, booked net dividends, trade/account/conversion fees and FX effects.
  End FX translates local P&L; opening FX and conversion principal are explicit.
  Price/FX interaction is allocated to price. This is an endpoint convention,
  not a claim of observed transaction-time FX attribution.
- Daily and intraday external-flow boundaries with ledger sequence preserved;
  Phase 8 units link component P&L through forward normalized-wealth increments.
  The whole window reconciles to TWR with residual and fixed decimal-return
  tolerance 1e-12 + 1e-12 × abs(TWR); no forced balancing security or rescaling.
- Private, read-only transport returning performance/contribution from one locked
  snapshot, memory-only client integration, top/bottom equity effects, opening
  exposure details, explicit undefined results and offline replay download.
- Fresh acceptance: 579 backend tests including actual PostgreSQL, zero skipped,
  97.64% statement/branch coverage; 125 frontend tests, lint/build and configured
  quality gates passed. Populated, missing and corrected browser cases accepted,
  including desktop/mobile/dark views and private-state clearing.

### Decisions carried into the next stages

1. Preserve the boundary between accounting contribution, benchmark-relative
   results and statistical factor explanation. The next approved stage needs a
   separate benchmark/active-risk contract and acceptance record: versioned
   identity, effective dates, total-return basis, currency and interval alignment,
   explicit coverage and descriptive comparative statistics. Do not substitute
   price-only or unmatched-calendar series for a suitable total-return benchmark.
2. Historical sector attribution requires point-in-time classifications and, for
   Brinson, appropriate benchmark weights. Current registry sectors do not supply
   that evidence. UUID-level equity contribution is the accepted scope here.
3. Retain the declared FX allocation. A future transaction-time FX extension needs
   explicit additional marked boundaries/evidence and its own tests; it must not
   silently redefine existing downloaded reports.
4. Preserve source compatibility for replay. The backend-source identity changes
   when Phase 9A is added; old Phase 8 reports require the compatible 890dd4a
   source/environment or explicit regeneration from reviewed evidence. Never edit
   historical audit/download hashes merely to pass current replay.
5. Keep the previously approved integration priorities: coherent dated ledger-to-
   construction handoff, deliberate fund/ETF support, actual broker fixtures and
   operational restore evidence before claiming real-account/platform readiness.
   This stage adds none of those extensions or publication.

This append records the bounded implementation and remaining sequence. Local
acceptance is not broker certification, hosted CI or deployment evidence. A reviewed
local source checkpoint follows the checks; no remote push/publication was requested.

Exact-byte replay evidence for Phase 9A also retains an archival source bundle.
Git line-ending conversion can change the conservative source fingerprint; both
synthetic exports passed replay from the separately extracted accepted source.
The bundle preserves evidence without revising historical hashes or adding a
second active calculation implementation.


## 2026-10-11 — approved continuation: Phase 9B benchmark/active-risk closeout

The owner instructed continuation of the approved sequence after Phase 9A.
Implemented bounded Phase 9B: explicit versioned selection for the chosen
account/report, reviewed gross/net total-return levels in account currency,
aligned daily and cumulative comparisons, realized TE/IR/beta/correlation,
coherent optional position contribution and offline replay. See
[BENCHMARK.md](BENCHMARK.md), [Phase 9B plan](superpowers/plans/2026-10-11-phase-9b-benchmark.md)
and the new [PHASE_9B_AUDIT.md](PHASE_9B_AUDIT.md). This entry is appended;
the permanent master, historical audits and previous suggestions are preserved.

Acceptance evidence: 625 backend cases including actual PostgreSQL, 97.76%
statement/branch coverage, 133 frontend cases, quality/build gates, synthetic
complete/missing/corrected responsive privacy workflows and three actual private
API exports replayed from independently extracted exact source. The browser
download button was exercised, but its saved file was not independently obtained;
actual browser file delivery remains unverified. No hosted/production/broker claim.

The bounded selection is retained with each report. The master brief's eventual
durable portfolio benchmark default remains later settings work. Do not infer
complete Phase 9 delivery from this substage. No automatic provider ingestion,
currency conversion, factor alpha, rolling analytics or Brinson was added.

Recommended next procedure within the approved sequence:

1. Specify a separate factor-regression stage before implementation: reviewed
   dated factor and risk-free series, actual portfolio excess returns, matching
   currency/calendar/units, factor version/provenance and complete coverage.
2. Document the regression estimators, intercept/betas/residuals, sample minimum,
   collinearity/rank/zero-variance behavior and uncertainty diagnostics. Treat
   historical alpha as a model-dependent estimate rather than persistent skill
   or an investor expected-return view. Require analytical identities and replay.
3. Retain this stage's complete paired funded-window policy. The first-funding
   regression showed why a post-funding portfolio day must not be compared with
   a full benchmark day. A future alternate/calendar policy needs an explicit
   method change and its own acceptance, not silent reduced samples.
4. Add durable versioned benchmark defaults and reviewed currency conversion
   only with dedicated settings/data contracts. Provider licenses and timestamp
   evidence must precede any automatic licensed-data archive.
5. Keep Brinson conditional on historical benchmark weights/classifications and
   reconcile its effects. Continue broker/fund typing, real-account reconciliation,
   operational backup/restore and publication through their separate gates.

This prospective entry does not rewrite earlier findings or make historical
acceptance appear cleaner. Investor benchmark suitability and investment decisions
remain the owner's judgment.


## 2026-10-11 — approved continuation: Phase 9C historical factor regression

The owner instructed continuation after Phase 9B, authorizing the next bounded
stage. Implemented supplied one-to-six-factor historical regression against
actual ledger-derived daily portfolio excess returns. Centered/scaled SVD OLS
returns signed coefficients, HC3 SE/t-statistics, R²/adjusted R² and daily residuals
with explicit period/count/df and complete funded coverage. Daily alpha remains
a model-dependent historical estimate with uncertainty, not an expected-return
view or evidence of persistent skill. See [FACTORS.md](FACTORS.md),
[Phase 9C plan](superpowers/plans/2026-10-11-phase-9c-factors.md) and the new
[PHASE_9C_AUDIT.md](PHASE_9C_AUDIT.md).

Local acceptance: 679 backend tests including actual PostgreSQL, zero skipped,
97.87% combined coverage; 141 frontend tests, quality/hooks/lint/build gates;
synthetic populated/missing/corrected responsive privacy checks and three actual
API exports replayed from working and separately extracted 86-file exact source.
The browser export control was exercised, but its saved file was not independently
obtained. Actual browser file delivery remains unverified; no hosted/production,
broker or provider-data claim. All historical records are preserved, and this entry
is appended to the existing suggestions rather than replacing prior findings.

Recommended next procedure:

1. Prioritize a dedicated versioned portfolio benchmark setting and reviewed
   factor-data readiness. The current report selections are explicit but temporary;
   the master brief's eventual portfolio-level benchmark configuration is still open.
2. Specify currency/calendar reconciliation before using actual public research
   factors. USD trading-day data and its risk-free convention do not silently become
   GBP daily calendar intervals. Require documented transformations and supplied
   evidence, then analytical/replay acceptance; never invent weekend observations.
3. Address serial dependence with a separately specified HAC or bootstrap policy
   before adding significance decisions or confidence intervals. HC3 handles
   heteroskedasticity only. Rolling beta/capture need declared windows, estimator,
   coverage and overlap/sample uncertainty; large t-statistics are not proof of skill.
4. Keep Brinson conditional on real historical classifications and benchmark weights.
   Existing current registry metadata does not meet that requirement. Prefer the
   accepted position contribution and factor diagnostics until those data exist.
5. Retain approved ledger-to-construction handoff, typed fund/ETF support, actual
   broker fixtures and operational restore checks as separate integration work.
   Publication remains after its own privacy, source and operational acceptance.

This bounded stage does not declare all broader Phase 9 goals complete. Numerical
replay is exact in the tested local runtime; retain compatible archived source and
environment rather than changing historical report hashes to force compatibility.


## 2026-10-12 — approved continuation: Phase 9D benchmark settings closeout

The owner continued after Phase 9C and reiterated the master plan. Implemented
bounded Phase 9D: immutable portfolio benchmark identity/reason revisions, private
history/save/clear, idempotent retries, independent ledger/settings versions and
explicit report selection receipts. This fulfills the master brief's portfolio
benchmark configuration requirement without hardcoding an index or supplying data.
See BENCHMARK_SETTINGS.md, prospective FACTOR_DATA_READINESS.md, the separate
2026-10-11-phase-9d-settings.md plan and new PHASE_9D_AUDIT.md.

Acceptance: 696 backend cases including real PostgreSQL, 97.89% coverage,
147 frontend cases, quality/hooks/lint/build, synthetic responsive save/report/
clear/persistence/privacy checks, three actual API exports replayed from working
and independently extracted 87-file source, and 148 historical preservation checks.
The new audit records early port/runner/test-wrapper findings rather than rewriting
old records. Browser saved-file delivery remains unverified; old qualifications
and exact archives remain unchanged. No hosted/deployment/real-provider claim.

Recommended next procedure under the master:

1. Specify a separately versioned common-valuation-interval method and reviewed
   real-factor adapter. Preserve daily ledger accounting, exact evidence provenance,
   complete funded windows and explicit aggregation. Require genuine reviewed
   source/fixture, currency, funding/hedging and risk-free interval definitions.
2. Keep current manual UTC daily factor inputs until that acceptance exists. Do
   not invent weekend factors, multiply excess/spread returns by FX spot levels,
   silently reduce samples or certify latest retrieval as historical publication.
3. Then scope HAC/bootstrap and rolling beta/up/down capture with window, estimator,
   dependence, coverage and sample context. Large historical t-statistics remain
   descriptive model estimates, not persistent skill or expected-return views.
4. Keep Brinson conditional on historical classifications and benchmark weights.
   Current registry metadata does not supply these inputs. Retain reconciled
   security contribution and accepted factor diagnostics while data are missing.
5. Continue fund typing, real broker reconciliation, ledger-to-construction handoff,
   operational restore and publication through their own integration/privacy gates.

This is a bounded Phase 9 substage; it does not declare Phase 9 or the complete
master plan finished. Saved identities establish explicit policy history, not
benchmark suitability or real-factor calendar/currency comparability.


## 2026-10-13 — approved continuation: Phase 9E native factor-source review

The owner continued after Phase 9D and again during closeout. Implemented a strict
offline French developed five-factor daily CSV parser and private source-review
workflow. It preserves native USD/date labels, converts percentages exactly,
retains missing-value semantics and rejects malformed rows rather than filling or
silently dropping them. Source review is separate from daily factor regression;
readiness remains false until common-boundary/currency/funding/provenance acceptance.

Verified against a six-row actual provider excerpt; the full downloaded member
parsed to 9436 rows. Retained only the minimal attributed numerical fixture plus
source hashes/retrieval evidence, with no general redistribution-rights claim.
Actual browser download delivery and independent replay succeeded for this source
receipt. Two API receipts also replayed from working and extracted 89-file source.
All 733 backend and 153 frontend tests passed, coverage 97.93%, alongside required
quality/lint/build gates. Preserved all 186 historical records/suggestions prefix.
Earlier audit/download qualifications remain unchanged.

Recommended next procedure:

1. Implement the separately versioned common-boundary measurement described in
   FACTOR_ALIGNMENT.md, with independent unit-wealth/TWR reconciliation tests and
   explicit missing/unfunded/irregular-window outcomes. Keep daily accounting intact.
2. Require an actual reviewed boundary-valuation/FX/funding fixture and publication
   evidence before connecting native research factors to a real portfolio. A clearly
   labelled USD research view of a GBP account is a candidate; it is not an adopted
   conversion policy and needs actual synchronized valuations/flow conversions.
3. Preserve native spread definitions and period-effective RF. Never multiply a
   spread by an FX spot level, invent weekend factors or certify retrieval/vintage
   as proof of historical publication. A source hash is consistency evidence only.
4. Scope HAC/bootstrap and rolling beta/up/down capture after alignment, including
   lag/window/dependence/sample policies. Keep Brinson conditional on historical
   classifications and benchmark weights. Broker/fund/restore/publication work
   retains its own integration and privacy acceptance.

Current scope/evidence: FACTOR_SOURCE_IMPORT.md, prospective FACTOR_ALIGNMENT.md,
new PHASE_9E_AUDIT.md and the separate execution plan. Phase 9 remains incomplete.
