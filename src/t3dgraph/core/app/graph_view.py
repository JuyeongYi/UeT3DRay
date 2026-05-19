"""QGraphicsView — 팬·줌 가능한 그래프 캔버스."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView


class GraphView(QGraphicsView):
    _ZOOM_STEP = 1.15

    def __init__(self) -> None:
        super().__init__()
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event) -> None:
        factor = self._ZOOM_STEP if event.angleDelta().y() > 0 else 1 / self._ZOOM_STEP
        self.scale(factor, factor)

    def fit(self) -> None:
        """씬 전체가 보이도록 맞춘다."""
        if self.scene() is not None and self.scene().items():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
