"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from ..analysis.flow import FlowResult
from ..base.paths import pin_segment, type_suffix, node_of
from .items import NodeItem, LinkItem
from .view_state import ViewState


class GraphScene(QGraphicsScene):
    pin_toggle_requested = Signal(str)        # Slice A: 핀 행 토글 (full_path)
    enter_subgraph_requested = Signal(str)    # Slice C: 헤더 더블클릭 (node name)

    def __init__(self) -> None:
        super().__init__()
        self._nodes: dict[str, NodeItem] = {}
        self._links: list[tuple[LinkItem, str, str]] = []

    def node_item(self, name: str) -> NodeItem | None:
        return self._nodes.get(name)

    def populate(self, graph: GraphModel, *,
                 view_state: ViewState | None = None,
                 flow: FlowResult | None = None) -> None:
        vs = view_state or ViewState()
        keep_selected = self.selected_node_name()
        self.clear()
        self._nodes = {}
        self._links = []

        connected = self._connected_paths_by_node(graph)
        convergence = set(flow.convergence_points) if flow is not None else set()

        fallback_i = 0
        for node in graph.nodes:
            item = NodeItem(
                node,
                connected_paths=frozenset(connected.get(node.name, set())),
                connected_only=vs.connected_pins_only,
                expanded_paths=frozenset(
                    p for p in vs.expanded_pin_paths if p.startswith(f"{node.name}.")
                ),
                highlighted=vs.fan_in_highlight and node.name in convergence,
            )
            if node.position is None:
                item.setPos((fallback_i % 8) * 240.0, (fallback_i // 8) * 200.0)
                fallback_i += 1
            if item.bus is not None:
                item.bus.pin_toggle_requested.connect(self.pin_toggle_requested)
                item.bus.enter_subgraph_requested.connect(self.enter_subgraph_requested)
            self.addItem(item)
            self._nodes[node.name] = item
        for link in graph.links:
            self._add_link(link)

        self.apply_hidden_types(vs.hidden_node_types)
        if keep_selected in self._nodes:
            self.select_node(keep_selected)

    @staticmethod
    def _connected_paths_by_node(graph: GraphModel) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for link in graph.links:
            for path in (link.source_path, link.target_path):
                node = pin_segment(path, 0)
                bucket = out.setdefault(node, set())
                parts = path.split(".")
                for i in range(2, len(parts) + 1):
                    bucket.add(".".join(parts[:i]))
        return out

    def _add_link(self, link: Link) -> None:
        s_node, t_node = node_of(link.source_path), node_of(link.target_path)
        src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
        if src is None or dst is None:
            return
        s_sub = link.source_path.split(".", 1)[1] if "." in link.source_path else ""
        t_sub = link.target_path.split(".", 1)[1] if "." in link.target_path else ""
        p1 = src.pin_anchor(s_sub, "Output")
        p2 = dst.pin_anchor(t_sub, "Input")
        item = LinkItem(p1, p2)
        self.addItem(item)
        self._links.append((item, s_node, t_node))

    def select_node(self, name: str) -> None:
        self.clearSelection()
        item = self._nodes.get(name)
        if item is not None:
            item.setSelected(True)

    def selected_node_name(self) -> str | None:
        for name, item in self._nodes.items():
            try:
                if item.isSelected():
                    return name
            except RuntimeError:
                pass
        return None

    def apply_fan_in_highlight(self, convergence: set[str], on: bool) -> None:
        for name, item in self._nodes.items():
            item.set_highlighted(on and name in convergence)

    def apply_search_highlight(self, hits: set[str]) -> None:
        """검색 매치 노드는 불투명, 미매치는 흐리게. hide 금지(PRESERVE-ALL)."""
        for name, item in self._nodes.items():
            item.setOpacity(1.0 if name in hits else 0.35)

    def apply_hidden_types(self, hidden_types: set[str]) -> None:
        for item in self._nodes.values():
            item.setVisible(type_suffix(item.node.cls) not in hidden_types)
        for link_item, s_node, t_node in self._links:
            src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
            visible = (src is not None and src.isVisible()
                       and dst is not None and dst.isVisible())
            link_item.setVisible(visible)
