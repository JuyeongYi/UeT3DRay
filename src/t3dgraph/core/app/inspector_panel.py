"""속성 인스펙터 — 선택 노드의 핀·기본값·연결됨·변경됨."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView,
)
from ..base.graph_model import GraphModel, Node, Pin
from .pin_status import is_changed_from_default
from .navigable_panel import NavigablePanel

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


class InspectorPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._title = QLabel("(노드를 선택하세요)")
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["핀", "타입", "방향", "기본값", "상태"])
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        self._col_widths = (140, 160, 70, 120, 90)
        for i, w in enumerate(self._col_widths):
            self._tree.setColumnWidth(i, w)
        self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
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
        header = node.display_name or node.name or "?"
        cls_part = node.cls or "?"
        role_bits = []
        if node.role_category:
            role_bits.append(node.role_category)
        if node.role_summary:
            role_bits.append(node.role_summary)
        role_suffix = f"   ·   역할: {' · '.join(role_bits)}" if role_bits else ""
        self._title.setText(f"{header}  [{cls_part}]{role_suffix}")
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
        texts = [pin.name, pin.cpp_type or "", pin.direction or "",
                 pin.default_value or "", status]
        item = QTreeWidgetItem(texts)
        self._apply_truncation_tooltips(item, texts)
        if is_conn:
            peer = _peer_of(full, graph)
            if peer:
                item.setData(0, _PEER_ROLE, peer)
        parent.addChild(item)
        self._items[full] = item
        for sub in pin.subpins:
            self._add_pin(sub, node_name, f"{path}.{sub.name}", connected, graph, item)

    def _apply_truncation_tooltips(self, item: QTreeWidgetItem, texts: list[str]) -> None:
        """셀 텍스트가 컬럼 폭을 초과하면 ToolTipRole에 풀 텍스트를 박는다."""
        fm = QFontMetrics(self._tree.font())
        for i, text in enumerate(texts):
            if not text:
                continue
            if fm.horizontalAdvance(text) > self._col_widths[i] - 12:
                item.setToolTip(i, text)

    def _on_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        peer = item.data(0, _PEER_ROLE)
        if peer:
            self.navigate_requested.emit(peer)

    def pin_count(self) -> int:
        return len(self._items)

    def is_pin_connected(self, full_path: str) -> bool:
        item = self._items.get(full_path)
        return item is not None and "연결됨" in item.text(4)

    def is_pin_changed(self, full_path: str) -> bool:
        item = self._items.get(full_path)
        return item is not None and "변경됨" in item.text(4)

    def activate_pin(self, full_path: str) -> None:
        item = self._items.get(full_path)
        if item is not None:
            self._on_activated(item, 0)
