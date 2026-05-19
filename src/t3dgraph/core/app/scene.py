"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from .items import NodeItem, LinkItem


def _seg(pin_path: str, index: int) -> str:
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


class GraphScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._nodes: dict[str, NodeItem] = {}

    def node_item(self, name: str) -> NodeItem | None:
        return self._nodes.get(name)

    def populate(self, graph: GraphModel) -> None:
        self.clear()
        self._nodes = {}
        for node in graph.nodes:
            item = NodeItem(node)
            self.addItem(item)
            self._nodes[node.name] = item
        for link in graph.links:
            self._add_link(link)

    def _add_link(self, link: Link) -> None:
        src = self._nodes.get(_seg(link.source_path, 0))
        dst = self._nodes.get(_seg(link.target_path, 0))
        if src is None or dst is None:
            return
        p1 = src.pin_anchor(_seg(link.source_path, 1), "Output")
        p2 = dst.pin_anchor(_seg(link.target_path, 1), "Input")
        self.addItem(LinkItem(p1, p2))
