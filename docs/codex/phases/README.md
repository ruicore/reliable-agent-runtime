---
audience: codex
document_role: phase_registry
scope: product
authority: normative
status: active
human_readable: false
---

# Product Phases

A product phase is a complete capability-derived product baseline. Internal stages are implementation and validation increments inside that baseline; they MUST NOT be treated as separate product scopes.

Do not pre-create future phases. Create a new phase only after capability assessment identifies a product-owned user problem and an accepted requirement/acceptance increment. Unfinished Phase 1 requirements, maintenance, defects, and compatibility corrections remain Phase 1 work.

## Phase registry

| Phase | Product outcome | Status | Plan |
| --- | --- | --- | --- |
| Phase 1 | Durable, recoverable, controlled, and independently reproducible Agent tool execution | Validated locally / Maintenance | [Phase 1: Reliable Agent Runtime](phase-1-reliable-runtime/README.md) |

## Required phase structure

- `README.md`: identity, lifecycle, internal-stage index, entry and exit gates.
- `requirements.md`: complete phase requirements, invariants, and non-goals.
- `acceptance.md`: independent evidence and pass/fail contract.
- `phase-plan.md`: dependency graph, tasks, checkpoints, and delivery gates.
- `stages/`: bounded internal increments that implement the same phase baseline.

## Lifecycle

`proposed -> contract_design -> approved -> implementation -> validated -> maintained`

Only explicit review can move a lifecycle gate. Contract approval authorizes implementation only; commit, push, release, and publication remain separate decisions.
