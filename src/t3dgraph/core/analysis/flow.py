"""실행 흐름 분석 — fan-in 수렴점, 공통 다운스트림."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin


@dataclass
class Convergence:
    node: str
    incoming_nodes: list[str]
    common_downstream: list[str]


@dataclass
class FlowResult:
    execution_edges: list[tuple[str, str]] = field(default_factory=list)
    convergence_points: list[str] = field(default_factory=list)
    branch_points: list[str] = field(default_factory=list)
    _convergences: dict[str, Convergence] = field(default_factory=dict)

    def convergence(self, node: str) -> Convergence:
        return self._convergences[node]


def _node_of(pin_path: str) -> str:
    return pin_path.split(".", 1)[0]


def _exec_pin_index(graph: GraphModel) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()

    def walk(node_name: str, pin: Pin) -> None:
        if pin.is_execution:
            out.add((node_name, pin.name))
        for sp in pin.subpins:
            walk(node_name, sp)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p)
    return out


def _pin_name(pin_path: str) -> str:
    parts = pin_path.split(".")
    return parts[1] if len(parts) > 1 else ""


def analyze_flow(graph: GraphModel) -> FlowResult:
    exec_pins = _exec_pin_index(graph)
    edges: list[tuple[str, str]] = []
    for link in graph.links:
        s_node, t_node = _node_of(link.source_path), _node_of(link.target_path)
        s_pin, t_pin = _pin_name(link.source_path), _pin_name(link.target_path)
        if (s_node, s_pin) in exec_pins and (t_node, t_pin) in exec_pins:
            edges.append((s_node, t_node))

    in_edges: dict[str, list[str]] = {}
    out_edges: dict[str, list[str]] = {}
    for s, t in edges:
        in_edges.setdefault(t, []).append(s)
        out_edges.setdefault(s, []).append(t)

    result = FlowResult(execution_edges=edges)
    result.convergence_points = sorted(n for n, srcs in in_edges.items() if len(srcs) >= 2)
    result.branch_points = sorted(n for n, tgts in out_edges.items() if len(tgts) >= 2)

    for node in result.convergence_points:
        result._convergences[node] = Convergence(
            node=node,
            incoming_nodes=sorted(in_edges[node]),
            common_downstream=_reachable(node, out_edges),
        )
    return result


def _reachable(start: str, out_edges: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    queue: deque[str] = deque(out_edges.get(start, []))
    while queue:
        n = queue.popleft()
        if n in seen:
            continue
        seen.add(n)
        queue.extend(out_edges.get(n, []))
    return sorted(seen)
