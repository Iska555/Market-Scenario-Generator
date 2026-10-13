# Phase 9E acceptance evidence

Work and source retrieval: 2026-10-12. Closeout: 2026-10-13. Entry: 913ccb1.
Scope and development findings: [Phase 9E audit](../../PHASE_9E_AUDIT.md).

- `checks.json` records the completed full runner: all ten gates exited 0.
  `backend.txt`: 733 passed, no skips, 97.93% coverage. `frontend.txt`: 153 passed,
  no failures/skips. Quality/dependency/hooks/lint/build logs are retained alongside.
  `staged-hooks.txt` records the final staged checks.
- `browser-source-review.json` is the **actual delivered browser download**, copied
  byte-for-byte from its local saved path. `api-source-review.json` and
  `api-empty-window.json` are actual private API exports. `invalid-source.txt`
  records a sanitized no-store422 response. Fixture account is disposable GBP;
  source rows come from the actual minimal provider excerpt.
- `working-*-replay.txt` and `archived-*-replay.txt` verify all three receipts.
  `accepted-replay-source.zip` contains 89 exact backend/entry-point Python files.
  `accepted-source.json` records archive/code hashes and Python version. The archive
  excludes migrations/dependencies/frontend/deployment. Use compatible runtime.
- `full-source-observation.json` records that the full provider member parsed to
  9436 rows and its selected rows matched the six-row fixture. It is a count/hash
  observation, **not** independent full-dataset replay. The full dataset is not
  redistributed here. The exact attributed minimal fixture and retrieval/hash
  provenance are in `backend/tests/fixtures/french_developed_daily`.
- `source-review-desktop.png` and `source-review-mobile.png` were visually
  inspected. Native USD, decimal rows and explicit alignment blockers are visible.
  The mobile table scrolls within a 375-pixel document at a 390×844 viewport.
- `preservation.json` records 186 historical full-file/original-suggestions-prefix
  checks. `cleanup.txt` records removal of only the named disposable schema and
  acceptance-service shutdown. Earlier audits/evidence remain unchanged.

Browser acceptance used the pasted text field; file chooser delivery was not
tested. Source-review download delivery/replay was verified this phase, without
altering older reports' download qualifications. No currency/calendar conversion,
real-account regression, publication or hosted-deployment acceptance is implied.
