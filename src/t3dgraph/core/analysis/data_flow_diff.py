from __future__ import annotations
from dataclasses import dataclass, field
from .data_flow import DataFlowResult
from .compute_trace import compute_trace


@dataclass
class PerSinkDiff:
    added_ancestors: list[str] = field(default_factory=list)
    removed_ancestors: list[str] = field(default_factory=list)
    depth_changes: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class DataFlowDiff:
    sinks_only_in_a: list[str] = field(default_factory=list)
    sinks_only_in_b: list[str] = field(default_factory=list)
    sinks_common: list[str] = field(default_factory=list)
    per_sink: dict[str, PerSinkDiff] = field(default_factory=dict)


def _depth_map(sink: str, incoming: dict[str, list[str]]) -> dict[str, int]:
    levels = compute_trace(sink, incoming)
    out: dict[str, int] = {}
    for lv in levels:
        for n in lv.nodes:
            out.setdefault(n, lv.depth)
    return out


def diff_data_flow(a: DataFlowResult, b: DataFlowResult) -> DataFlowDiff:
    sa = set(a.sinks)
    sb = set(b.sinks)
    diff = DataFlowDiff(
        sinks_only_in_a=sorted(sa - sb),
        sinks_only_in_b=sorted(sb - sa),
        sinks_common=sorted(sa & sb),
    )
    for s in diff.sinks_common:
        da = _depth_map(s, a.incoming_nodes)
        db = _depth_map(s, b.incoming_nodes)
        diff.per_sink[s] = PerSinkDiff(
            added_ancestors=sorted(set(db) - set(da)),
            removed_ancestors=sorted(set(da) - set(db)),
            depth_changes={n: (da[n], db[n]) for n in (set(da) & set(db)) if da[n] != db[n]},
        )
    return diff
