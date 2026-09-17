---
audience: codex
document_role: product_contract
scope: product
authority: normative
status: active
human_readable: false
---

# Reliable Agent Runtime Product Contract

Interpret `must`, `must not`, `required`, and `prohibited` as normative constraints. Do not infer features from common runtime conventions.

This is the independent public product authority. It contains no private provenance. The current product baseline is delivered as one product phase with internal stages; an internal stage is not a narrower product definition.

Development baseline: Python 3.14. Supported floor: Python 3.13. Release validation MUST cover Python 3.13 and 3.14.

## Problem

When a tool-using agent times out, is cancelled, or restarts, a developer needs evidence of what happened, whether retry is safe, whether an approval still matches the action, and whether cancellation means the work actually stopped.

## Independent scenario

Use public or generated Markdown. A deterministic model simulator produces a practice-card document. A user reviews an immutable write action. A local tool simulator records the side effect. Tool variants separately declare query, deduplication, and cancellation guarantees. An independent test observer, unavailable to non-queryable Runtime adapters, verifies the actual side effect.

## Current complete product behavior

- Persist logical runs, immutable actions, attempts, approvals, rules, budgets, decisions, and append-only events before relevant dispatch.
- Resolve identical submissions to one logical run and reject conflicting reuse of request identity.
- Preserve unknown external outcomes; a missing or late reply is not success, confirmed failure, or retry permission.
- Recover only from declared, verified adapter guarantees; otherwise pause or require an explicit human decision that preserves the original unknown fact.
- Bind approval to exact action, target, input, and digest identities; changes invalidate old approval.
- Record cancellation acceptance, dispatch ordering, stopping confirmation, late results, and side-effect facts independently.
- Persist retry and execution-time budgets across process restart and prohibit new attempts after exhaustion.
- Distinguish response receipt, structural validity, business acceptance, and external completion.
- Expose typed, versioned interfaces and reject unsafe recovery when required data or compatible rules are unavailable.
- Produce minimized, redacted, reproducible evidence with independent tool-side observation.

## Product Phase 1

Phase 1 contains the complete behavior above. It is delivered through:

`Stage 00 contract design -> Stage 01 traceable execution -> Stage 02 recoverable execution -> Stage 03 controlled execution -> Stage 04 reproducible delivery`

Every implementation Stage (01-04) delivers an operable, verified increment and preserves conservative defaults for capabilities not yet implemented. Stage 00 is the contract gate. Phase 1 exits only when AC-01 through AC-18 pass with the required evidence. Planning, implementation, validation, public push, and release remain separate facts.

## Explicit non-goals

No real provider credentials, private services, generic agent framework, provider gateway, MCP platform, RAG/chat product, model-quality evaluation platform, multi-agent orchestration, multi-tenant billing, policy language, strong sandbox guarantee, observability SaaS, Kubernetes control plane, distributed executor coordination, generic compensation, or exactly-once guarantee for arbitrary external services.

Future product increments require a newly assessed capability or failure boundary, a concrete user problem, a requirement change, and independent acceptance. New libraries, frameworks, or models alone do not expand the product.
