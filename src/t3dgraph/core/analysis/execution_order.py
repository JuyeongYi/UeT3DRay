"""구조화된 실행 순서 — 진입 노드부터 위상 순회."""
from __future__ import annotations
from dataclasses import dataclass
from ..base.graph_model import GraphModel
from .flow import analyze_flow, FlowResult


@dataclass
class ExecutionStep:
    node: str
    depth: int
    kind: str = "node"


def compute_execution_order(
    graph: GraphModel, flow: FlowResult | None = None
) -> list[ExecutionStep]:
    if flow is None:
        flow = analyze_flow(graph)
    out_edges: dict[str, list[str]] = {}
    in_count: dict[str, int] = {}
    nodes_in_flow: set[str] = set()
    for s, t in flow.execution_edges:
        out_edges.setdefault(s, []).append(t)
        in_count[t] = in_count.get(t, 0) + 1
        nodes_in_flow.update((s, t))

    entries = sorted(n for n in nodes_in_flow if in_count.get(n, 0) == 0)
    node_kind = {n.name: n.kind for n in graph.nodes}

    steps: list[ExecutionStep] = []
    visited: set[str] = set()
    for entry in entries:
        stack: list[tuple[str, int]] = [(entry, 0)]
        while stack:
            node, depth = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            steps.append(ExecutionStep(node=node, depth=depth, kind=node_kind.get(node, "node")))
            succ = out_edges.get(node, [])
            child_depth = depth if len(succ) <= 1 else depth + 1
            for nxt in reversed(succ):          # 역순 push → 원래 순서로 pop
                stack.append((nxt, child_depth))
    return steps
