"""QGraphicsView — 팬·줌 가능한 그래프 캔버스."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QMouseEvent
from PySide6.QtWidgets import QGraphicsView


class GraphView(QGraphicsView):
    _ZOOM_STEP = 1.15

    def __init__(self) -> None:
        super().__init__()
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._panning = False
        self._pan_anchor = None
        self._previous_drag_mode = QGraphicsView.RubberBandDrag

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_anchor = event.position().toPoint()
            self._previous_drag_mode = self.dragMode()
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning and self._pan_anchor is not None:
            pos = event.position().toPoint()
            delta = pos - self._pan_anchor
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self._pan_anchor = pos
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self._pan_anchor = None
            self.setDragMode(self._previous_drag_mode)
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        factor = self._ZOOM_STEP if event.angleDelta().y() > 0 else 1 / self._ZOOM_STEP
        self.scale(factor, factor)

    def fit(self) -> None:
        """씬 전체가 보이도록 맞춘다."""
        if self.scene() is not None and self.scene().items():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
