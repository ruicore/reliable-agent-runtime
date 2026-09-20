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

## Installation

The alpha distribution is intended for Python 3.13 and 3.14:

```text
python -m pip install reliable-agent-runtime
```

The package is local-first and does not require a model-provider account or a
hosted service. SQLite is used through SQLAlchemy; external providers and
production coordination are outside the Phase 1 boundary.

## Minimal usage

```python
from reliable_agent_runtime import DeterministicModel, RuntimeService, SQLiteRepository
from reliable_agent_runtime.tool import SideEffectStore, SimulatedTool

effects = SideEffectStore()
runtime = RuntimeService(SQLiteRepository(), DeterministicModel(), SimulatedTool(effects))
view = runtime.submit(request_id="example-1", text="durable execution")
runtime.approve(view.action.action_id)
completed = runtime.execute(run_id=view.run.run_id)
```

The public repository contains the complete contract, recovery/control examples,
fault matrix, and reproducibility instructions.

Stages 00-04 are complete for the Phase 1 local product baseline. The project
now enters maintenance and capability-driven evolution: a new stage is opened
only when a newly evidenced capability or failure boundary changes the product
contract. External provider guarantees, distributed coordination, production
deployment, and release publication remain outside this baseline.

## Not this product

This is not a general agent framework, model-provider gateway, chat or RAG application, model-quality evaluation platform, multi-agent orchestrator, observability SaaS, billing system, strong sandbox, or exactly-once guarantee for arbitrary external services.
