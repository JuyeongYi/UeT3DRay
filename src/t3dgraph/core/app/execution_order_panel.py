"""분석 도크 — 실행 순서 코드 뷰."""
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from ..analysis.execution_order import ExecutionStep

_NODE_ROLE = Qt.UserRole + 1
_INDENT = "    "


class ExecutionOrderPanel(QWidget):
    navigate_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setFont(QFont("Consolas"))
        layout.addWidget(self._list)
        self._list.itemActivated.connect(self._on_activated)
        self._rows: dict[str, QListWidgetItem] = {}

    def show_order(self, steps: list[ExecutionStep]) -> None:
        self._list.clear()
        self._rows = {}
        for step in steps:
            item = QListWidgetItem(_INDENT * step.depth + step.node)
            item.setData(_NODE_ROLE, step.node)
            self._list.addItem(item)
            self._rows[step.node] = item

    def _on_activated(self, item: QListWidgetItem) -> None:
        node = item.data(_NODE_ROLE)
        if node:
            self.navigate_requested.emit(node)

    def step_count(self) -> int:
        return self._list.count()

    def row_text(self, row: int) -> str:
        return self._list.item(row).text()

    def activate_row(self, row: int) -> None:
        self._on_activated(self._list.item(row))

    def highlight_node(self, node: str | None) -> None:
        item = self._rows.get(node) if node else None
        if item is not None:
            self._list.setCurrentItem(item)
        else:
            self._list.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._list.currentItem()
        return item.data(_NODE_ROLE) if item is not None else None
