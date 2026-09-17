---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST03
status: blocked
blocked_by: PH1-G02
implementation_authorized: false
human_readable: false
---

# Stage 03: Controlled Execution

Purpose: compose recovery with cancellation, stopping confirmation, approval invalidation, and persistent execution bounds.

Scope: PH1-CT01..CT05. Add cancel/dispatch interlocks, adapter stop confirmation, late-result behavior, approval revalidation, retry/time budgets, and the interleaving regression matrix.

Safety boundary: cancellation acceptance is not stopping confirmation or rollback. Exhausted budgets block new attempts but do not erase in-flight facts. Late success is visible but does not restart a cancelled flow.

Exit: AC-09, AC-10, AC-11, AC-12, and AC-13 pass and Stages 01-02 regress cleanly. Stage 04 remains blocked otherwise.
