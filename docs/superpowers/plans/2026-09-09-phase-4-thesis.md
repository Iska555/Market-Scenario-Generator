# Phase 4 thesis system implementation plan

Spec: `docs/MASTER_BRIEF.md`, Phase 4. Owner authorization: 2026-09-09,
"Commit and continue with Phase 4". Phases 1–3 committed as `88f4390` after
238 PostgreSQL-inclusive backend tests and full frontend/static checks.

## Design and boundaries

One stable thesis identity refers to a research security UUID. Every edit appends
a complete immutable revision with a sequential number, server timestamp, and
captured ticker/exchange label. A required `expected_revision` prevents stale
forms from silently overwriting another revision. PostgreSQL locks the thesis
identity while allocating revisions and uniqueness is a second line of defense.

Version content: status (`draft`, `active`, `invalidated`, `closed`), positive
`horizon_months`, conviction (`low`, `medium`, `high`), `valuation_currency`,
nullable Decimal `target_low`/`target_high` (paired, ordered, positive), nullable
annual effective `required_return` (fraction > −1), and narrative fields
`variant_perception`, `business_quality`, `earnings_drivers`, `catalysts`, `risks`,
`bear_case`, `base_case`, `bull_case`, `invalidation_conditions`, `notes`.
Drafts may contain empty narratives. Active theses require the substantive
non-note sections. All statuses and judgments are manually selected.

Reviews append to a specific immutable `revision_id` belonging to the thesis.
Fields: server `reviewed_at`, explicit decision (`BUY_MORE`, `HOLD`, `REDUCE`,
`EXIT`, `WATCH`), nullable positive `current_price`, `valuation_currency`,
`what_changed`, `what_was_correct`, `what_was_wrong`, `new_information`,
`thesis_still_valid` boolean, nullable annual effective `updated_expected_return`
(owner-declared fraction > −1), and `notes`. Review action never changes the
thesis status or initiates a trade. No model computes an expected return.

Reuse the private research API key and transaction/session dependencies. New
schema migration descends from `20260908_01`; old revisions, reviews and thesis
identities cannot be updated/deleted through PostgreSQL or application routes.
GET histories expose server-recorded ordering, with an optional `as_of` cutoff
for latest thesis reads. No user-backdated authoring timestamps.

A focused frontend Thesis tab supports connection by an in-memory owner key,
security selection, creation/editing, immutable history inspection and review
entry. Saved revisions remain distinct from unsaved edits. Disconnect clears
private data/key; secrets are never placed in localStorage or URLs. Forms show
valuation currency and decimal annual-return units. Display the five behavioral
prompts from the backend. Decisions have no automatic recommendation/default.
The existing Risk Lab UI and statistics remain intact.

## Stable API contract for parallel implementation

Prefix `/api/research`, all protected with existing `X-Research-Key`:

- `GET /theses/prompts`: list of five prompt strings.
- `POST /theses`: content fields plus `security_id`; returns ThesisRead.
- `GET /theses?security_id=...&limit=100&offset=0`: list[ThesisRead].
- `GET /theses/{id}?as_of=...`: ThesisRead with newest eligible revision.
- `POST /theses/{id}/revisions`: content + `expected_revision`; returns RevisionRead.
- `GET /theses/{id}/revisions?limit=100&offset=0`: newest-first list[RevisionRead].
- `POST /theses/{id}/reviews`: review fields + `revision_id`; returns ReviewRead.
- `GET /theses/{id}/reviews?limit=100&offset=0`: newest-first list[ReviewRead].

ThesisRead: `id`, `security_id`, `created_at`, `latest` (RevisionRead).
RevisionRead: all content + `id`, `thesis_id`, `security_id`, `revision`,
`created_at`, `ticker`, `exchange`. ReviewRead: input fields + `id`, `thesis_id`,
`reviewed_at`. UUIDs and ISO timestamps are strings in JSON; Decimals are strings
or null. All list limits1–100; offset>=0. Missing404, conflict409, invalid422,
unconfigured/database503, unauthorized401. Security list reuses Phase3 endpoint.

## Tasks

- [x] Backend: typed thesis package, immutable ORM records, transaction-aware
  repository, private thin routes, migration and focused tests (delegated).
- [x] Frontend: focused thesis workspace, form/contract tests and app navigation;
  preserve state and prevent stale response/unsaved edit confusion (delegated).
- [x] Integration: PostgreSQL migration agreement/immutability and concurrent
  revision tests, actual browser flow, full inherited regression/static checks.
- [x] Documentation: design/implementation audit, schema/API/methodology updates,
  baseline commit reference, verified evidence and remaining limitations.
- [x] Independent review, resolve concrete findings, stop before Phase 5.

Decisions: use server authoring timestamps and immutable versions rather than
backdated journaling; API keys stay in memory; no automatic valuation or trading.
These are reversible implementation choices within the approved Phase4 scope.
No publish, merge or deployment. Leave Phase4 changes reviewable separately from
the requested initial foundation commit.
