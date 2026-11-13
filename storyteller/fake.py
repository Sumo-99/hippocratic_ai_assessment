"""Scripted stand-in for the LLM. Tests never touch the network."""
from typing import Any


class FakeLLM:
    def __init__(self, script: dict[str, list[Any]]):
        self.script = {stage: list(items) for stage, items in script.items()}
        self.calls: list[tuple[str, str, str]] = []  # (stage, system, user)
        self.schemas: list[tuple[str, Any]] = []      # (stage, schema) for structured calls

    def _next(self, system: str, user: str, stage: str) -> Any:
        self.calls.append((stage, system, user))
        queue = self.script.get(stage)
        assert queue, f"FakeLLM: no scripted reply left for stage {stage!r}"
        item = queue.pop(0)
        return item(system, user) if callable(item) else item  # callable = computed reply

    async def text(self, system, user, *, stage):
        return self._next(system, user, stage)

    async def structured(self, system, user, schema, *, stage):
        self.schemas.append((stage, schema))
        return self._next(system, user, stage)
