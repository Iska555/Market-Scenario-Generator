# Usability repair evidence — 2026-10-17

See [the dated acceptance](../../USABILITY_REPAIR_2026-10-17.md) for scope and limits.

- `checks.json` and matching text files: all ten local checks, 790 backend and
  178 frontend tests; final frontend rerun after presentation changes.
- `hosted-checks.json`: live Fly timings, transport, CORS, owner-only simulation,
  typed results and unchanged public history. Timings exclude cold readiness
  except the separately recorded first health request.
- `hosted-concurrency.json`: simultaneous owner requests return 200 / bounded 503.
- `runtime-final.json`: final deployed backend hashes and package/runtime identity.
  Its process memory snapshot is after the final frontend-only redeployment;
  `runtime-workload.json` records the peak workload on the preceding image with
  exactly the same 95 backend files and runtime.
- `retained-backup-restore.json`: fresh local recovery of the retained synthetic
  production dump; no new cloud backup or production restore is claimed.
- `vercel-http.json`, `hosted-ci.json`: production proxy/history and hosted CI.
- `overview-desktop.png`: actual final Fly overview, with larger product identity.
- `simulation-desktop.png`: actual final Fly joint-GMM output for illustrative
  40/40/20 weights; these are not actual account holdings or forecasts.
- `simulation-mobile.png`: final live mobile form; result presence/overflow was
  also checked in the DOM. `workspace-mobile-dark.png`: actual dark theme.
- `vercel-simulation.png`: actual successful result at the originally reported URL.
- `source.zip`, `source-manifest.json`: explicit 206-file source/build/helper archive,
  per-file hashes, image and release code identity; no private inputs or credentials.

All previous audit/replay archives and the master brief remain unchanged. Private
key recovery files, protected credentials, dumps and raw hosted records stay in
ignored `.verification/` and are not part of this directory or the public download.
