from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TraceLevel:
    depth: int
    nodes: list[str]


def compute_trace(
    sink: str,
    incoming_nodes: dict[str, list[str]],
    max_depth: int = 64,
) -> list[TraceLevel]:
    seen: set[str] = set()
    levels: list[TraceLevel] = []
    frontier: list[str] = [sink]
    depth = 0
    while frontier and depth <= max_depth:
        unique = sorted({n for n in frontier if n not in seen})
        if not unique:
            break
        levels.append(TraceLevel(depth=depth, nodes=unique))
        seen.update(unique)
        nxt: list[str] = []
        for n in unique:
            for parent in incoming_nodes.get(n, []):
                if parent not in seen:
                    nxt.append(parent)
        frontier = nxt
        depth += 1
    return levels
