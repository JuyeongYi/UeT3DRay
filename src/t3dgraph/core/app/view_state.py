"""뷰어 표현 상태 — 선택·필터·뷰 모드. 순수 Python(Qt 없음)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ViewState:
    selected_node: str | None = None
    hidden_node_types: set[str] = field(default_factory=set)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    expanded_pin_paths: set[str] = field(default_factory=set)

    def select(self, node: str | None) -> None:
        self.selected_node = node

    def set_type_hidden(self, type_name: str, hidden: bool) -> None:
        if hidden:
            self.hidden_node_types.add(type_name)
        else:
            self.hidden_node_types.discard(type_name)

    def is_type_hidden(self, type_name: str) -> bool:
        return type_name in self.hidden_node_types

    def set_connected_pins_only(self, value: bool) -> None:
        self.connected_pins_only = value

    def set_fan_in_highlight(self, value: bool) -> None:
        self.fan_in_highlight = value

    def is_pin_expanded(self, full_path: str) -> bool:
        return full_path in self.expanded_pin_paths

    def toggle_pin_expanded(self, full_path: str) -> None:
        if full_path in self.expanded_pin_paths:
            self.expanded_pin_paths.remove(full_path)
        else:
            self.expanded_pin_paths.add(full_path)

    def expand_all_pins(self, paths: list[str]) -> None:
        self.expanded_pin_paths.update(paths)

    def collapse_all_pins(self) -> None:
        self.expanded_pin_paths.clear()

    def expand_node_pins(self, node_name: str, all_paths: list[str]) -> None:
        """노드의 모든 핀 path(서브핀 포함)를 expanded set에 추가."""
        self.expanded_pin_paths.update(all_paths)

    def collapse_node_pins(self, node_name: str) -> None:
        """노드 prefix에 해당하는 path를 expanded set에서 제거."""
        prefix = f"{node_name}."
        self.expanded_pin_paths = {
            p for p in self.expanded_pin_paths if not p.startswith(prefix)
        }
