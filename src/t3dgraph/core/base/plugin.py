"""그래프 타입 플러그인 계약."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
from .interpreter import AbstractGraphInterpreter


@dataclass
class GraphTypePlugin:
    id: str
    class_prefixes: list[str]
    interpreter_factory: Callable[[], AbstractGraphInterpreter]
    view_ref: str | None = None
    controller_ref: str | None = None

    def matches(self, class_path: str) -> bool:
        return any(class_path.startswith(p) for p in self.class_prefixes)
