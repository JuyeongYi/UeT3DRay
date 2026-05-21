"""데이터 흐름 분석 — exec 핀이 아닌 핀들 사이의 링크."""
from __future__ import annotations
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin
from ..t3d.paths import node_of


@dataclass
class DataFlowResult:
    data_edges: list[tuple[str, str]] = field(default_factory=list)
    inputs_of: dict[str, list[str]] = field(default_factory=dict)
    outputs_of: dict[str, list[str]] = field(default_factory=dict)
    sinks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    isolated: list[str] = field(default_factory=list)
    all_nodes: list[str] = field(default_factory=list)


@dataclass
class DepNode:
    node: str
    children: list["DepNode"] = field(default_factory=list)


def _collect_exec_pin_paths(graph: GraphModel) -> set[tuple[str, str]]:
    """(node_name, pin_relative_path) 쌍으로 exec 핀 경로 집합 반환."""
    out: set[tuple[str, str]] = set()

    def walk(node_name: str, pin: Pin, prefix: str) -> None:
        full = f"{prefix}.{pin.name}"
        rel = full[len(node_name) + 1:]
        if pin.is_execution:
            out.add((node_name, rel))
        for sp in pin.subpins:
            walk(node_name, sp, full)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    return out


def analyze_data_flow(graph: GraphModel) -> DataFlowResult:
    exec_paths = _collect_exec_pin_paths(graph)
    edges: list[tuple[str, str]] = []

    for link in graph.links:
        s_node = node_of(link.source_path)
        t_node = node_of(link.target_path)
        s_rel = link.source_path[len(s_node) + 1:] if "." in link.source_path else ""
        t_rel = link.target_path[len(t_node) + 1:] if "." in link.target_path else ""
        if (s_node, s_rel) in exec_paths or (t_node, t_rel) in exec_paths:
            continue
        edges.append((s_node, t_node))

    inputs_of: dict[str, list[str]] = {}
    outputs_of: dict[str, list[str]] = {}
    for s, t in edges:
        outputs_of.setdefault(s, []).append(t)
        inputs_of.setdefault(t, []).append(s)

    all_nodes = [n.name for n in graph.nodes]
    nodes_with_data = {x for pair in edges for x in pair}
    sources = sorted(n for n in nodes_with_data
                     if not inputs_of.get(n) and outputs_of.get(n))
    sinks = sorted(n for n in nodes_with_data
                   if inputs_of.get(n) and not outputs_of.get(n))
    isolated = sorted(n for n in all_nodes if n not in nodes_with_data)

    return DataFlowResult(
        data_edges=edges,
        inputs_of=inputs_of,
        outputs_of=outputs_of,
        sinks=sinks,
        sources=sources,
        isolated=isolated,
        all_nodes=all_nodes,
    )


def dependency_tree(
    sink: str,
    inputs_of: dict[str, list[str]],
    max_depth: int = 64,
) -> DepNode:
    """sink에서 출발해 입력 노드들을 자식으로 펼친 트리.

    노드 중복 cap: 한 번 본 노드는 children에 두지 않음(순환·DAG fan-in 보호).
    """
    seen: set[str] = set()

    def build(name: str, depth: int) -> DepNode | None:
        if name in seen or depth >= max_depth:
            return None
        seen.add(name)
        node = DepNode(node=name)
        for src in inputs_of.get(name, []):
            child = build(src, depth + 1)
            if child is not None:
                node.children.append(child)
        return node

    return build(sink, 0) or DepNode(node=sink)
