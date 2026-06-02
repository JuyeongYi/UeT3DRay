"""데이터 흐름 분석 — 핀 단위 정보 보존(PRESERVE-INFO)."""
from __future__ import annotations
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin
from ..base.pin_ref import PinRef
from ..base.paths import pin_rel_path


@dataclass(frozen=True)
class DataFlowEdge:
    source: PinRef
    target: PinRef

    @property
    def source_node(self) -> str:
        return self.source.node

    @property
    def target_node(self) -> str:
        return self.target.node


@dataclass
class DataFlowResult:
    data_edges: list[DataFlowEdge] = field(default_factory=list)
    # 엣지 단위 인덱스 — 핀 정보 보존
    inputs_of: dict[str, list[DataFlowEdge]] = field(default_factory=dict)
    outputs_of: dict[str, list[DataFlowEdge]] = field(default_factory=dict)
    # 노드 단위 호환 — 중복 제거 + 정렬
    incoming_nodes: dict[str, list[str]] = field(default_factory=dict)
    outgoing_nodes: dict[str, list[str]] = field(default_factory=dict)
    sinks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    isolated: list[str] = field(default_factory=list)
    all_nodes: list[str] = field(default_factory=list)


@dataclass
class DepNode:
    node: str
    children: list["DepNode"] = field(default_factory=list)


def _collect_exec_pin_refs(graph: GraphModel) -> set[PinRef]:
    out: set[PinRef] = set()

    def walk(node_name: str, pin: Pin, prefix: str) -> None:
        full = f"{prefix}.{pin.name}"
        rel = pin_rel_path(node_name, full)
        if pin.is_execution:
            out.add(PinRef(node=node_name, pin_path=rel))
        for sp in pin.subpins:
            walk(node_name, sp, full)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    return out


def analyze_data_flow(graph: GraphModel) -> DataFlowResult:
    exec_refs = _collect_exec_pin_refs(graph)
    edges: list[DataFlowEdge] = []

    for link in graph.links:
        src = PinRef.parse(link.source_path)
        tgt = PinRef.parse(link.target_path)
        if src in exec_refs or tgt in exec_refs:
            continue
        edges.append(DataFlowEdge(source=src, target=tgt))

    inputs_of: dict[str, list[DataFlowEdge]] = {}
    outputs_of: dict[str, list[DataFlowEdge]] = {}
    for e in edges:
        outputs_of.setdefault(e.source_node, []).append(e)
        inputs_of.setdefault(e.target_node, []).append(e)

    incoming_nodes: dict[str, list[str]] = {
        tgt: sorted({e.source_node for e in es})
        for tgt, es in inputs_of.items()
    }
    outgoing_nodes: dict[str, list[str]] = {
        src: sorted({e.target_node for e in es})
        for src, es in outputs_of.items()
    }

    all_nodes = [n.name for n in graph.nodes]
    nodes_with_data = set(incoming_nodes) | set(outgoing_nodes)
    sources = sorted(n for n in nodes_with_data
                     if not incoming_nodes.get(n) and outgoing_nodes.get(n))
    sinks = sorted(n for n in nodes_with_data
                   if incoming_nodes.get(n) and not outgoing_nodes.get(n))

    # F30: isolated 판정은 모든 link 기준 — exec 연결도 "고립 아님"으로 인정
    nodes_with_any_connection: set[str] = set()
    for link in graph.links:
        nodes_with_any_connection.add(PinRef.parse(link.source_path).node)
        nodes_with_any_connection.add(PinRef.parse(link.target_path).node)
    isolated = sorted(n for n in all_nodes if n not in nodes_with_any_connection)

    return DataFlowResult(
        data_edges=edges,
        inputs_of=inputs_of,
        outputs_of=outputs_of,
        incoming_nodes=incoming_nodes,
        outgoing_nodes=outgoing_nodes,
        sinks=sinks,
        sources=sources,
        isolated=isolated,
        all_nodes=all_nodes,
    )


def dependency_tree(
    sink: str,
    incoming_nodes: dict[str, list[str]],
    max_depth: int = 64,
) -> DepNode:
    """sink 기준 의존 트리 — 노드 단위(시각화 단순화).

    노드 중복 cap: 한 번 본 노드는 children에 두지 않음(순환·DAG fan-in 보호).
    """
    seen: set[str] = set()

    def build(name: str, depth: int) -> DepNode | None:
        if name in seen or depth >= max_depth:
            return None
        seen.add(name)
        node = DepNode(node=name)
        for src in incoming_nodes.get(name, []):
            child = build(src, depth + 1)
            if child is not None:
                node.children.append(child)
        return node

    return build(sink, 0) or DepNode(node=sink)
