"""분석 도크 — 실행 순서 코드 뷰."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QVBoxLayout, QListWidget, QListWidgetItem
from ..analysis.execution_order import ExecutionStep
from .navigable_panel import NavigablePanel

_NODE_ROLE = Qt.UserRole + 1
_INDENT = "    "


def _format_step(step) -> str:
    indent = _INDENT * step.depth
    if step.kind == "loop":
        return f"{indent}ForEach {step.node}:"
    if step.kind == "sequence":
        return f"{indent}Sequence {step.node}:"
    if step.kind == "function":
        return f"{indent}{step.node}() {{ … }}"
    return f"{indent}{step.node}"


class ExecutionOrderPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self._list)
        self._list.itemActivated.connect(self._on_activated)
        self._rows: dict[str, QListWidgetItem] = {}

    def show_order(self, steps: list[ExecutionStep]) -> None:
        self._list.clear()
        self._rows = {}
        for step in steps:
            item = QListWidgetItem(_format_step(step))
            item.setData(_NODE_ROLE, step.node)
            self._list.addItem(item)
            self._rows[step.node] = item

    def _on_activated(self, item: QListWidgetItem) -> None:
        node = item.data(_NODE_ROLE)
        if node:
            self.navigate_requested.emit(node)

    def list_font(self):
        return self._list.font()

    def step_count(self) -> int:
        return self._list.count()

    def row_text(self, row: int) -> str:
        return self._list.item(row).text()

    def activate_row(self, row: int) -> None:
        self._on_activated(self._list.item(row))

    def _lookup_item(self, name: str):
        return self._rows.get(name)

    def _clear_highlight(self) -> None:
        self._list.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._list.currentItem()
        return item.data(_NODE_ROLE) if item is not None else None
