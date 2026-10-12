# Phase 9D — portfolio benchmark settings and factor-data readiness

The owner's continuation after accepted Phase 9C authorizes this bounded stage.
Preserve the master, all existing audits/evidence and the suggestions byte prefix.

1. Add append-only portfolio benchmark identity settings with independent revision,
   server recording time, reason, idempotency ID and optimistic concurrency.
   Clearing a choice appends a null identity; no levels or factors are persisted.
2. Reuse the portfolio row lock. Validate same currency, reviewed identity and
   nonfuture provenance. Expose private latest/paginated history/append endpoints.
   Add PostgreSQL migration with update/delete rejection, retaining old migrations.
3. Report requests explicitly opt into a saved revision. Under the same lock,
   reject changed/cleared settings, identity mismatch and knowledge-cutoff leakage.
   Retain a hashed selection receipt in comparison and nested factor exports;
   verify it offline without consulting a later database default.
4. Add settings review/save/clear/history and explicit use of saved identity to
   Performance. Retain no invented levels, automatic comparison or hidden benchmark.
   Clear private state on lock/account/refresh and suppress late responses.
5. Specify real factor currency/calendar readiness and required source/provenance
   transformations; this stage does not convert USD trading-day factors into GBP
   calendar data, ingest providers or add HAC/rolling/Brinson/publication.
6. Verify contracts, API rollback/idempotency/clear/stale selection, receipt tampering,
   PostgreSQL immutability/concurrent writers/report read-only behavior, client state
   and browser settings lifecycle. Run full acceptance gates, retain fresh evidence,
   append suggestions, write PHASE_9D_AUDIT.md and create a local checkpoint.
