"""노드 타입 필터 — 타입별 체크박스."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from ..base.graph_model import GraphModel
from ..t3d.paths import type_suffix


class NodeFilterPanel(QWidget):
    type_toggled = Signal(str, bool)

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.addStretch(1)
        self._boxes: dict[str, QCheckBox] = {}

    def set_graph(self, graph: GraphModel) -> None:
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

    def type_names(self) -> list[str]:
        return list(self._boxes.keys())

    def is_checked(self, type_name: str) -> bool:
        box = self._boxes.get(type_name)
        return box is not None and box.isChecked()

    def set_checked(self, type_name: str, checked: bool) -> None:
        box = self._boxes.get(type_name)
        if box is not None:
            box.setChecked(checked)
