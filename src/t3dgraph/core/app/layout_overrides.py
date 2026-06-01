"""그래프별 노드 위치 오버라이드 — F18 드래그 결과 세션 보관."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class LayoutOverrides:
    """graph_key → {node_name → (x, y)} 의 두 단계 dict."""

    _by_graph: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)

    def set(self, graph_key: str, node: str, x: float, y: float) -> None:
        self._by_graph.setdefault(graph_key, {})[node] = (x, y)

    def get(self, graph_key: str, node: str) -> tuple[float, float] | None:
        return self._by_graph.get(graph_key, {}).get(node)

    def clear_node(self, graph_key: str, node: str) -> None:
        graph = self._by_graph.get(graph_key)
        if graph is not None:
            graph.pop(node, None)

    def clear_graph(self, graph_key: str) -> None:
        self._by_graph.pop(graph_key, None)

    def all_for_graph(self, graph_key: str) -> dict[str, tuple[float, float]]:
        return dict(self._by_graph.get(graph_key, {}))

    def graph_keys(self) -> Iterable[str]:
        """현재 보관 중인 graph_key 목록. 직렬화/cleanup용 public."""
        return self._by_graph.keys()

    def clear_by_prefix(self, prefix: str) -> None:
        """prefix 로 시작하는 모든 graph_key 의 데이터를 삭제 (탭 close 시 사용)."""
        for k in [k for k in self._by_graph if k.startswith(prefix)]:
            del self._by_graph[k]
