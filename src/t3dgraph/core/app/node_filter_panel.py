"""노드 타입 필터 — 타입별 체크박스 + 이름/표시명 검색."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QLineEdit
from ..base.graph_model import GraphModel
from ..base.paths import type_suffix


class NodeFilterPanel(QWidget):
    type_toggled = Signal(str, bool)
    search_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("이름/표시명 검색…")
        self._search.textChanged.connect(lambda _: self.search_changed.emit())
        self._layout.addWidget(self._search)
        self._layout.addStretch(1)
        self._boxes: dict[str, QCheckBox] = {}
        self._graph: GraphModel | None = None

    def set_graph(self, graph: GraphModel) -> None:
        self._graph = graph
        for box in self._boxes.values():
            box.setParent(None)
        self._boxes = {}
        for type_name in sorted({type_suffix(n.cls) for n in graph.nodes}):
            box = QCheckBox(type_name)
            box.setChecked(True)
            box.toggled.connect(
                lambda checked, t=type_name: self.type_toggled.emit(t, not checked))
            self._layout.insertWidget(self._layout.count() - 1, box)
            self._boxes[type_name] = box

    def set_search_text(self, text: str) -> None:
        self._search.setText(text)

    def matched_node_names(self) -> set[str]:
        if self._graph is None:
            return set()
        q = self._search.text().strip().lower()
        if not q:
            return {n.name for n in self._graph.nodes}
        out: set[str] = set()
        for n in self._graph.nodes:
            if q in (n.name or "").lower():
                out.add(n.name)
            elif n.display_name and q in n.display_name.lower():
                out.add(n.name)
        return out

    def type_names(self) -> list[str]:
        return list(self._boxes.keys())

    def is_checked(self, type_name: str) -> bool:
        box = self._boxes.get(type_name)
        return box is not None and box.isChecked()

    def set_checked(self, type_name: str, checked: bool) -> None:
        box = self._boxes.get(type_name)
        if box is not None:
            box.setChecked(checked)
