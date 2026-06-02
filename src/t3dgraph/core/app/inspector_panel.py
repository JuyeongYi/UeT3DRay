"""속성 인스펙터 — 선택 노드의 핀·기본값·연결됨·변경됨."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView, QSizePolicy,
)
from ..base.graph_model import GraphModel, Node, Pin
from .pin_status import is_changed_from_default
from .navigable_panel import NavigablePanel
from .scene import _changed_paths_by_node, _connected_paths_by_node

_PEER_ROLE = Qt.UserRole + 1


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
        self._title.setWordWrap(False)
        self._title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        fm = QFontMetrics(self._title.font())
        self._title.setMaximumHeight(fm.lineSpacing() + 4)
        self._title_raw_text: str = "(노드를 선택하세요)"
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
        header.sectionResized.connect(self._on_section_resized)
        self._items: dict[str, QTreeWidgetItem] = {}

    def show_node(self, node: Node | None, graph: GraphModel,
                  *,
                  changed_paths: set[str] | None = None,
                  connected_paths: set[str] | None = None) -> None:
        self._tree.clear()
        self._items = {}
        if node is None:
            self._set_title("(노드를 선택하세요)")
            return
        header = node.display_name or node.name or "?"
        cls_part = node.cls or "?"
        role_bits = []
        if node.role_category:
            role_bits.append(node.role_category)
        if node.role_summary:
            role_bits.append(node.role_summary)
        role_suffix = f"   ·   역할: {' · '.join(role_bits)}" if role_bits else ""
        self._set_title(f"{header}  [{cls_part}]{role_suffix}")
        # 단일 진실원 — 외부에서 받으면 그대로, 아니면 모듈 함수로 계산
        if changed_paths is None:
            changed_paths = _changed_paths_by_node(graph).get(node.name, set())
        if connected_paths is None:
            connected_paths = _connected_paths_by_node(graph).get(node.name, set())
        for pin in node.pins:
            self._add_pin(pin, node.name, pin.name,
                          changed_paths, connected_paths, graph,
                          self._tree.invisibleRootItem())

    def _set_title(self, raw_text: str) -> None:
        self._title_raw_text = raw_text
        self._apply_title_elide()

    def _apply_title_elide(self) -> None:
        fm = QFontMetrics(self._title.font())
        available = max(self._title.width() - 12, 100)
        elided = fm.elidedText(self._title_raw_text, Qt.ElideRight, available)
        self._title.setText(elided)
        self._title.setToolTip(self._title_raw_text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_title_elide()

    def _add_pin(self, pin: Pin, node_name: str, path: str,
                 changed_paths: set[str], connected_paths: set[str],
                 graph: GraphModel, parent: QTreeWidgetItem) -> None:
        full = f"{node_name}.{path}"
        # is_in_conn is True for ancestor prefixes too — _is_self_target disambiguates direct endpoint vs descendant
        is_self_conn = self._is_self_target(full, graph)
        is_self_chg = (full in changed_paths) and is_changed_from_default(pin)
        # descendant check: any direct child path present in set (sets include prefix closure)
        has_desc_conn = any(f"{full}.{sp.name}" in connected_paths for sp in pin.subpins)
        has_desc_chg = any(f"{full}.{sp.name}" in changed_paths for sp in pin.subpins)
        status_parts = []
        if is_self_conn and has_desc_conn:
            status_parts.append("연결됨 (원소 포함)")
        elif is_self_conn:
            status_parts.append("연결됨")
        elif has_desc_conn:
            status_parts.append("원소 연결됨")
        if is_self_chg and has_desc_chg:
            status_parts.append("변경됨(추정) (원소 포함)")
        elif is_self_chg:
            status_parts.append("변경됨(추정)")
        elif has_desc_chg:
            status_parts.append("원소 변경됨")
        status = " · ".join(status_parts)
        default_text = pin.default_value or ""
        if pin.variable_source:
            if default_text:
                default_text = f"← var: {pin.variable_source} ({default_text})"
            else:
                default_text = f"← var: {pin.variable_source}"
        texts = [pin.name, pin.cpp_type or "", pin.direction or "",
                 default_text, status]
        item = QTreeWidgetItem(texts)
        self._apply_truncation_tooltips(item, texts)
        if is_self_conn:
            peer = _peer_of(full, graph)
            if peer:
                item.setData(0, _PEER_ROLE, peer)
        parent.addChild(item)
        self._items[full] = item
        for sub in pin.subpins:
            self._add_pin(sub, node_name, f"{path}.{sub.name}",
                          changed_paths, connected_paths, graph, item)

    @staticmethod
    def _is_self_target(full: str, graph: GraphModel) -> bool:
        for link in graph.links:
            if link.source_path == full or link.target_path == full:
                return True
        return False

    _CELL_PAD_PX = 12  # 셀 좌우 패딩 추정치

    def _apply_truncation_tooltips(self, item: QTreeWidgetItem, texts: list[str]) -> None:
        """셀 텍스트가 라이브 컬럼 폭을 초과하면 ToolTipRole에 풀 텍스트를 박는다.

        `self._tree.columnWidth(i)` 로 현재 폭을 읽어 Interactive resize 반영.
        미초과 컬럼은 빈 문자열로 명시 초기화(item 재사용 대비 idempotent).
        """
        fm = QFontMetrics(self._tree.font())
        for i, text in enumerate(texts):
            live_w = self._tree.columnWidth(i)
            if text and fm.horizontalAdvance(text) > live_w - self._CELL_PAD_PX:
                item.setToolTip(i, text)
            else:
                item.setToolTip(i, "")

    def _on_section_resized(self, _logical: int, _old: int, _new: int) -> None:
        """컬럼 폭 변경 시 모든 item 툴팁 재평가."""
        for item in self._items.values():
            texts = [item.text(i) for i in range(self._tree.columnCount())]
            self._apply_truncation_tooltips(item, texts)

    def _on_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        peer = item.data(0, _PEER_ROLE)
        if peer:
            self.navigate_requested.emit(peer)

    def show_multi_selection(self, count: int) -> None:
        """N개 선택 시 타이틀만 표시, tree clear."""
        self._tree.clear()
        self._items = {}
        self._set_title(f"(다중 선택 — {count}개 노드)")

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
