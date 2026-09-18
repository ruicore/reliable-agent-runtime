"""Deterministic model simulator; it has no network or provider dependency."""

from __future__ import annotations

from .domain import ModelInput, ModelOutput, ModelValidity, canonicalize_input


class DeterministicModel:
    def generate(self, model_input: ModelInput) -> ModelOutput:
        text = canonicalize_input(model_input.text)
        if not text:
            return ModelOutput(
                validity=ModelValidity.INVALID,
                error_code="empty_input",
            )
        return ModelOutput(
            validity=ModelValidity.VALID,
            title=f"Practice card: {text[:80]}",
            body=f"Review the following concept and write one verification question:\n\n{text}",
        )


class InvalidModel:
    """Test-only model used to prove invalid output cannot create an action."""

    def __init__(self, output: object) -> None:
        self.output = output

    def generate(self, model_input: ModelInput) -> object:
        return self.output
