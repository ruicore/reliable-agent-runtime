---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST00
status: accepted
implementation_authorized: true
human_readable: false
---

# Stage 00: Contract Design

Purpose: freeze the complete Phase 1 behavior and keep each implementation increment
inside an explicit contract. This Stage owns PH1-C00..C09 and gate PH1-G00 in
`../phase-plan.md`.

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

## R1 interface freeze

The first executable slice exposes the following typed application operations:

- `submit(request_id, text) -> RunView`: canonicalizes input, invokes the deterministic model, and persists a run plus immutable action intent when the model output is valid.
- `query(run_id) -> RunView`: returns durable run, action, attempt, and append-only event facts.
- `approve(action_id)`: records exact approval for the immutable action.
- `execute(run_id) -> RunView`: requires approval, persists attempt/dispatch facts before tool invocation, and records the tool result.
- `report(run_id) -> machine-readable mapping`: returns minimized identifiers, state, timeline kinds, and explicit unsupported controls.

The R1 state dimensions are orthogonal: run control (`pending_approval`, `ready`,
`completed`, `model_invalid`, `terminated`), approval (`pending`, `approved`, `rejected`),
dispatch (`not_dispatched`, `intent_persisted`, `dispatched`), and action result
(`not_started`, `succeeded`, `rejected`, `unknown`). A model-invalid submission has
no executable action. Dispatch is never inferred from a result, and the external
side effect is observed only by a separate test observer.

## SQLite/SQLAlchemy persistence freeze

The `SQLiteRepository` is the only Phase 1 persistence adapter. Its schema stores
runs, one immutable action per run, attempts, and append-only events. The adapter
enables SQLite foreign keys and owns SQLAlchemy sessions/engine details. Domain
types and ports contain no SQLAlchemy or SQLite imports. Submission and dispatch
intent are committed before the tool call; result facts are committed afterward.

## First vertical-slice acceptance mapping

The implementation is intentionally bounded to AC-01, AC-02, AC-03, and AC-14 baseline
observations: deterministic valid model output; invalid model output produces no
action; duplicate request identity reuses one run/action; conflicting content is
rejected; approval, persist-before-dispatch, one simulated side effect, independent
observation, and a minimized report are covered. Recovery, retries, cancellation,
budgets, real providers, and restart harnesses remain explicitly unsupported.

Exit: the R1 contract is accepted for the bounded Stage 01 slice. Full Stage 00
acceptance still requires the later contract artifacts (recovery, cancellation,
budgets, compatibility, reports, and fault matrix) to remain explicit before their
implementation begins.
