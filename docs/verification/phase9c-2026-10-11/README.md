# Phase 9C local acceptance evidence — 2026-10-11

See the [new Phase 9C audit](../../PHASE_9C_AUDIT.md) and
[factor contract/methodology](../../FACTORS.md). These are fresh local results;
earlier audits and evidence retain their original findings.

- `checks.json` and the ten corresponding logs retain the complete corrected
  PostgreSQL-enabled verification run: 679 backend tests, zero skipped, 97.87%
  combined coverage; quality/hooks, benchmark, 141 frontend cases, lint and build.
- `final-frontend.txt`, `final-lint.txt`, `final-build.txt` retain the successful
  client rerun after the four-decimal factor R² presentation change.
- `staged-hooks.txt` records the final staged quality checks.
- `browser-acceptance.txt` describes populated, missing-row, append-only correction,
  responsive and privacy checks. Five JPG captures retain inspected browser views;
  the corrected desktop capture uses the final R² formatter. The earlier desktop
  capture preserves its earlier two-decimal presentation.
- `browser-evidence.json`, `browser-factors.json`, `browser-benchmark.json` are
  explicitly synthetic, reviewed manual inputs, not provider market data.
- `complete-report.json` and `missing-report.json` are actual private API exports
  from synthetic ledger version 3. `corrected-report.json` is version 4 after the
  fee reversal. Each embeds its exact inputs, ledger snapshot, source identity,
  portfolio/contribution/comparison and factor result. The missing browser check
  used version 4; the retained missing API export used version 3.
- The three `*-replay.txt` logs verify these reports against working source;
  `archived-*-replay.txt` verifies them against separately extracted archived source.
- `accepted-replay-source.zip` retains 86 exact backend Python/entry-point files;
  `accepted-source.json` records SHA-256 identities and Python 3.12.14. This is
  replay source, not a dependency bundle, hosted build or deployment artifact.
- `preservation.json` proves all 108 task-entry historical checks, including the
  original suggestions byte prefix. `cleanup.txt` records scoped schema removal
  and stopped acceptance services.

Reproduce an exported report with compatible dependencies/runtime:

```powershell
./backend/.venv/Scripts/python.exe scripts/replay_factors.py docs/verification/phase9c-2026-10-11/corrected-report.json
```

For archive replay, extract into a separate directory and run its
`scripts/replay_factors.py` with the same compatible interpreter and report path.
Archive bytes and numerical replay were checked locally; cross-platform bitwise
reproducibility is not attested. Source/dependency fingerprints are verified,
not rewritten to force compatibility.

The browser export button was activated, but the resulting saved file was not
independently obtained. Retained and replayed files are actual API exports;
actual browser file delivery remains unverified. Synthetic regression coefficients
and t-statistics are constructed test observations, not evidence of investment skill.
