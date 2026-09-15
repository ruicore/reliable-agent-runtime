# Reliable Agent Runtime: public implementation brief

This brief is the clean-room entry point for the first public milestone. It
contains only the public problem, independent product boundary, and acceptance
contract.

The development baseline is Python 3.14. The public package supports Python 3.13
and newer, with release validation covering Python 3.13 and 3.14.

## Problem

When a tool-using agent times out, is cancelled, or is restarted, a developer
needs to know whether an external action happened, whether it is safe to retry,
and whether human approval still applies to the exact action being considered.

## First scenario

Use public or generated Markdown as input. A deterministic model simulator creates
a practice-card document. A user approves a specific write action. A local tool
simulator records the side effect. The simulator can expose either a queryable,
deduplicating guarantee or an unknown-result boundary.

## Required behavior

- Persist a logical run, actions, attempts, and decisions before dispatch.
- Preserve unknown outcomes; do not infer success or safe retry from a missing reply.
- Bind approval to the exact action and input identity.
- Record cancellation acceptance separately from confirmed stopping.
- Keep attempt and execution budgets across process restart.
- Produce redacted, reproducible execution evidence.

## Explicit non-goals

No real provider credentials, private services, model training, generic agent
orchestration, multi-tenant billing, dashboard, Kubernetes control plane, or
guarantee of exactly-once execution for arbitrary external services.

The detailed acceptance matrix is derived from this brief before implementation.
