# Phase 9A local acceptance evidence — 2026-10-09

This directory contains fresh evidence for [PHASE_9A_AUDIT.md](../../PHASE_9A_AUDIT.md).
All portfolio/transaction/security records and marks in the JSON/screenshots are
explicit synthetic acceptance fixtures, never owner or broker records. No private
workspace credential is included. Earlier Phase 8 evidence remains untouched.

| Artifact | What it establishes |
| --- | --- |
| `backend.txt` | Full PostgreSQL-enabled run: 579 passed, zero skipped, 97.64% statement/branch coverage |
| `checks.json` | Full verification runner exit status and elapsed duration per gate |
| `dependencies.txt`, `resolved-python.txt` | Dependency compatibility and resolved local Python runtime packages |
| `ruff.txt`, `format.txt`, `mypy.txt`, `hooks.txt` | Full runner quality gates |
| `staged-hooks.txt` | Configured hooks over final staged/new source files before checkpoint |
| `benchmark.txt` | Existing scenario benchmark; not a contribution throughput guarantee |
| `frontend.txt`, `lint.txt`, `build.txt` | Full runner client gates |
| `final-frontend.txt`, `final-lint.txt`, `final-build.txt` | Final client gates after temporary browser diagnostics were removed |
| `api-postgres.txt` | Focused contribution API and actual PostgreSQL acceptance |
| `browser-evidence.json` | Complete synthetic daily and pre-flow valuation input |
| `browser-downloaded-report.json` | Actual browser-downloaded version-4 contribution report: TWR15%, equity+20pp, accountfee−5pp |
| `corrected-report.json` | Actual API export after correcting reversal/version5: TWR20%, equity+20pp, no accountfee |
| `downloaded-replay.txt`, `corrected-replay.txt` | Successful offline verification of the two retained reports |
| `accepted-replay-source.zip`, `accepted-source.json` | Exact backend source bytes/offline entry points and their source/archive SHA-256, preserving line endings independently of Git checkout conversion |
| `archived-downloaded-replay.txt`, `archived-corrected-replay.txt` | Successful replay of both exports using source extracted from that archive |
| `contribution-desktop.jpg` | Initial populated contribution view |
| `contribution-corrected-desktop.jpg` | Corrected reconciled+20pp/residual/tolerance view |
| `contribution-mobile.jpg`, `contribution-mobile-dark.jpg` | Responsive corrected view in light/dark themes |
| `contribution-missing.jpg` | Final-client undefined whole-window contribution when the intermediate equity quote is omitted |
| `preservation.json` | Task-entry full-file SHA-256 comparisons for historical records/evidence and original suggestions byte-prefix comparison: 35/35 pass |
| `cleanup.txt` | Disposable schema removal and local acceptance-service shutdown |

JSON replay requires the accepted Phase 9A backend source and compatible runtime.
The source digest is recorded within each embedded performance manifest; Git
metadata reflects the source base at calculation time while the digest includes
the actual new/uncommitted backend source. Adding further backend files can change
this conservative identity. Keep compatible source/environment rather than editing
saved report identity. These checks establish consistency, not independent broker
attestation or a trusted external signature.

To replay the retained fixtures from their exact source, run from the repository
root with the documented compatible Python environment:

```powershell
Expand-Archive docs/verification/phase9a-2026-10-09/accepted-replay-source.zip .verification/phase9a-source
./backend/.venv/Scripts/python.exe .verification/phase9a-source/scripts/replay_contribution.py docs/verification/phase9a-2026-10-09/browser-downloaded-report.json
./backend/.venv/Scripts/python.exe .verification/phase9a-source/scripts/replay_contribution.py docs/verification/phase9a-2026-10-09/corrected-report.json
```

The archive is a bounded evidence bundle for offline calculation, not a second
active implementation or a full application/deployment package. Source bytes
must remain unchanged for exact fingerprint verification; runtime/package versions
must match the manifests. Archive metadata records 74 files and Python 3.12.14.

Logs retain original check output. Their paths describe this Windows environment;
timings are local observations. Synthetic services used the disposable local test
database/schema and were stopped after acceptance. No production/hosted CI or
real-account claim follows from these artifacts.
