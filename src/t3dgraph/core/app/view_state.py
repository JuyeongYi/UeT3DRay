"""뷰어 표현 상태 — 선택·필터. 순수 Python(Qt 없음)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ViewState:
    selected_node: str | None = None
    hidden_node_types: set[str] = field(default_factory=set)
    connected_pins_only: bool = False
    expand_subpins: bool = False
    fan_in_highlight: bool = False
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for cb in self._listeners:
            cb()

    def select(self, node: str | None) -> None:
        self.selected_node = node
        self._notify()

    def set_type_hidden(self, type_name: str, hidden: bool) -> None:
        if hidden:
            self.hidden_node_types.add(type_name)
        else:
            self.hidden_node_types.discard(type_name)
        self._notify()

    def is_type_hidden(self, type_name: str) -> bool:
        return type_name in self.hidden_node_types

    def set_connected_pins_only(self, value: bool) -> None:
        self.connected_pins_only = value
        self._notify()

    def set_expand_subpins(self, value: bool) -> None:
        self.expand_subpins = value
        self._notify()

    def set_fan_in_highlight(self, value: bool) -> None:
        self.fan_in_highlight = value
        self._notify()
