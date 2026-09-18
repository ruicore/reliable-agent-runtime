---
audience: codex
document_role: stage_plan
phase_id: PH1
stage_id: PH1-ST02
status: in_progress
implementation_authorized: true
human_readable: false
---

# Stage 02: Recoverable Execution

Purpose: make uncertain and interrupted execution recoverable only when durable facts and verified adapter guarantees justify a decision.

Scope: PH1-RC01..RC06. Add query/deduplication guarantee declarations, reconciliation, real process kill/restart tests, finite retry accounting, human handling that preserves unknown facts, recovery-material/version refusal, and recovery evidence.

Safety boundary: temporary not-found, a client idempotency key, or a human click is not completion proof. Non-queryable unknown results do not retry automatically. Stage 02 lays the persistent count foundation for AC-12 but does not claim complete budget acceptance.

## R2 recovery contract increment

The first Stage 02 increment freezes the following database-neutral contracts:

- `AdapterGuarantees` declares whether the tool is queryable, whether server-side deduplication is verified, the deduplication scope, and the guarantee version. A client idempotency key alone is not a verified guarantee.
- `RecoveryDecision` is one of `no_action`, `query`, `retry`, or `human_attention`. An unknown result is never converted to completion by the decision function.
- Query is eligible only when the adapter declares queryability. Retry is eligible only when the adapter declares a verified retry-safe guarantee and durable attempt accounting shows remaining allowance. Otherwise the decision is `human_attention`.
- Attempt rows and events remain the durable source of consumed-attempt facts. A new Runtime instance must derive the same attempt count from SQLite rather than reset it in memory.
- Recovery material carries its contract version and input digest. Missing or incompatible material returns an explicit refusal and never substitutes current input or defaults.

This increment does not yet implement the process-kill harness, tool query reconciliation, human decision mutation, or the full AC-04..08/17 evidence matrix. Those remain Stage 02 work.

Exit: AC-04, AC-05, AC-06, AC-07, AC-08, and AC-17 pass and Stage 01 regresses cleanly. Stage 03 remains blocked otherwise.
