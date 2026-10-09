# Investment Management Workspace — UX refinement

Work requested 2026-09-13; verification completed 2026-09-15. This is a focused
refinement within the authorized Phase 7 boundary. No financial formula, backend
authorization guard, security registry schema or database migration was changed.
No Phase 8, attribution, public track record or investment decision automation
was added. The supplied checkout already contained substantial Phase 4–7 changes;
those changes and historical audits were preserved.

## Delivered behavior

- Current product branding, browser title, shell and API title use **Investment
  Management Workspace**. Overview is the initial destination. Navigation groups
  the eight implemented destinations under Portfolio, Research, and Risk &
  scenarios. Security registration remains within Thesis.
- One global **Private workspace key** unlocks the existing private research and
  accounting modules. Its helper explicitly distinguishes it from broker and
  market-data credentials. Password input clears immediately on submission.
  The secret lives only in memory, outside public store snapshots. Nothing
  writes it to localStorage, sessionStorage, IndexedDB or cookies.
- The existing `RESEARCH_API_KEY` / `X-Research-Key` authorization boundary is
  unchanged: research, valuation, construction, historical scenarios and
  accounting already share `require_research_access`. Validation uses an
  authenticated research read; module loading errors remain visible separately.
  This is a frontend session abstraction, not a new server token or permission
  tier. Public price-history simulation endpoints retain their existing access.
- Navigation clears the departing private module's unsaved state but preserves
  the unlock. **Lock workspace** clears registered controllers and remounts local
  form/result state, preserving the selected destination and theme. Refresh
  starts locked. Pending responses cannot restore cleared private state. A write
  already sent may still finish on the server; locking is not transaction rollback.
- Overview reads existing account identities, ledger-derived equity quantities
  and trade-date cash, with optional research identity labels. It preserves exact
  decimal strings and makes no financial calculations. Empty accounts, empty
  holdings and unavailable reads have different states. There are no invented
  holdings, NAV, performance, weights, review counts or saved valuation summaries.
- Construction identifies its source as hypothetical declared weights. It does
  not load current ledger weights or treat quantities/cost basis as market-value
  allocations. Only implemented reference/candidate strategies are shown.
- Risk Lab controls use **Forward return assumption**, distinguish risk-only and
  historical diagnostics, retain the precise zero-log-drift caveat, and explicitly
  state that saved investor-view conditioning is unavailable here. No saved
  valuation output is silently adopted. Single-asset Gaussian and GMM descriptions
  are univariate; irrelevant covariance and rebalancing selectors are absent.
- New frontend portfolio and historical replay/bootstrap requests default to
  buy and hold. Explicit daily/per-observation choices remain supported. Portfolio
  Risk Lab shows the current weight policy even with Advanced settings collapsed.
  Backend defaults and financial implementations are unchanged; requests and
  manifests carry the selected values.
- Ledoit-Wolf, GMM, EWMA, return assumptions, rebalancing and history-window
  tradeoffs have concise explanations. The current equity-only boundary remains
  visible; the separate asset-type roadmap describes planned typed support.

## Risk control classification

| Control | Presentation and reason |
| --- | --- |
| Asset / portfolio, scenario family | Normal investment decisions |
| Horizon, initial scenario value, valuation currency | Normal; units remain explicit, no FX conversion inferred |
| Forward return assumption | Normal; only zero log drift and historical diagnostic choices implemented |
| Estimation window | Normal 3/5/10-year presets and custom input; economic sample tradeoff stays visible |
| Paths, seed, confidence, risk-free rate | Advanced; exact values retained |
| Periods per year | Default annualization convention 252, inspectable/editable in Advanced settings |
| Portfolio covariance | Advanced; Ledoit-Wolf default with plain-language help |
| Portfolio rebalancing | Advanced selector, normal-mode policy summary; buy and hold default |
| GMM component count/regularizer, EWMA lambda | Advanced and conditional on the selected family |
| Single-asset covariance / rebalancing selectors | Not applicable as owner-facing controls; shared API fields retained |
| Historical bootstrap path count, block length, seed, confidence | Advanced resampling/reproducibility disclosure |
| Supplied history, calendar and knowledge/publication cutoffs | Remain explicit where needed to define evidence and economic timing |

## Defects and repair status

| Original file / function | Finding | Status / limitation |
| --- | --- | --- |
| `frontend/src/App.jsx::SimulationConfig` | Mixed investment decisions and technical controls; inappropriate single-asset selectors | Extracted into `components/SimulationConfig.jsx`; normal/advanced separation, exact contracts preserved |
| Five private `*Workspace.jsx` entry components | Independent key forms exposed backend authentication repeatedly | Removed; shared connection hook and one shell control |
| `frontend/src/scenarioContract.js::DEFAULT_ASSUMPTIONS` and `features/stress/stress.js::emptyStress` | Routine portfolio defaults implied frequent rebalancing | Explicit frontend buy-and-hold defaults; methodology and regression tests updated |
| `components/PlatformShell.jsx`, `App.jsx::PortfolioPlatform` | Obsolete identity and no natural portfolio landing destination | New branding, Overview, blank Risk Lab asset inputs |
| `features/workspace/session.js::unlock` / `App.jsx::SessionContents` (introduced during this pass) | Initial epoch reset sent unlock attempts back to Overview | Repaired after independent review; navigation lives outside cleared state, locked unlock does not remount key form |
| `scenarioContract.js::MODEL_OPTIONS` | Shared Gaussian copy described correlation for one asset | Separate volatility-only single-asset explanation |

No quantitative defect was discovered that required changing established formulas.

## Files changed by this refinement

Existing files (including files already untracked or modified when work began):

- `README.md`, `backend/main.py`, `backend/tests/test_research_contracts.py`
- `docs/ARCHITECTURE.md`, `docs/METHODOLOGY.md`, `docs/THESIS.md`, `docs/ACCOUNTING.md`
- `frontend/index.html`, `frontend/src/App.jsx`, `frontend/src/index.css`
- `frontend/src/components/PlatformShell.jsx`, `PlatformShell.test.js`,
  `ScenarioResults.jsx`, `ScenarioResults.test.js`
- `frontend/src/scenarioContract.js`, `scenarioContract.test.js`
- `frontend/src/features/construction/ConstructionWorkspace.jsx`,
  `ConstructionWorkspace.test.js`, `construction.js`
- `frontend/src/features/ledger/LedgerWorkspace.jsx`, `LedgerWorkspace.test.js`, `ledger.js`
- `frontend/src/features/thesis/ThesisWorkspace.jsx`, `ThesisWorkspace.test.js`,
  `thesis.js`, `thesis.test.js`
- `frontend/src/features/valuation/ValuationWorkspace.jsx`,
  `ValuationWorkspace.test.js`, `valuation.js`
- `frontend/src/features/stress/StressWorkspace.jsx`, `StressWorkspace.test.js`,
  `stress.js`, `stress.test.js`

New files:

- `frontend/src/components/SimulationConfig.jsx`, `SimulationConfig.test.js`
- `frontend/src/features/workspace/session.js`, `session.test.js`, `sessionContext.js`,
  `PrivateWorkspace.jsx`, `overview.js`, `overview.test.js`, `Overview.jsx`,
  `OverviewWorkspace.test.js`
- `docs/ASSET_TYPE_ROADMAP.md`, this report, and
  `docs/superpowers/plans/2026-09-13-workspace-ux.md`

`MASTER_BRIEF.md`, `BRIEF_SUGGESTIONS.md`, previous phase audits and historical
plans were not rewritten by this refinement.

## Verification

- Backend: **456 passed, 13 skipped**, **97.82% branch-aware coverage** (95% gate).
  The skips require an isolated PostgreSQL `TEST_DATABASE_URL`; no such database
  was configured for this run. The existing Windows joblib warning falls back
  from unavailable physical-core detection to logical cores.
- Frontend: **109 passed**. Added/extended checks cover shared auth across all
  five private modules, lock/unmount/late responses, failed unlock navigation,
  absence of durable secret storage, Overview records and empty/unavailable
  states, branding, removal of local password forms, exact advanced API values,
  return-label mappings and rebalancing defaults.
- Added seven backend contract cases covering rejection of six deferred asset
  types and unchanged equity identity normalization.
- Ruff and mypy pass; mypy checks **98 source files**. Frontend ESLint and Vite
  production build pass. Vite reports its existing >500 kB chunk advisory and
  old Browserslist data; neither is a build failure.
- Two independent scoped code reviews found the unlock-navigation issue and
  single-asset wording issue above. Both were repaired; final scoped review
  found no actionable correctness or security issues.
- Browser inspection covers Overview, Ledger, Construction, Thesis, Valuation,
  Single-asset Risk Lab, Portfolio Risk Lab, and Historical & shocks at desktop
  and a **390 × 844** mobile viewport. Checked branding, hierarchy, controls,
  horizontal navigation, empty/loading states and disclosure. The page width
  stayed within the mobile viewport. An isolated read-only loopback fixture
  returned empty record lists for connected-screen inspection; no account or
  portfolio records were created. Production PostgreSQL connectivity and
  populated private user records were not exercised by this visual fixture.
- Final browser session check confirmed that locking preserves the selected
  destination, re-unlocking does not restore unsaved private input, and refreshing
  returns to a locked Overview. The test used only a disposable local fixture key.

## Deliberately deferred

Saved investor-return-view/CAPM drift integration into Monte Carlo, current
ledger-to-Construction weights, target portfolio mode, dashboard research-count
aggregation, saved latest-valuation summaries, ETF/fund registry implementation,
look-through exposure, bond analytics, native broker imports, performance,
attribution and publishing. Their boundaries are explicit. No deployment or
commit was performed; the work is left for owner review before Phase 8.
