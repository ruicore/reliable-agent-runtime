---
audience: codex
document_role: phase_execution_plan
phase_id: PH1
authority: operational
status: active
active_stage: PH1-ST01
implementation_authorized: true
human_readable: false
---

# Phase 1 Delivery Plan

Status: active. Stage 00 R1 contract is accepted for the bounded deterministic model-tool slice. This document does not authorize commit, push, release, or publication.

The private product catalog remains the source for product scope, capability
ownership, portfolio status, and phase-level decisions. This public plan owns the
detailed implementation work breakdown, contract decisions, test evidence, and
execution gates. When a requirement or acceptance rule changes, the catalog is
updated first and this plan is synchronized afterward.

## Dependency chain

`ST00 contract -> ST01 traceable -> ST02 recoverable -> ST03 controlled -> ST04 reproducible -> Phase 1 exit`

Every later Stage depends on the prior Stage exit and full regression of earlier behavior. A Stage may prepare test specifications for later behavior but MUST NOT claim or silently implement a broader control contract.

## Stage 00: Contract Design

| ID | Deliverable | Exit evidence |
| --- | --- | --- |
| PH1-C00 | Scope, glossary, orthogonal invariants, non-goals | Every behavior is owned by PH1-R01..08 or rejected. |
| PH1-C01 | Data classification, retention, recovery-data and diagnostic-data rules | Every field has storage, disclosure, redaction, and lifecycle treatment. |
| PH1-C02 | Request/content/action/attempt/approval identities and digest versions | Duplicate, conflict, immutability, and approval invalidation are unambiguous. |
| PH1-C03 | State dimensions, allowed transitions, forbidden inferences, late-result rules | Unknown, cancel, stop, budget, approval, and external result remain orthogonal. |
| PH1-C04 | Typed application interfaces and one developer entry surface | Submit/query/approve/reject/execute/cancel/manual/report operations have explicit availability and errors. |
| PH1-C05 | Model/tool port contracts and capability declarations | Receipt, validity, business decision, completion, query, dedup, cancel, and retry guarantees are distinct. |
| PH1-C06 | SQLite/SQLAlchemy persistence model, uniqueness, database-neutral Repository and unit-of-work ports, transaction ordering, event ordering, restart boundary | Required facts are durable before dispatch; SQLAlchemy/SQLite stays in infrastructure; independent observation stays separate. |
| PH1-C07 | Retry/time budget and recovery-decision contracts | Eligibility, clocks, consumption, exhaustion, restart, and human wait are explicit. |
| PH1-C08 | Error, compatibility, and version-rejection contract | No error implies retry; incompatible recovery is explicit and data-safe. |
| PH1-C09 | AC-01..18 scenarios, process fault harness, observer, and report schema | Every requirement has independent pass/fail evidence and default `not_run`. |
| PH1-G00 | Integrated contract review and user decision | Contradictions/privacy gaps resolved; user explicitly authorizes Stage 01 implementation. |

## Stage 01: Traceable Execution

| ID | Deliverable | Primary acceptance |
| --- | --- | --- |
| PH1-T01 | Immutable domain types, typed errors, and version values | Contract/invariant tests |
| PH1-T02 | SQLAlchemy-backed SQLite run/action/attempt/approval/event persistence and uniqueness behind database-neutral ports | AC-02, AC-03 |
| PH1-T03 | Deterministic model simulator and validation | AC-01, AC-14 |
| PH1-T04 | Simulated tool, isolated side-effect store, and test observer | AC-01, AC-14 |
| PH1-T05 | Submit/query/approve/reject/execute orchestration with persist-before-dispatch | AC-01, approval safety |
| PH1-T06 | Baseline timeline, minimization, thin developer entry, and explicit unsupported controls | AC-01, AC-14, redaction guard |

Exit: AC-01, AC-02, AC-03, and AC-14 pass; no unapproved dispatch, acknowledgement-as-success, or automatic retry of unknown results occurs.

## Stage 02: Recoverable Execution

| ID | Deliverable | Primary acceptance |
| --- | --- | --- |
| PH1-RC01 | Adapter guarantee registry and reconciliation decisions | AC-04, AC-05, AC-07 |
| PH1-RC02 | Durable recovery scan and real process kill/restart harness | AC-06 |
| PH1-RC03 | Safe retry eligibility with finite persistent attempt accounting | AC-04, AC-06; AC-12 foundation |
| PH1-RC04 | Unknown-attention queue and evidence-bound human handling | AC-05, AC-08 |
| PH1-RC05 | Recovery-input retention/reference and compatibility refusal | AC-17 |
| PH1-RC06 | Recovery evidence and Stage 01 regression | AC-01..08, AC-14, AC-17 applicable set |

Exit: AC-04, AC-05, AC-06, AC-07, AC-08, and AC-17 pass. AC-12 remains incomplete until Stage 03 validates the full budget contract.

## Stage 03: Controlled Execution

| ID | Deliverable | Primary acceptance |
| --- | --- | --- |
| PH1-CT01 | Cancel request/acceptance and dispatch interlock | AC-09, AC-10 |
| PH1-CT02 | Adapter stopping confirmation and late-result handling | AC-09, AC-10 |
| PH1-CT03 | Approval revalidation across mutation and restart | AC-11 |
| PH1-CT04 | Persistent retry-count and execution-time budget enforcement | AC-12, AC-13 |
| PH1-CT05 | Cancellation/recovery/approval/budget interleaving matrix and regression | AC-01..14, AC-17 applicable set |

Exit: AC-09, AC-10, AC-11, AC-12, and AC-13 pass; Stages 01-02 regress cleanly.

## Stage 04: Reproducible Delivery

| ID | Deliverable | Primary acceptance |
| --- | --- | --- |
| PH1-D01 | Versioned machine report and concise human explanation | AC-16 |
| PH1-D02 | Synthetic-canary redaction and recoverability matrix | AC-15 |
| PH1-D03 | Repeatable full fault matrix with independent observations | AC-16 and AC-01..18 regression |
| PH1-D04 | English install/use/fault/interpretation guide | AC-18 |
| PH1-D05 | Clean Python 3.13/3.14 installation and package verification | AC-18 |
| PH1-D06 | Dependency, provenance, diff, history, package-content, privacy, and claims audit | Public-candidate gate |

Exit: AC-15, AC-16, AC-18, and full AC-01..18 regression pass. Release candidate readiness still does not authorize push or release.

## Review gates

| Gate | Decision |
| --- | --- |
| PH1-G00 | Complete contract is coherent, public-safe, and explicitly approved before implementation beyond the bounded Stage 01 slice. |
| PH1-G01 | Traceable vertical slice is real and independently observed before recovery work. |
| PH1-G02 | Restart/recovery semantics pass before cancellation and full budget composition. |
| PH1-G03 | Complete execution-control semantics pass before final delivery work. |
| PH1-G04 | Full product evidence, compatibility, privacy, and packaging pass before any publication decision. |

## Parallelization constraints

After PH1-G00, domain/persistence, model adapter, and simulated tool work may branch only from the same approved contract version. Recovery, cancellation, budget, report, and transport code MUST NOT invent independent states or errors. Contract changes return to the owning Stage 00 artifact and trigger affected acceptance review.

## Product evolution rule

`new capability or failure boundary -> product-owned user problem -> requirement delta -> independent acceptance -> Phase increment -> staged implementation`

More evidence may change confidence without adding functionality. Unfinished Phase 1 scope and corrections continue inside Phase 1. A new framework, model, library, or convention without a requirement/acceptance delta does not create a feature.
