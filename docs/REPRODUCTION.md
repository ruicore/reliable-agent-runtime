# Reliable Agent Runtime: Reproduction Guide

This guide is intentionally limited to the public Phase 1 simulator. It does
not claim compatibility with arbitrary model providers or external tools.

## Supported environments

- Development baseline: Python 3.14
- Compatibility floor: Python 3.13
- Persistence: SQLite through SQLAlchemy only
- Dependency manager: `uv`

Install the locked test environment from the repository root:

```text
uv sync --extra test --frozen
```

## Normal scenario

Run the deterministic model-tool and all contract tests:

```text
uv run pytest -q
```

The normal scenario submits canonical Markdown, persists the action intent,
requires exact approval, dispatches the local simulated tool, and verifies the
side effect through a separate observer. The runtime report contains only
digests, state, event kinds, budget facts, and bounded environment identity.

## Fault matrix

The repeatable matrix is encoded in `tests/test_r1_vertical_slice.py`,
`tests/test_stage03_controlled_execution.py`, and
`tests/test_stage04_reproducible_delivery.py`.

```text
uv run pytest -q
```

The matrix covers duplicate and conflicting submission, invalid model output,
malformed tool responses, lost replies, query reconciliation, conservative
retry, human handling, real subprocess restart, cancellation interleavings,
late results, approval invalidation, retry/time exhaustion, redaction, and
decision-signature reproducibility.

## Reports

`RuntimeService.report(run_id)` returns the versioned machine report. Use
`RuntimeService.report_json(run_id)` for a JSON artifact and
`RuntimeService.human_report(run_id)` for the concise explanation. Reports do
not include raw input, model body, tool payload, approval content, recovery
material, or canary values. Independent side-effect evidence remains an input
from the test harness; Runtime alone cannot assert it.

The `reproducibility.decision_signature` value compares repeated controlled
faults while allowing run/action/attempt identities and timestamps to differ.

## Python compatibility checks

Run the exact suite on both declared interpreters:

```text
uv run --python 3.13 --extra test --frozen pytest -q
uv run --python 3.14 --extra test --frozen pytest -q
```

An unavailable interpreter is `unverified`, not a pass. The delivery record
must retain the interpreter version, package version, contract version, and
whether independent observation was attached.

## Interpretation limits

- A simulator result is not a provider guarantee.
- An acknowledgement without typed completion evidence remains `unknown`.
- A cancellation label does not roll back a side effect.
- Unknown results are not automatically retried without verified adapter
  guarantees and remaining budget.
- Passing tests establish the declared local contract, not throughput,
  latency, availability, or arbitrary exactly-once behavior.
