# L4 controlled publication acceptance — 2026-10-14

Accepted locally: L4.1–L4.2. This is a local publication lifecycle rehearsal, not
an externally deployed release. L1–L3 acceptance and all older evidence remain intact.

Additive migration 07 creates an immutable channel, captured owner previews and
append-only lifecycle events. Authenticated commands generate the strict allowlist
on the server; callers cannot submit arbitrary public financial content. The channel
row serializes competing publication intents; portfolio/source locks fence coherent
reads. A publish reprojects and checks the captured source/content and event sequence.
Stale source, changed calculation code, changed history and a different demo identity
are rejected. Exact intent retries never append duplicate events.

Published content is frozen independently of subsequent private source changes.
Each correction requires a new reviewed preview, the previous public version and
an explicit public reason. Withdrawal hides latest and prior version content and
downloads with HTTP 410/no-store; public dates/reasons and private records remain.
Republishing uses a new version and does not expose earlier withdrawn content.
Previously downloaded copies cannot be recalled. Hashes are consistency evidence,
not external timestamping, personal performance verification or broker proof.

Owner controls deliberately select original research, preview, publish, disclose
corrections and withdraw. Keys stay in closures/header transport; lock, unmount,
refresh, uncertain retries and late responses are guarded. `PUBLIC_RELEASE_MODE=1`
requires existing owner authentication for legacy simulation endpoints, preserving
default legacy API compatibility. Public readers have separate transports without
owner headers, and cannot enumerate captured previews or access private portfolios.

Final full gate: **783 backend tests, 174 frontend tests, zero skips, 97.62% coverage**;
all ten checks exit zero. Actual PostgreSQL verifies immutable rows, serialized
competing publishes, source-write locks, edited source rejection and unchanged
published content. Analytical L1–L3/earlier financial checks remain in the gate.
Working and extracted compatible-source replays pass for all three fresh reports.

Actual browser: owner preview with Harbor only still includes the complete Orchard
loss; first publish, refreshed history, disclosed correction adding the Orchard
review, anonymous public history, keyboard links, desktop/mobile and withdrawal
were exercised. A fresh version restored availability after the rehearsal; lock
immediately removed owner controls. Measured 1280×900 / 390×844 (document 1265/375).
Actual version JSON download was delivered and matched typed content, source and
hashes; NAV £10,516, closed local loss −US$400, full negative TWR and both reviews.
Earlier withdrawn pages/downloads remain 410. Anonymous private/API calculation
requests return 401; fixed local preview is disabled in this release-mode rehearsal.

Final local public version: `079ef599-a949-4d8f-aab3-be5fc5f90c3a`.
Content SHA-256: `8334425874be0865dfcf369cd64862f479063aa0261abcaca8ccadc91ad95d44`.
Calculation source SHA-256: `595d3bf5ccc73ef61609159edeb700de71c5c5e9bf4632a0beefab84d11c9871`.
These identify the retained local rehearsal, not the future hosted release.

Observed defects/repairs: an intermediate edit read UTF-8 through Windows' default
encoding, corrupting punctuation in the public component/current plan. Repaired
the affected sequences, used explicit UTF-8 thereafter, and verified final browser
text and gate. The identity banner previously said nothing was published; it now
states publication is managed separately. Initial download tooling was very slow;
the actual file eventually arrived and was inspected. A verification script initially
expected no-store on generic unauthenticated legacy errors; corrected that assertion
to the implemented public/publication policy. Those generic errors contain no account
data; L5 may harden all release API cache behavior.

Static public metadata is generated for `/demo/` and `/demo-preview/`; actual
`/demo/` HTML/browser metadata is synthetic. Vite fallback `/demo`/deep versions
still need the production routing rule. Existing large-bundle/Starlette warnings
remain; local Python 3.12.14/PostgreSQL 17.11 differ from the full CI matrix.
Hosted CI, recovery, resource/cost limits, staging and deployment are unfinished.

[Evidence](verification/launch-l4-2026-10-14/README.md) retains gate, browser, actual
download, boundary checks and source/report archives. **352 prior records** unchanged
(designated evolving documents retain byte prefixes). Master brief and prior audits
remain unchanged. Next: L5.1. Owner subsequently identified Fly.io and Neon with a
total US$5/month ceiling, free preferred; account access and costs must be verified.
