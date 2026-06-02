"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from ..analysis.flow import FlowResult
from ..base.paths import type_suffix, node_of
from .items import NodeItem, LinkItem
from .layout_overrides import LayoutOverrides
from .node_profiles import NodeProfileTable
from .pin_colors import PinColorTable
from .view_state import ViewState


class GraphScene(QGraphicsScene):
    pin_toggle_requested = Signal(str)
    enter_subgraph_requested = Signal(str)
    node_position_changed = Signal(str, float, float)   # F18
    node_context_menu_requested = Signal(str, object)   # F19

    def __init__(self) -> None:
        super().__init__()
        self._nodes: dict[str, NodeItem] = {}
        # (link_item, src_node, src_sub, dst_node, dst_sub)
        self._links: list[tuple[LinkItem, str, str, str, str]] = []
        self._populating = False  # suppress position_changed during setPos in populate
        self._graph: GraphModel | None = None
        self._pin_colors: "PinColorTable | None" = None

    def node_item(self, name: str) -> NodeItem | None:
        return self._nodes.get(name)

    def populate(self, graph: GraphModel, *,
                 view_state: ViewState | None = None,
                 flow: FlowResult | None = None,
                 pin_colors: "PinColorTable | None" = None,
                 layout_overrides: LayoutOverrides | None = None,
                 graph_key: str = "",
                 node_profiles: "NodeProfileTable | None" = None) -> None:
        vs = view_state or ViewState()
        keep_selected = self.selected_node_name()
        self.clear()
        self._nodes = {}
        self._links = []
        self._graph = graph
        self._pin_colors = pin_colors

        connected = self._connected_paths_by_node(graph)
        convergence = set(flow.convergence_points) if flow is not None else set()

        fallback_i = 0
        self._populating = True
        try:
            for node in graph.nodes:
                profile = None
                if node_profiles is not None:
                    suffix = (node.cls or "").rsplit(".", 1)[-1]
                    profile = node_profiles.resolve(suffix)
                item = NodeItem(
                    node,
                    connected_paths=frozenset(connected.get(node.name, set())),
                    connected_only=vs.connected_pins_only,
                    expanded_paths=frozenset(
                        p for p in vs.expanded_pin_paths if p.startswith(f"{node.name}.")
                    ),
                    highlighted=vs.fan_in_highlight and node.name in convergence,
                    pin_colors=pin_colors,
                    profile=profile,
                )
                override = (layout_overrides.get(graph_key, node.name)
                            if layout_overrides is not None else None)
                if override is not None:
                    item.setPos(*override)
                elif node.position is None:
                    item.setPos((fallback_i % 8) * 240.0, (fallback_i // 8) * 200.0)
                    fallback_i += 1
                item.bus.pin_toggle_requested.connect(self.pin_toggle_requested)
                item.bus.enter_subgraph_requested.connect(self.enter_subgraph_requested)
                item.bus.position_changed.connect(self._relay_position_changed)
                item.bus.context_menu_requested.connect(self.node_context_menu_requested)
                self.addItem(item)
                self._nodes[node.name] = item
        finally:
            self._populating = False
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
                node = node_of(path)
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
        color = None
        color_end = None
        is_exec = False
        if self._graph is not None:
            src_pin = self._graph.find_pin(link.source_path)
            if src_pin is not None:
                is_exec = src_pin.is_execution
                if self._pin_colors is not None:
                    color = self._pin_colors.resolve(src_pin.cpp_type).color
            if not is_exec and self._pin_colors is not None:
                dst_pin = self._graph.find_pin(link.target_path)
                if dst_pin is not None:
                    color_end = self._pin_colors.resolve(dst_pin.cpp_type).color
        width = 3.0 if is_exec else 1.5
        item = LinkItem(p1, p2, pen_color=color, pen_color_end=color_end,
                        width=width, is_execution=is_exec)
        self.addItem(item)
        self._links.append((item, s_node, s_sub, t_node, t_sub))

    def _relay_position_changed(self, name: str, x: float, y: float) -> None:
        if not self._populating:
            self.node_position_changed.emit(name, x, y)
            self._update_links_for_node(name)

    def _update_links_for_node(self, node_name: str) -> None:
        """드래그 후 해당 노드와 연결된 링크의 bezier path를 재계산한다."""
        for link_item, s_node, s_sub, d_node, d_sub in self._links:
            if s_node == node_name or d_node == node_name:
                src = self._nodes.get(s_node)
                dst = self._nodes.get(d_node)
                if src and dst:
                    p1 = src.pin_anchor(s_sub, "Output")
                    p2 = dst.pin_anchor(d_sub, "Input")
                    link_item.update_endpoints(p1, p2)

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
        for link_item, s_node, _ss, t_node, _ts in self._links:
            src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
            visible = (src is not None and src.isVisible()
                       and dst is not None and dst.isVisible())
            link_item.setVisible(visible)
