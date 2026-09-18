---
audience: codex
document_role: phase_manifest
phase_id: PH1
authority: normative
status: implementation
active_stage: PH1-ST01
implementation_authorized: true
human_readable: false
---

# Phase 1: Reliable Agent Runtime

Phase ID: `PH1`

Status: Stage 00 R1 contract accepted; bounded Stage 01 implementation is in progress.

## Product outcome

A developer can run a deterministic tool-using workflow and obtain durable, evidence-backed answers about execution, duplication, uncertainty, recovery, approval, cancellation, budgets, compatibility, and reproducibility.

Phase 1 is the complete current product baseline. Stage 01 is the first executable vertical slice, not the whole phase. Recovery, cancellation, budgets, and reproducible evidence MUST NOT be deferred into an undefined future product phase.

The private catalog owns product scope, capability provenance, acceptance ownership,
and portfolio status. This public phase owns the implementation contract, detailed
tasks, and evidence requirements. It is intentionally not a mirror of the private
phase documents.

## Documents

- [Requirements](requirements.md)
- [Acceptance contract](acceptance.md)
- [Phase plan](phase-plan.md)

## Internal stages

| Stage | Name | Status | Primary exit |
| --- | --- | --- | --- |
| 00 | [Contract Design](stages/00-contract-design.md) | Active | Complete requirements, interfaces, states, persistence, errors, data rules, and AC-01..18 mappings are approved. |
| 01 | [Traceable Execution](stages/01-traceable-execution.md) | Blocked by Stage 00 | AC-01, AC-02, AC-03, and AC-14 pass. |
| 02 | [Recoverable Execution](stages/02-recoverable-execution.md) | Blocked by Stage 01 | AC-04..08 and AC-17 pass; Stage 01 regresses cleanly. |
| 03 | [Controlled Execution](stages/03-controlled-execution.md) | Blocked by Stage 02 | AC-09..13 pass; Stages 01-02 regress cleanly. |
| 04 | [Reproducible Delivery](stages/04-reproducible-delivery.md) | Blocked by Stage 03 | AC-15, AC-16, AC-18 and full AC-01..18 regression pass. |

## Phase entry

- The public problem, independent scenario, full Phase 1 boundary, and non-goals are recorded.
- All examples use public or generated data and local simulators.
- The bounded AC-01/AC-02/AC-03/AC-14 slice is implemented and tested locally; full acceptance remains `not_run` until independent evidence is collected.

## Phase exit

- PH1-R01 through PH1-R08 are implemented without widening the non-goals.
- AC-01 through AC-18 pass with Runtime evidence and required independent tool-side facts.
- Interfaces, persisted facts, reports, documentation, and observed behavior agree.
- Declared Python versions and clean installation/reproduction environments pass.
- Privacy, provenance, dependency, history, and package-content gates pass.
- Simulation and unsupported-service limitations remain explicit.

Phase completion does not authorize commit, public push, release, or publication.
