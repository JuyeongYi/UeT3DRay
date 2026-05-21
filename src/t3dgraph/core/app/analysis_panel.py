"""분석 도크 — fan-in 수렴점 목록."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from ..analysis.flow import FlowResult
from .navigable_panel import NavigablePanel

_NODE_ROLE = Qt.UserRole + 1


class AnalysisPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._summary = QLabel("(그래프를 열어주세요)")
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["수렴점 / 상세"])
        layout.addWidget(self._summary)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        self._rows: dict[str, QTreeWidgetItem] = {}

    def show_flow(self, flow: FlowResult) -> None:
        self._tree.clear()
        self._rows = {}
        cps = flow.convergence_points
        if not cps:
            self._summary.setText("실행 수렴점(fan-in) 없음 — 선형 실행 흐름")
            return
        self._summary.setText(f"실행 수렴점 {len(cps)}개")
        for node in cps:
            conv = flow.convergence(node)
            top = QTreeWidgetItem([node])
            top.setData(0, _NODE_ROLE, node)
            top.addChild(QTreeWidgetItem([f"유입 경로: {', '.join(conv.incoming_nodes)}"]))
            down = ", ".join(conv.common_downstream) or "(없음)"
            top.addChild(QTreeWidgetItem([f"공통 다운스트림: {down}"]))
            self._tree.addTopLevelItem(top)
            self._rows[node] = top

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        node = item.data(0, _NODE_ROLE)
        if node:
            self.navigate_requested.emit(node)

    def summary_text(self) -> str:
        return self._summary.text()

    def convergence_count(self) -> int:
        return len(self._rows)

    def has_convergence(self, node: str) -> bool:
        return node in self._rows

    def activate_convergence(self, node: str) -> None:
        item = self._rows.get(node)
        if item is not None:
            self._on_activated(item, 0)

    def _lookup_item(self, name: str):
        return self._rows.get(name)

    def _clear_highlight(self) -> None:
        self._tree.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._tree.currentItem()
        return item.data(0, _NODE_ROLE) if item is not None else None
