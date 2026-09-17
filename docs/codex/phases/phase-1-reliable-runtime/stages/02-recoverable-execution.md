---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST02
status: blocked
blocked_by: PH1-G01
implementation_authorized: false
human_readable: false
---

# Stage 02: Recoverable Execution

Purpose: make uncertain and interrupted execution recoverable only when durable facts and verified adapter guarantees justify a decision.

Scope: PH1-RC01..RC06. Add query/deduplication guarantee declarations, reconciliation, real process kill/restart tests, finite retry accounting, human handling that preserves unknown facts, recovery-material/version refusal, and recovery evidence.

Safety boundary: temporary not-found, a client idempotency key, or a human click is not completion proof. Non-queryable unknown results do not retry automatically. Stage 02 lays the persistent count foundation for AC-12 but does not claim complete budget acceptance.

Exit: AC-04, AC-05, AC-06, AC-07, AC-08, and AC-17 pass and Stage 01 regresses cleanly. Stage 03 remains blocked otherwise.
