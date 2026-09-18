---
audience: codex
document_role: codex_context_index
scope: repository
authority: routing
status: active
human_readable: false
---

# Codex Context Index

## Load order

1. `product-contract.md`
2. `phases/README.md`
3. Active phase `README.md`
4. Active phase `requirements.md`
5. Active phase `acceptance.md`
6. Active phase `phase-plan.md`
7. Active internal-stage file only

Current phase: `PH1`

Current stage: `PH1-ST00`

Implementation authorization: `false`

## Resolution rules

- Higher authority overrides lower authority.
- A task without a requirement ID and acceptance mapping is out of scope.
- A blocked dependency prohibits downstream work.
- `not_run`, `blocked`, `passed`, and `released` are distinct states.
- Missing evidence MUST NOT be replaced by inference.
- Product expansion requires a newly accepted capability-derived product increment;
  unfinished Phase 1 scope continues without inventing a new product phase.
- Private provenance MUST NOT enter this repository.
- Only `../../PRODUCT.md` is intentionally optimized for human product reading.
- The private catalog owns product scope, capability mapping, and phase status;
  this repository owns the public implementation contract and detailed execution
  plan. These documents are an independently reviewed public expression, not a
  mirror of private planning files.
- When a requirement, acceptance rule, or Stage gate changes, update the private
  product source first, then synchronize the public-safe contract and run the
  consistency checks before implementation.

## State mutation protocol

When work status changes, update the narrowest owning document first, then update
the phase manifest and this index if the active phase, active stage, or
implementation authorization changes. Never rewrite historical evidence to match a
new plan.
