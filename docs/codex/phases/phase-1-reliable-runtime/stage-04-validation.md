---
audience: codex
document_role: local_validation_record
phase_id: PH1
stage_id: PH1-ST04
status: local_pass
human_readable: false
---

# Stage 04 Local Validation Record

This record captures reproducible local evidence for the Phase 1 delivery gate.
It is not a release or external-provider certification.

## Commands

```text
uv lock --check
uv sync --extra test --frozen
uv run --python 3.13 --extra test --frozen pytest -q
uv run --python 3.14 --extra test --frozen pytest -q
uv run python -m compileall -q src tests
uv build
git diff --check
```

Observed test results: `32 passed` on Python 3.13.12 and `32 passed` on Python
3.14.3. Package source distribution and wheel build successfully.

## Coverage ownership

- AC-01..03 and AC-14: `tests/test_r1_vertical_slice.py`
- AC-04..08 and AC-17: `tests/test_r1_vertical_slice.py`
- AC-09..13: `tests/test_stage03_controlled_execution.py`
- AC-15 and AC-16: `tests/test_stage04_reproducible_delivery.py`
- AC-18: `docs/REPRODUCTION.md` plus the two interpreter runs above

The Stage 04 tests verify that raw canaries are absent from reports and safe
representations, that repeated controlled faults share a decision signature,
and that independent side-effect observation remains outside Runtime state.

## Remaining boundary

The local simulator is not an external provider. Independent tool-side facts
must be supplied by a harness for each real adapter. No throughput, latency,
availability, distributed-coordination, or arbitrary exactly-once claim is
made. Release publication remains a separate authorization decision.
