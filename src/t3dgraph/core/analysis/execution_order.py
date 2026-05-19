"""구조화된 실행 순서 — 진입 노드부터 위상 순회."""
from __future__ import annotations
from dataclasses import dataclass
from ..base.graph_model import GraphModel
from .flow import analyze_flow


@dataclass
class ExecutionStep:
    node: str
    depth: int


def compute_execution_order(graph: GraphModel) -> list[ExecutionStep]:
    flow = analyze_flow(graph)
    out_edges: dict[str, list[str]] = {}
    in_count: dict[str, int] = {}
    nodes_in_flow: set[str] = set()
    for s, t in flow.execution_edges:
        out_edges.setdefault(s, []).append(t)
        in_count[t] = in_count.get(t, 0) + 1
        nodes_in_flow.update((s, t))

    entries = sorted(n for n in nodes_in_flow if in_count.get(n, 0) == 0)

    steps: list[ExecutionStep] = []
    visited: set[str] = set()

    def walk(node: str, depth: int) -> None:
        if node in visited:
            return
        visited.add(node)
        steps.append(ExecutionStep(node=node, depth=depth))
        succ = out_edges.get(node, [])
        child_depth = depth if len(succ) <= 1 else depth + 1
        for nxt in succ:
            walk(nxt, child_depth)

    for e in entries:
        walk(e, 0)
    return steps
