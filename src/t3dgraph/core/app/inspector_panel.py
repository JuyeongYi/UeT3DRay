"""속성 인스펙터 — 선택 노드의 핀·기본값·연결됨·변경됨."""
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from ..base.graph_model import GraphModel, Node, Pin
from .pin_status import is_changed_from_default

_PEER_ROLE = Qt.UserRole + 1


def _connected_pin_paths(graph: GraphModel) -> set[str]:
    paths: set[str] = set()
    for link in graph.links:
        paths.add(link.source_path)
        paths.add(link.target_path)
    return paths


def _peer_of(path: str, graph: GraphModel) -> str | None:
    for link in graph.links:
        if link.source_path == path:
            return link.target_path.split(".", 1)[0]
        if link.target_path == path:
            return link.source_path.split(".", 1)[0]
    return None


class InspectorPanel(QWidget):
    navigate_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._title = QLabel("(노드를 선택하세요)")
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["핀", "타입", "방향", "기본값", "상태"])
        layout.addWidget(self._title)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        self._items: dict[str, QTreeWidgetItem] = {}

    def show_node(self, node: Node | None, graph: GraphModel) -> None:
        self._tree.clear()
        self._items = {}
        if node is None:
            self._title.setText("(노드를 선택하세요)")
            return
        self._title.setText(f"{node.name}  [{node.cls or '?'}]")
        connected = _connected_pin_paths(graph)
        for pin in node.pins:
            self._add_pin(pin, node.name, pin.name, connected, graph, self._tree.invisibleRootItem())

    def _add_pin(self, pin: Pin, node_name: str, path: str,
                 connected: set[str], graph: GraphModel, parent: QTreeWidgetItem) -> None:
        full = f"{node_name}.{path}"
        is_conn = full in connected
        is_chg = is_changed_from_default(pin)
        status = " · ".join(
            s for s in ("연결됨" if is_conn else "", "변경됨(추정)" if is_chg else "") if s)
        item = QTreeWidgetItem(
            [pin.name, pin.cpp_type or "", pin.direction or "",
             pin.default_value or "", status])
        if is_conn:
            peer = _peer_of(full, graph)
            if peer:
                item.setData(0, _PEER_ROLE, peer)
        parent.addChild(item)
        self._items[pin.name] = item
        for sub in pin.subpins:
            self._add_pin(sub, node_name, f"{path}.{sub.name}", connected, graph, item)

    def _on_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        peer = item.data(0, _PEER_ROLE)
        if peer:
            self.navigate_requested.emit(peer)

    def pin_count(self) -> int:
        return len(self._items)

    def is_pin_connected(self, pin_name: str) -> bool:
        item = self._items.get(pin_name)
        return item is not None and "연결됨" in item.text(4)

    def is_pin_changed(self, pin_name: str) -> bool:
        item = self._items.get(pin_name)
        return item is not None and "변경됨" in item.text(4)

    def activate_pin(self, pin_name: str) -> None:
        item = self._items.get(pin_name)
        if item is not None:
            self._on_activated(item, 0)
