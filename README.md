# Reliable Agent Runtime Repository Context

Audience: Codex. Treat this file as the repository routing entry point, not as a
human-facing product description. Human product summary: [PRODUCT.md](PRODUCT.md).

## Authority order

1. [Codex document index](docs/codex/README.md)
2. [Product contract](docs/codex/product-contract.md)
3. Current phase requirements and acceptance contract
4. Current phase plan and stage plan
5. Source, tests, and generated evidence after implementation begins

Lower-authority material MUST NOT broaden a higher-authority product boundary.

## Current phase

- Registry: [product phases](docs/codex/phases/README.md)
- Active phase: [PH1 reliable runtime](docs/codex/phases/phase-1-reliable-runtime/README.md)
- Lifecycle: `stage_04_reproducible_delivery`
- Implementation authorization: `authorized_for_phase_1`
- Acceptance status: `stage_04_local_validation_in_progress`
- Public push authorization for current changes: `user_authorized`

## Repository constraints

- Public/generated inputs only.
- No private provenance, services, credentials, paths, or raw session material.
- Runtime behavior MUST trace to an approved phase requirement and acceptance case.
- Unknown external outcomes MUST NOT become success, failure, or retry permission.
- Python development baseline: `3.14`; supported floor: `3.13`.
- Phase 1 owns the complete current product baseline; Stage 00-04 are internal delivery increments.
- Phase 1 implementation includes the deterministic model-tool slice, conditional recovery, cancellation, approval invalidation, persistent retry/execution budgets, minimized reports, and reproducible local fault tests.
- External providers, arbitrary exactly-once guarantees, automatic recovery scans, distributed coordination, and production deployment remain outside Phase 1.

## Commands after implementation authorization

```text
uv sync --extra test
uv run pytest -q

# Reproduce the same checks on the supported floor and development baseline:
uv run --python 3.13 --extra test --frozen pytest -q
uv run --python 3.14 --extra test --frozen pytest -q
```

For the English installation, fault reproduction, and report interpretation
guide, see [Reproduction Guide](docs/REPRODUCTION.md).

License: MIT. See [LICENSE](LICENSE).
