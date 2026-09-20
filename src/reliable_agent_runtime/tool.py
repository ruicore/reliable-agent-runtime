"""Deterministic tool simulator and independent side-effect observer."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from .domain import ActionResultState, ToolOutput


@dataclass(frozen=True, repr=False)
class SideEffect:
    action_id: str
    target: str
    payload: str

    def __repr__(self) -> str:
        from .domain import digest_text

        return (
            "SideEffect("
            f"action_id={self.action_id!r}, target={self.target!r}, "
            f"payload_digest={digest_text(self.payload)!r})"
        )


class SideEffectStore:
    """Separate storage representing the tool's external system."""

    def __init__(self) -> None:
        self._items: dict[str, SideEffect] = {}
        self._lock = Lock()

    def put_once(self, effect: SideEffect) -> None:
        with self._lock:
            self._items.setdefault(effect.action_id, effect)

    def observe(self, action_id: str) -> SideEffect | None:
        with self._lock:
            return self._items.get(action_id)

    def count(self) -> int:
        with self._lock:
            return len(self._items)


class SimulatedTool:
    target = "practice_card_store"

    def __init__(self, side_effects: SideEffectStore) -> None:
        self._side_effects = side_effects
        self.dispatch_count = 0

    def execute(self, *, action_id: str, target: str, payload: str) -> ToolOutput:
        self.dispatch_count += 1
        self._side_effects.put_once(SideEffect(action_id, target, payload))
        return ToolOutput(ActionResultState.SUCCEEDED)


class IndependentObserver:
    """Test observer; Runtime code receives no reference to this type."""

    def __init__(self, side_effects: SideEffectStore) -> None:
        self._side_effects = side_effects

    def find(self, action_id: str) -> SideEffect | None:
        return self._side_effects.observe(action_id)

    def count(self) -> int:
        return self._side_effects.count()
