---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST01
status: in_progress
implementation_authorized: true
human_readable: false
---

# Stage 01: Traceable Execution

Purpose: deliver the first complete deterministic model-tool path with durable facts, request idempotency, exact approval, typed result semantics, and independent side-effect observation.

Scope: PH1-T01..T06. Build the domain contract, SQLite persistence, deterministic model simulator, simulated tool and observer, application orchestration, timeline, and one thin developer entry.

Conservative boundary: recovery, cancellation, manual resolution, and budget controls are explicitly unsupported. Unknown results pause; they are never converted into success or automatically retried.

Exit: AC-01, AC-02, AC-03, and AC-14 pass; persist-before-dispatch and approval guards are demonstrated; exactly one logical product is independently observed. Stage 02 remains blocked otherwise.
