---
audience: codex
document_role: phase_requirements
phase_id: PH1
authority: normative
status: proposed
implementation_authorized: false
human_readable: false
---

# Phase 1 Requirements

Every behavior MUST map to an acceptance case before implementation is complete. Unlisted behavior MUST NOT be inferred as in scope. All requirements below belong to Phase 1; Stage assignment controls delivery order, not product ownership.

## PH1-R01 Durable execution facts

- Persist run, action, attempt, approval, rule, input/content identity, contract version, decision, timestamp, and append-only event facts.
- Persist the action intent and sufficient recovery facts before external dispatch.
- Distinguish one logical action from its attempts.
- Resolve identical request identity and canonical content to one logical run, including concurrent submission.
- Reject the same request identity with different canonical content without mutating the original run.
- A restart MUST NOT interpret a missing reply as proof of success or non-execution.

## PH1-R02 Conditional recovery

- Keep `not_dispatched`, confirmed completion, confirmed failure, and unknown result facts distinct.
- Let verified adapter guarantees determine query, wait, retry, continue, or human-attention eligibility.
- A client idempotency key alone is not proof of server-side atomic deduplication.
- Temporary not-found is not proof that a late side effect cannot occur.
- Automatic retry is allowed only when the declared contract makes it safe and the remaining budget permits it.
- Human handling may add evidence, terminate the flow, or explicitly authorize a separately tracked risk-bearing attempt; it MUST preserve the original unknown fact.

## PH1-R03 Cancellation and stopping

- Record cancellation request, cancellation acceptance, prohibition of new downstream dispatch, stopping confirmation, and side-effect result as separate facts.
- Cancellation MUST NOT claim rollback of an existing side effect.
- Dispatch/cancel ordering determines whether an action is in flight and requires reconciliation.
- Late results remain visible but MUST NOT restart downstream execution after cancellation.

## PH1-R04 Approval and bounded execution

- Approval binds exact run, action, target, input/payload identity, action digest, and digest version.
- Changed action content, target, identity, or relevant recovery input invalidates prior approval without rewriting its history.
- Rejection or invalid approval prevents dispatch.
- Retry-count and execution-time budgets have declared values, consumption facts, and exhaustion reasons.
- Restart and recovery preserve consumed budget. Exhaustion prevents new attempts while preserving actual or unknown in-flight results.
- Human-wait time is recorded separately from execution time unless a future accepted contract says otherwise.

## PH1-R05 Model and tool contracts

- Validate inputs before invocation and separately record response receipt, structural validity, business acceptance, and external completion.
- Invalid model output MUST NOT create or dispatch a dependent tool action.
- Adapters declare typed input/output, error categories, request identity, deduplication scope, query semantics, cancellation confirmation, retry eligibility, and known limitations.
- Missing or unverified guarantees force conservative Runtime behavior.
- The deterministic model simulator returns the same structured result for the same valid input and contract version without network, time, locale, or randomness dependence.

## PH1-R06 Reviewable evidence

- Expose run/attempt timelines, rule and approval basis, recovery decisions, budget consumption, result facts, and minimized evidence references.
- Do not put raw input, full model context/output, complete tool payload, approval content, recovery material, or generated canaries in logs, exceptions, representations, or diagnostic exports.
- Export a machine-readable report plus concise human explanation containing scenario, versions, environment, fault point, expected/observed behavior, evidence, limitations, and unverified items.
- Side-effect claims require an independent tool-side observer using storage separate from Runtime. Runtime adapters declared non-queryable MUST NOT access it.

## PH1-R07 Typed interfaces and compatibility

- Provide one minimal developer entry surface with explicit typed submit, query, approve/reject, execute, cancel, manual handling, and report operations as each Stage enables them.
- Errors are typed and expose only data allowed by the disclosure contract.
- Input, digest, action, adapter, rule, event, recovery, query-view, and report contracts carry recognizable versions.
- Missing or changed recovery input and incompatible rules or versions MUST stop safe recovery with an explicit explanation; current defaults MUST NOT replace historical meaning.
- Phase 1 identifies and rejects incompatibility; it does not promise migration for every historical version.

## PH1-R08 Reproducible delivery

- Provide independent installation, sample execution, fault reproduction, and result interpretation instructions.
- Separate package/code version, configuration identity, execution process, and validation environment in evidence.
- Restart scenarios MUST terminate and restart the actual execution process, not simulate restart only by raising an in-process exception.
- Validate the declared clean environments on Python 3.13 and 3.14.
- Keep test passing, release-candidate readiness, public push, and release as separate states.

## State invariants

- Run control, action result, attempt result, approval validity, cancellation/stopping confirmation, budget state, recovery decision, and human decision are orthogonal dimensions.
- Dispatch is an event or execution phase, not an action-result fact.
- Unknown MUST NOT collapse into success, confirmed failure, or retry permission.
- A run completes only when every required action has confirmed completion under its declared contract.
- Historical decisions/events are append-only; current validity is derived.
- Unsupported Stage-later operations fail explicitly and conservatively.

## Operating boundary

- One active execution service; sequential and concurrent requests within it MUST be correct.
- SQLite is the planned local durable store unless Stage 00 explicitly changes it.
- Public/generated small text fixtures only; no network, provider key, private service, private package source, or private data.
- Runtime dependencies remain zero unless purpose, license, maintenance, and supply-chain review approve an addition.
- No throughput, latency, capacity, service-level, model-quality, or arbitrary exactly-once claim.

## Phase 1 non-goals

- Multiple executors, distributed leases, horizontal scaling, or Kubernetes.
- Real model/provider routing, fallback, streaming, MCP platform, prompt platform, RAG, or chat UI.
- Generic planner, DAG editor, agent framework, or multi-agent orchestration.
- Generic compensation/rollback, arbitrary external exactly-once execution, or strong sandboxing.
- Billing, tenancy, general policy language, dashboard, observability SaaS, or model-quality eval platform.
- Learning-product features beyond the generated demonstration.

## Traceability

| Requirement | Primary acceptance |
| --- | --- |
| PH1-R01 | AC-01, AC-02, AC-03, AC-06 |
| PH1-R02 | AC-04, AC-05, AC-06, AC-07, AC-08 |
| PH1-R03 | AC-09, AC-10 |
| PH1-R04 | AC-11, AC-12, AC-13 |
| PH1-R05 | AC-04, AC-05, AC-07, AC-14 |
| PH1-R06 | AC-08, AC-15, AC-16 |
| PH1-R07 | AC-03, AC-14, AC-17 |
| PH1-R08 | AC-06, AC-18 |

## Stage 00 blocking decisions

Freeze request namespace, canonicalization/digest versions, immutable action identity, orthogonal states and transitions, adapter capability declarations, recovery eligibility, cancellation ordering, budget accounting, persistence transactions, data retention/disclosure, typed errors, report schema, fault injection, and the single developer entry surface before implementation.
