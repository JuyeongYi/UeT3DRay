"""그래프 종류 무관 추상 데이터 모델."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Pin:
    name: str
    cpp_type: str | None
    direction: str | None
    default_value: str | None = None
    is_execution: bool = False
    subpins: list["Pin"] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    name: str
    cls: str | None
    pins: list[Pin] = field(default_factory=list)
    position: tuple[float, float] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    is_generic: bool = False
    kind: str = "node"          # node | loop | sequence | function
    display_name: str | None = None
    role_summary: str | None = None
    role_category: str | None = None


@dataclass
class Link:
    source_path: str
    target_path: str


@dataclass
class VariableRef:
    variable_name: str
    cpp_type: str | None
    node_name: str


@dataclass
class GraphModel:
    nodes: list[Node] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    variable_refs: list[VariableRef] = field(default_factory=list)
    external_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def node_by_name(self, name: str) -> Node | None:
        for n in self.nodes:
            if n.name == name:
                return n
        return None
