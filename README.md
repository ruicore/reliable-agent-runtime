# Reliable Agent Runtime

A small, inspectable runtime for durable agent tool execution, recovery,
cancellation, and evidence.

This repository is being built from a public problem statement and generated
fixtures. It is not a provider proxy, a general-purpose agent framework, a chat
application, or an observability SaaS.

## Product boundary

The runtime helps developers answer what an agent workflow actually completed,
which side effects remain unknown, whether a retry is safe, and whether an action
still has valid approval. The first public scenario uses deterministic model and
tool simulators; it does not require private services or credentials.

The implementation brief records the current public product boundary. A detailed
acceptance matrix will be added before implementation. Every behavior must be
supported by a reproducible test and an explicit failure semantic.

## Status

Planning reset: clean repository created on 2026-09-15. Runtime implementation has
not started.

## Local development

The development baseline is Python 3.14, with Python 3.13 as the minimum
supported version. Release validation should cover both 3.13 and 3.14. Create an
environment, install the package in editable mode with `pip install -e .[test]`,
and run `python -m pytest`. The initial implementation brief defines the product
contracts; implementation is intentionally still pending.

## License

MIT. See [LICENSE](LICENSE).
