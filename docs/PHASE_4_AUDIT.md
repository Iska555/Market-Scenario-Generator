# Phase 4 thesis audit — 2026-09-09

Authorization: "Commit and continue with Phase 4". Phases 1–3 were committed as
`88f4390` after 238 backend tests including PostgreSQL, 97.22% combined branch
coverage, Ruff, formatting, mypy, dependency consistency and 14 frontend tests,
lint and build passed. No push or deployment was requested. The canonical master
brief is preserved. Phase 5 has not started.

## Scope and repair record

| Original location / function | Classification | Phase 4 disposition |
|---|---|---|
| `backend/src/research/` (no thesis domain) | DESIGN DEBT | New typed thesis package stores complete immutable owner-authored revisions and review evidence |
| `backend/main.py` router registration | DESIGN DEBT | Adds thin private thesis routes through existing key/session dependencies |
| `backend/migrations/versions/20260908_01_research.py` existing schema | CORRECT AS IMPLEMENTED | Original migration retained; a separate descendant adds thesis tables and immutable triggers |
| `frontend/src/App.jsx` navigation | DESIGN DEBT | Adds focused private Thesis workspace; existing Risk Lab remains separate |
| New `research/thesis/repository.py` create/append response | CONFIRMED BUG during development | DB refresh makes Decimal serialization consistent between immediate write response and later history reads |
| New `frontend/src/features/thesis/thesis.js` `saveThesis` | CONFIRMED BUG during review — FIXED | Preserves dirty review content and its selected historical revision; regression test and independent re-review passed |
| New `frontend/src/features/thesis/thesis.js` `reloadThesis` | POTENTIAL BUG — FIXED | Identity checks preserve edits made after a reload request starts; regression test passed |

The PostgreSQL contract covers stable security/thesis/revision identities,
immutable snapshots of ticker/exchange, sequential version allocation, optimistic
revision conflicts, review-to-revision foreign keys, exact decimals, and migration
compatibility with existing research data. These are storage guarantees for
ordinary application/database operations; database owners can alter triggers.

## Verification

Final local verification on Windows, Python 3.14.0, Node 24.12 and PostgreSQL 17.11:

- Full backend suite: **273 passed**, none skipped with `TEST_DATABASE_URL` set.
  Combined statement/branch coverage **97.82%**, above the 95% threshold. The new
  thesis package has 100% measured statement/branch coverage.
- Four dedicated PostgreSQL cases passed: price precision and update/delete
  rejection; competing revision writers; cross-thesis review rejection;
  upgrade/downgrade preservation of existing research. Existing migration tests
  also verify agreement between runtime metadata and the full migration chain.
- Ruff lint and formatting passed (57 files); mypy passed (55 source files).
  Dependency consistency and all pre-commit hooks passed. Hooks used the project
  Python environment and a temporary writable hook cache.
- Frontend: **26 tests passed**, lint passed, production build passed. Tests cover
  the simultaneous thesis/review draft case, stale reload/selection responses,
  private-key handling, exact decimal presentation and rendered history fields.
- Browser using synthetic data in an isolated PostgreSQL schema: created a
  security and thesis, appended revision 2, inspected unchanged revision 1,
  attached a manual review to revision 1, confirmed unchanged thesis status,
  and reproduced a stale-save 409 with draft text retained. Disconnect cleared
  private state. Final contextual heading/layout was visually inspected.
- Independent review found one material issue (unsaved review loss); repaired,
  regression-tested and re-reviewed with no additional findings. The repair was
  verified through automated tests; the final browser reconnect was interrupted
  by the disposable database process ending, so no post-repair browser claim is made.
- Synthetic browser schema removed. The temporary backend/frontend processes
  were no longer running at cleanup verification; `pg_ctl status` confirmed the
  temporary database was stopped. An earlier shutdown attempt was blocked by an
  automatic approval usage-limit error, with no cleanup command executed then.
- Canonical master brief SHA-256 remains
  `5615B5E7C4747A300C7FE54DF06CD41995A2A5F04CD82A42D69E76AE4E380AEA`.

Phase 4 changes are left uncommitted for owner review, separately from the
requested foundation commit. No push, deployment or Phase 5 work occurred.

## Assumptions and remaining limits

See [THESIS.md](THESIS.md) for API fields, time/units, configuration and limitations.
No new financial estimator is introduced. Rates, value ranges, prices, conviction
and decisions are owner inputs. A review is not a transaction and does not change
thesis status. Sources are narrative references rather than attached immutable
fundamental snapshots. There is one shared owner key, no author-specific identity,
no externally certified timestamp, and no offline draft persistence. A network
failure after commit requires checking history before retrying; reviews have no
idempotency token. Live pagination can shift when another writer adds records.
Database/network failures use driver and browser timeout behavior; there is no
application-wide request deadline. A stalled connection can keep the workspace
busy until it fails or the owner disconnects. Disconnect ignores late responses;
it does not cancel a server-side transaction already in progress.

Production database deployment and hosted CI execution are outside this local
verification. Inherited frontend build warnings concern the browser support
dataset and bundle size; neither changes the thesis storage semantics.
