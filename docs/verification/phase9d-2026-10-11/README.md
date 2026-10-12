# Phase 9D acceptance evidence

Work began 2026-10-11; closeout dated 2026-10-12. Scope and findings are in
[the new audit](../../PHASE_9D_AUDIT.md). This directory contains synthetic local
acceptance evidence. It does not establish hosted deployment or real-source readiness.

## Gates

The final full verification runner passed through frontend tests. A continuation
interrupted it during lint; remaining lint/build commands then completed with exit
code 0. There is no claim that the interrupted runner produced a complete checks.json.

| Evidence | Result |
| --- | --- |
| backend.txt | 696 passed, zero skipped; 97.89% coverage; actual PostgreSQL included |
| ruff.txt / format.txt / mypy.txt | Passed; 144 formatted files and 138 typed source files |
| hooks.txt | Configured hooks passed in the full runner |
| staged-hooks.txt | Final staged hooks, retained at closeout |
| frontend.txt | 147 passed; zero failed/skipped |
| final-lint.txt / final-build.txt | Explicitly completed remaining gates; build 29.19s |
| benchmark.txt | Local Gaussian 0.2443s / GMM 0.4631s observations |
| dependencies.txt / resolved-python.txt | Dependency/runtime evidence from the runner |

lint.txt is the interrupted runner's partial lint log; final-lint.txt is the
completed command's evidence. Inherited Starlette/Vite warnings remain in logs.

## Workflow and exports

The disposable GBP cash fixture had a 1000 deposit, ledger version 1, and synthetic
benchmark levels 100/102/101. Screenshots linked-report.jpg, cleared-desktop.jpg,
settings-mobile.jpg and cleared-mobile.jpg were visually inspected. Desktop and
390×844 light views covered save, explicit selection, report receipt, clear/history
and private-state reset. Mobile page width was 375; final localhost console capture
contained no errors. Browser input evidence is retained in browser-*.json.

settings-before-clear.json and settings-after-clear.json are actual API histories.
selected-comparison.json and selected-factors.json are actual API exports with
revision-1 receipts. report-only-after-clear.json is an actual API export with no
saved selection. stale-selection.txt records the old selected request's no-store
409 after revision 2 cleared the setting. The factor fixture has 32 cash intervals,
a constant response and incomplete auxiliary benchmark coverage; its null statistics
are intentional. Browser saved-file delivery was not independently verified here.

All three exports passed the matching working-*.txt and archived-*.txt replay
checks. accepted-replay-source.zip contains 87 exact backend Python/entry-point
files. accepted-source.json records its archive hash and backend code identity.
The archive excludes migrations, dependencies, frontend and deployment; use a
compatible Python environment. Old reports retain their own accepted source archives.

preservation.json proves 148 historical full-file/original-suggestions-prefix
checks against entry commit 30db8bc. cleanup.txt records removal of the named
disposable schema and shutdown of acceptance services. Historical records were
preserved; development failures and interruptions are described in the new audit.
