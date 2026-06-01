"""그래프 종류 무관 추상 데이터 모델."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DroppedObject:
    """인터프리터가 처리하지 못해 그래프에 들어가지 못한 객체."""
    name: str
    cls: str | None
    reason: str            # "unknown class" | "depth cap" | "graph at top" | "no resolver"
    parent_obj: str | None # 부모 객체명 (재귀 손실 추적). top-level이면 None


@dataclass
class InterpreterDiagnostics:
    """인터프리터 한 사이클의 정량 진단."""
    objects_dropped: list[DroppedObject] = field(default_factory=list)
    extracted_per_class: dict[str, int] = field(default_factory=dict)
    max_depth_seen: int = 0
    contained_graph_count: int = 0
    external_refs_unresolved: list[str] = field(default_factory=list)


@dataclass
class Pin:
    name: str
    cpp_type: str | None
    direction: str | None
    default_value: str | None = None
    is_execution: bool = False
    subpins: list["Pin"] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    variable_source: str | None = None   # F16: 변수 노드에서 값이 공급되는 경우 변수명


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
    subgraph: "GraphModel | None" = None      # F6: ContainedGraph 추출 결과
    extra_subgraphs: list["GraphModel"] = field(default_factory=list)  # C-A1: 다중 자식 보존


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
    label: str | None = None                                # F5: 브레드크럼/탭 라벨
    parent_node: str | None = None                          # F6: 자식 그래프의 부모 노드명
    boundary_refs: list[str] = field(default_factory=list)  # §7.4 경계 핀 참조
    diagnostics: InterpreterDiagnostics | None = None

    def node_by_name(self, name: str) -> Node | None:
        for n in self.nodes:
            if n.name == name:
                return n
        return None
