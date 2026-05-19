"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from ..analysis.flow import FlowResult
from .items import NodeItem, LinkItem
from .view_state import ViewState


def _seg(pin_path: str, index: int) -> str:
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


def _type_suffix(cls: str | None) -> str:
    return (cls or "?").rsplit(".", 1)[-1]


class GraphScene(QGraphicsScene):
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

        for node in graph.nodes:
            item = NodeItem(
                node,
                connected_paths=frozenset(connected.get(node.name, set())),
                connected_only=vs.connected_pins_only,
                show_subpins=vs.expand_subpins,
                highlighted=vs.fan_in_highlight and node.name in convergence,
            )
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
                out.setdefault(_seg(path, 0), set()).add(path)
        return out

    def _add_link(self, link: Link) -> None:
        s_node, t_node = _seg(link.source_path, 0), _seg(link.target_path, 0)
        src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
        if src is None or dst is None:
            return
        p1 = src.pin_anchor(_seg(link.source_path, 1), "Output")
        p2 = dst.pin_anchor(_seg(link.target_path, 1), "Input")
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

    def apply_hidden_types(self, hidden_types: set[str]) -> None:
        for item in self._nodes.values():
            item.setVisible(_type_suffix(item.node.cls) not in hidden_types)
        for link_item, s_node, t_node in self._links:
            src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
            visible = (src is not None and src.isVisible()
                       and dst is not None and dst.isVisible())
            link_item.setVisible(visible)
