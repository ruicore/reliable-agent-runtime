---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST03
status: complete
implementation_authorized: true
human_readable: false
---

# Stage 03: Controlled Execution

Purpose: compose recovery with cancellation, stopping confirmation, approval invalidation, and persistent execution bounds.

Scope: PH1-CT01..CT05. Add cancel/dispatch interlocks, adapter stop confirmation, late-result behavior, approval revalidation, retry/time budgets, and the interleaving regression matrix.

Safety boundary: cancellation acceptance is not stopping confirmation or rollback. Exhausted budgets block new attempts but do not erase in-flight facts. Late success is visible but does not restart a cancelled flow.

## R3 control contract entry

Stage 03 freezes the following database-neutral control dimensions before implementation:

- Cancellation is orthogonal to action result: request, acceptance, stopping confirmation, and late-result facts are distinct. Cancellation never claims rollback.
- Dispatch interlocks record whether cancellation was accepted before dispatch, during an in-flight call, or after dispatch. No downstream action starts after accepted cancellation.
- Approval is revalidated against the immutable action identity, target, input digest, action digest, and relevant recovery material. Any mutation or incompatible recovery input invalidates the prior approval.
- `RetryBudget` and `ExecutionTimeBudget` are durable facts. Exhaustion blocks new attempts, survives restart, and does not rewrite confirmed or unknown in-flight results. Human-wait time remains a separate clock.
- A late success after cancellation remains visible but cannot restart the cancelled flow or schedule downstream work.

The implementation covers the cancellation state machine, dispatch interlocks, late-result recording, approval invalidation, persistent retry-count and execution-time budgets, human-wait accounting, additive SQLite migration, and the AC-09..13 control matrix while preserving the Stage 01-02 regression boundary.

Exit: AC-09, AC-10, AC-11, AC-12, and AC-13 control tests pass locally and Stages 01-02 regress cleanly. Stage 04 reproducible delivery is now complete locally.
