---
audience: codex
document_role: phase_acceptance_contract
phase_id: PH1
authority: normative
status: proposed
case_default_status: not_run
human_readable: false
---

# Phase 1 Acceptance Contract

Every case is `not_run` until implementation exists and all required observations have been collected. Missing evidence is `not_run` or `blocked`, never inferred success.

## Evidence record

Each result MUST contain case/contract version, scenario and fault mode, run/action/attempt identities, input/rule/adapter versions, environment, expected and observed behavior, Runtime facts, independent tool-side facts where a side effect is claimed, limitations, unverified boundaries, and final status.

The independent observer uses storage separate from Runtime and is test-only. A non-queryable adapter cannot use it. Runtime state alone cannot prove an external side effect.

## Stage ownership

| Stage | Primary cases | Additional rule |
| --- | --- | --- |
| 00 Contract Design | None | Freeze all case preconditions, faults, observations, and pass criteria; all remain `not_run`. |
| 01 Traceable Execution | AC-01, AC-02, AC-03, AC-14 | Verify approval guard, persist-before-dispatch, conservative unsupported behavior, and baseline redaction. |
| 02 Recoverable Execution | AC-04, AC-05, AC-06, AC-07, AC-08, AC-17 | Add finite retry accounting needed by recovery; do not mark AC-12 complete yet. Regress Stage 01. |
| 03 Controlled Execution | AC-09, AC-10, AC-11, AC-12, AC-13 | Regress Stages 01-02 under cancellation, approval, budget, and late-result interleavings. |
| 04 Reproducible Delivery | AC-15, AC-16, AC-18 | Run complete AC-01..18 regression and public-candidate checks. |

## Cases

### AC-01 Normal approved execution

Submit generated Markdown, inspect and approve the exact immutable action, execute, and query. One logical run/action/approval/attempt is traceable; no side effect exists before dispatch; the independent observer finds exactly one expected product; only confirmed completion completes the run.

### AC-02 Duplicate and concurrent submission

Run sequential, concurrent, waiting-for-approval, and post-completion duplicates with the same request/content identity. Persistent uniqueness returns one logical run and action; the independent observer eventually finds one logical product.

### AC-03 Request identity conflict

Reuse a request identity with different canonical content. Return a typed conflict, preserve the original facts, create no new run/action/side effect, and disclose no raw conflicting content.

### AC-04 Lost reply with verified query/deduplication

The tool writes but its reply is lost. When the adapter has verified reconciliation or deduplication guarantees, Runtime queries first and recognizes the original result under those guarantees without creating a duplicate logical product. Evidence cites the guarantee and observation.

### AC-05 Non-queryable tool timeout after write

The tool writes and then times out, while its Runtime adapter cannot query the result. Preserve unknown, block dependent work, require human attention, and do not retry. The test observer confirms the hidden write without exposing that channel to Runtime.

### AC-06 Process termination and restart matrix

Terminate and restart the execution process around intent persistence, dispatch, tool write, and result persistence boundaries. Recover or pause from durable facts; never infer success or non-dispatch from a missing result; preserve attempts and consumed budgets; reconcile with independent side-effect facts.

### AC-07 Temporary not-found, late success, or ignored idempotency key

When a query temporarily returns not-found but the old request later succeeds, or a tool ignores a client idempotency key, keep unknown unless stable guarantees prove safe retry. Do not dispatch a potentially duplicating retry; record late facts or require human attention.

### AC-08 Human handling of unknown

Allow verified evidence to confirm a fact, allow termination, or allow an explicit risk-bearing new attempt. Preserve the old unknown result, append the human decision and rationale, and give the new attempt a separate identity. A human decision alone is not tool-completion proof.

### AC-09 Cancellation during tool execution

After cancellation takes effect, start no downstream action. Claim stopped only with stopping confirmation. Preserve already occurred or unknown side effects, and do not let a terminal control label hide an unknown action result.

### AC-10 Cancel/dispatch interleaving and late success

Cover cancel-before-dispatch and dispatch-before-cancel. Record ordering and in-flight facts. A late success is visible but does not restart the cancelled flow or schedule downstream work.

### AC-11 Approval invalidation

Change input, target, action, digest, or relevant recovery content after approval, including across restart. Derive old approval as invalid, do not dispatch, and wait for a new exact approval. Explicit rejection also prevents dispatch.

### AC-12 Retry-budget exhaustion

Keep a safely retryable action failing until the declared attempt limit is exhausted. Independent tool call counts do not exceed the limit; restart does not reset consumption; Runtime prevents new attempts and explains the stop or human-attention decision.

### AC-13 Execution-time budget exhaustion

Exhaust execution time with an in-flight call and cover pause for human handling. Start no new attempt; preserve in-flight confirmed or unknown facts; keep consumption across restart; report human-wait time under its separately declared clock.

### AC-14 Model and tool contract failures

Run invalid model structure, confirmed tool business rejection, acknowledgement without completion proof, and invalid tool response structure. Invalid model output creates no executable action; confirmed rejection is not completion; acknowledgement or invalid completion evidence becomes unknown and is not retried automatically.

### AC-15 Redaction and recoverability

Place generated sensitive canaries in input and tool output, restart, and export evidence. Logs, errors, representations, diagnostics, and reports contain no excluded raw value. Authorized recovery material is sufficient to recover or the run explicitly pauses; minimization still explains the fault.

### AC-16 Repeated fault and report reproducibility

Repeat each controlled fault and generate reports. Runtime decisions match independent tool facts; controlled fault and decision are reproducible while timestamps and identities may differ; unverified scope is explicit and simulator evidence is not generalized to arbitrary services.

### AC-17 Missing or incompatible recovery material

Remove or change recovery input, or use incompatible rule/report versions. Explicitly reject safe recovery and explain why. Never substitute current input or current defaults for historical meaning; query and documentation agree.

### AC-18 Clean-environment reproduction

In declared clean Python 3.13 and 3.14 environments, follow English instructions to install, run the normal scenario and fault matrix, and obtain versioned reports. No private service/data is required. An unavailable environment remains unverified and blocks its claim.

## Honest status rules

- A written or collected test that has not run is not passed.
- A Runtime assertion without independent observation cannot pass a side-effect claim.
- An acknowledgement cannot pass completion.
- A Stage result cannot satisfy the whole Phase 1 exit.
- Simulator evidence cannot establish guarantees for arbitrary external services.
- Test completion, release-candidate readiness, push, and release are separate statuses.
