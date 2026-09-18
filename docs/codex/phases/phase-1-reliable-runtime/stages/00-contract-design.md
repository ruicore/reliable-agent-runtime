---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST00
status: active
implementation_authorized: false
human_readable: false
---

# Stage 00: Contract Design

Purpose: freeze the complete Phase 1 behavior before source or test implementation. This Stage owns PH1-C00..C09 and gate PH1-G00 in `../phase-plan.md`.

Required output:

- PH1-R01..R08 and AC-01..18 remain mutually traceable.
- Identities, immutable digests, orthogonal states/transitions, typed errors, adapter guarantees, persistence ordering, recovery, cancellation, approval, budgets, data rules, reports, and fault injection are explicit.
- Persistence is fixed to SQLite through SQLAlchemy for Phase 1. Domain rules,
  Repository ports, and the transaction boundary remain database agnostic; the
  SQLite/SQLAlchemy adapter owns engine, session, locking, migration, and
  SQLite-specific behavior.
- Phase 1 does not design a Postgres adapter or a dual-backend runtime. A future
  Postgres adapter requires a separate capability/problem decision and migration,
  compatibility, and concurrency acceptance.
- Every Stage-later operation has a conservative unsupported behavior until implemented.
- Public content has no private provenance or environment dependency.

Exit: integrated contract review resolves every blocker and the user explicitly authorizes Stage 01 implementation. Until then, no source or test changes are allowed.
