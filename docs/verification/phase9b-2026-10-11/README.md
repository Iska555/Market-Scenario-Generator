# Phase 9B local acceptance evidence — 2026-10-11

Fresh evidence for [PHASE_9B_AUDIT.md](../../PHASE_9B_AUDIT.md). All account,
transaction, security, quote and benchmark records in the JSON/screenshots are
explicit synthetic acceptance fixtures, not owner/broker records or a real index.
No private authentication key is included. Earlier evidence remains untouched.

| Artifact | What it establishes |
| --- | --- |
| `backend.txt`, `checks.json` | Full PostgreSQL-enabled verification: 625 passed, no skipped, 97.76% statement/branch coverage; all ten gates exit zero |
| `dependencies.txt`, `resolved-python.txt` | Dependency compatibility and resolved Python environment |
| `ruff.txt`, `format.txt`, `mypy.txt`, `hooks.txt` | Full-run quality gates |
| `staged-hooks.txt` | Configured hooks covering final staged/new source before checkpoint |
| `frontend.txt`, `lint.txt`, `build.txt` | 133 client cases, lint and production build |
| `benchmark.txt` | Existing scenario workload timing; not comparison endpoint throughput |
| `analytical.txt`, `api-postgres.txt` | Focused 41-case analytical and five-case private API/actual PostgreSQL acceptance |
| `browser-evidence.json`, `browser-benchmark.json` | Complete synthetic daily/pre-flow valuations and explicit benchmark input |
| `complete-report.json` | Actual private API export: version 4, portfolio15%, benchmark10%, difference5pp, relative4.54545% |
| `missing-report.json` | Actual private API export with omitted middle benchmark level: no complete paired window; independent portfolio/contribution retained |
| `corrected-report.json` | Actual private API export after fee reversal/version5: portfolio20%, benchmark10%, difference10pp, relative9.09091% |
| `complete-replay.txt`, `missing-replay.txt`, `corrected-replay.txt` | Successful working-source offline verification |
| `accepted-replay-source.zip`, `accepted-source.json` | Exact accepted backend Python bytes plus three offline entry points; source/archive SHA-256, 80 files and runtime metadata |
| `archived-complete-replay.txt`, `archived-missing-replay.txt`, `archived-corrected-replay.txt` | Successful verification using independently extracted source archive |
| `comparison-desktop.jpg`, `comparison-missing.jpg` | Populated and missing benchmark browser views |
| `comparison-corrected-desktop.jpg` | Corrected same-snapshot comparison with clear cumulative units and sample limitation |
| `comparison-mobile.jpg`, `comparison-mobile-dark.jpg` | Corrected responsive light/dark views |
| `browser-acceptance.txt` | Observed browser workflow, privacy/responsiveness results and actual download-delivery qualification |
| `preservation.json` | 70/70 task-entry hashes/prefix checks for historical master, audits, evidence and original suggestions |
| `cleanup.txt` | Named disposable schema removal, test schema absence and service/port shutdown |

The browser download control was activated, but its saved file was not obtained
for independent verification. The retained reports are API exports; none is
labelled as an actual browser download. Actual browser file delivery remains
unverified in this phase. Offline report verification and financial comparison
are supported by the artifacts above.

Source hashing covers raw backend source bytes, including uncommitted additions
at calculation time. Adding files or Git checkout line-ending conversion can
change that identity. The archive preserves exact accepted bytes. Compatible
Python/package versions are required; see each manifest and `resolved-python.txt`.
Git metadata identifies the source base, while `code_sha256` identifies actual
source. Do not alter historical reports or hashes to bypass compatibility.

Run from the repository root with the documented compatible runtime:

```powershell
Expand-Archive docs/verification/phase9b-2026-10-11/accepted-replay-source.zip .verification/phase9b-source
./backend/.venv/Scripts/python.exe .verification/phase9b-source/scripts/replay_comparison.py docs/verification/phase9b-2026-10-11/complete-report.json
./backend/.venv/Scripts/python.exe .verification/phase9b-source/scripts/replay_comparison.py docs/verification/phase9b-2026-10-11/missing-report.json
./backend/.venv/Scripts/python.exe .verification/phase9b-source/scripts/replay_comparison.py docs/verification/phase9b-2026-10-11/corrected-report.json
```

The archive is a bounded calculation-evidence bundle, not an application,
dependency distribution or deployment package. Replay verifies internal
consistency, not independently certified market evidence or broker reconciliation.
New log copies have trailing EOF whitespace normalized; check output is retained.
Paths/timings describe this local Windows environment. No hosted CI or production
claim follows from these artifacts.
