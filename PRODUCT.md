---
audience: human
document_role: concise_product_summary
normative: false
---

# Reliable Agent Runtime

Reliable Agent Runtime helps developers operate small tool-using agent workflows. It records what the agent actually did and provides evidence for deciding whether to continue, reconcile, stop, or request human review after interruption, timeout, cancellation, restart, or an uncertain external result.

## Product capabilities

- Durable execution facts for runs, actions, attempts, approvals, rules, and outcome evidence.
- Safe duplicate handling that resolves identical requests to one logical run and rejects conflicting reuse of an identity.
- Conditional recovery based on verified tool query, deduplication, and cancellation guarantees; uncertainty remains explicit when evidence is insufficient.
- Exact approval and cancellation semantics that keep approval identity, cancellation acceptance, stopping confirmation, and side-effect facts separate.
- Bounded execution with retry-count and execution-time budgets that survive process restarts.
- Reviewable evidence through independent tool-side observations, redacted timelines, machine-readable reports, and reproducible fault scenarios.
- Explicit compatibility boundaries for inputs, rules, actions, adapters, and reports.
- SQLite through SQLAlchemy is the only Phase 1 persistence path; PostgreSQL and dual-backend operation are not included.

## Product Phase 1

Phase 1 delivers the complete current product baseline. Recovery, cancellation, budgets, compatibility, and evidence are internal delivery stages, not deferred product phases:

1. Stage 00 freezes interfaces, states, identities, persistence, errors, data rules, and acceptance contracts.
2. Stage 01 delivers the traceable, approval-gated deterministic model-tool vertical slice.
3. Stage 02 adds uncertain-result handling, real process restart, conditional recovery, and human resolution.
4. Stage 03 adds cancellation and stopping confirmation, approval invalidation, retry budgets, and time budgets.
5. Stage 04 completes redacted evidence, the fault matrix, compatibility validation, and independently reproducible delivery.

The demonstration uses public or generated Markdown. A deterministic model simulator creates practice cards, a user approves the exact write action, and a local tool simulator records the side effect. Tests verify the actual result through an independent tool-side store.

The project is currently in Stage 00 contract planning. Runtime feature implementation has not started.

## Not this product

This is not a general agent framework, model-provider gateway, chat or RAG application, model-quality evaluation platform, multi-agent orchestrator, observability SaaS, billing system, strong sandbox, or exactly-once guarantee for arbitrary external services.
