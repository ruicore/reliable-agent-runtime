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
- SQLite through SQLAlchemy is the supported persistence path in this release; PostgreSQL and dual-backend operation are not included.

The demonstration uses public or generated Markdown. A deterministic model simulator creates practice cards, a user approves the exact write action, and a local tool simulator records the side effect. Tests verify the actual result through an independent tool-side store.

## Installation

The alpha distribution is intended for Python 3.13 and 3.14:

```text
python -m pip install reliable-agent-runtime
```

The package is local-first and does not require a model-provider account or a
hosted service. SQLite is used through SQLAlchemy; external providers and
production coordination are outside the current release scope.

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
fault matrix, and reproducibility instructions. The implementation evolves when
new evidence changes the runtime contract or exposes a new failure boundary.
External provider guarantees, distributed coordination, production deployment,
and release publication are outside the current release scope.

## Not this product

This is not a general agent framework, model-provider gateway, chat or RAG application, model-quality evaluation platform, multi-agent orchestrator, observability SaaS, billing system, strong sandbox, or exactly-once guarantee for arbitrary external services.
