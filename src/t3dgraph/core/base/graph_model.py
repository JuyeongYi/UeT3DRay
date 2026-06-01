"""그래프 종류 무관 추상 데이터 모델."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterator


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

    def iter_paths(self, prefix: str) -> "Iterator[str]":
        path = f"{prefix}.{self.name}"
        yield path
        for sp in self.subpins:
            yield from sp.iter_paths(path)


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

    def find_pin(self, path: str) -> "Pin | None":
        """'NodeName.PinName[.SubPin...]' → Pin. 없으면 None."""
        if not path:
            return None
        parts = path.split(".")
        node = self.node_by_name(parts[0])
        if node is None:
            return None
        cur_pins = node.pins
        last: Pin | None = None
        for name in parts[1:]:
            pin = next((p for p in cur_pins if p.name == name), None)
            if pin is None:
                return None
            last = pin
            cur_pins = pin.subpins
        return last

    def iter_pin_paths(self, *, node_name: str | None = None) -> Iterator[str]:
        """모든 핀 경로(서브핀 포함) 순회. node_name 지정 시 그 노드만."""
        nodes = ([n for n in self.nodes if n.name == node_name]
                 if node_name else self.nodes)
        for node in nodes:
            for pin in node.pins:
                yield from pin.iter_paths(node.name)
