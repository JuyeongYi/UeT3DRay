"""브레드크럼 바 — 그래프 스택 진입 경로 표시 (F5)."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class BreadcrumbBar(QWidget):
    segment_clicked = Signal(int)              # 클릭한 세그먼트 인덱스

    def __init__(self) -> None:
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._buttons: list[QPushButton] = []

    def set_segments(self, labels: list[str]) -> None:
        # 기존 위젯 모두 제거 (버튼/분리기/stretch 포함)
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._buttons = []

        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.clicked.connect(lambda _checked=False, idx=i: self.segment_clicked.emit(idx))
            self._layout.addWidget(btn)
            self._buttons.append(btn)
            if i < len(labels) - 1:
                self._layout.addWidget(QLabel(">"))
        self._layout.addStretch(1)

    def segment_labels(self) -> list[str]:
        return [b.text() for b in self._buttons]

    def click_segment(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].click()
