# Public demonstration presentation

Only the original isolated synthetic demo is eligible. `PublicSnapshot` is a
strict typed allowlist: it contains stable fictional public keys, dates, financial
outputs, selected original research and explicit conventions/disclosures. Private
portfolio/security/transaction IDs, account fields, raw reports, notes and secrets
are excluded. Selecting research never removes a loss from measured performance.

`scripts/prepare_demo_preview.py` requires an already loaded, unchanged demo and a
fresh output path. The optional `ENABLE_DEMO_PREVIEW=1` route reads only the fixed
`backend/demo/public_preview_v1.json`, validates its hash and returns no-store
responses. It does not publish or query an anonymous caller's account. Default
preview access is disabled. `/demo-preview` is explicitly labelled unpublished.

Backend domain engines produce return series and calendar aggregates. Backend
projection computes growth/drawdown with visible gap/zero semantics; the frontend
formats and draws those supplied values. Unsupported prospective risk contribution
is unavailable, with a reason. The complete closed history includes the synthetic
loser. Both thesis dates and actual creation timestamps are visible.

The public JSON is presentation data, not a private report replay file. The private
compatible source/input/report bundle is retained separately in acceptance evidence.
Hashes prove internal consistency, not authenticity or external attestation. The
frozen local preview remains reproducible with its retained source even when later
implementation changes. See [L3 acceptance](LAUNCH_L3_AUDIT.md).
