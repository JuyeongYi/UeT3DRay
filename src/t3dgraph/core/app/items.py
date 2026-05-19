"""QGraphicsItem 기반 노드/핀/링크 렌더링 요소."""
from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsLineItem,
)
from ..base.graph_model import Node, Pin

NODE_WIDTH = 200.0
ROW_HEIGHT = 20.0
HEADER_HEIGHT = 26.0
PIN_RADIUS = 4.0


class NodeItem(QGraphicsRectItem):
    """노드 1개 — 헤더 텍스트 + 핀 행 목록. 데이터 Position에 배치."""

    def __init__(self, node: Node):
        self.node = node
        pin_count = max(len(node.pins), 1)
        height = HEADER_HEIGHT + pin_count * ROW_HEIGHT
        super().__init__(QRectF(0, 0, NODE_WIDTH, height))
        x, y = node.position if node.position else (0.0, 0.0)
        self.setPos(x, y)
        self.setPen(QPen(QColor(40, 40, 40)))
        self.setBrush(QBrush(QColor(70, 70, 80) if not node.is_generic
                              else QColor(90, 60, 60)))
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

        title = QGraphicsSimpleTextItem(node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)

        self._rows: dict[str, float] = {}
        for i, pin in enumerate(node.pins):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[pin.name] = cy
            is_input = (pin.direction or "").lower() != "output"
            mx = 0.0 if is_input else NODE_WIDTH
            dot = QGraphicsEllipseItem(
                mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
            dot.setBrush(QBrush(QColor(200, 200, 120)))
            dot.setPen(QPen(Qt.NoPen))
            label = QGraphicsSimpleTextItem(pin.name, self)
            label.setBrush(QBrush(QColor(210, 210, 210)))
            lx = 8 if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
            label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)

    def pin_anchor(self, pin_name: str, direction: str) -> QPointF:
        """핀의 씬 좌표 앵커. 알 수 없는 핀은 노드 중앙으로 폴백."""
        cy = self._rows.get(pin_name)
        if cy is None:
            return self.mapToScene(QPointF(NODE_WIDTH / 2, self.rect().height() / 2))
        lx = NODE_WIDTH if (direction or "").lower() == "output" else 0.0
        return self.mapToScene(QPointF(lx, cy))


class LinkItem(QGraphicsLineItem):
    """두 핀 앵커를 잇는 선."""

    def __init__(self, p1: QPointF, p2: QPointF):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y())
        self.setPen(QPen(QColor(170, 170, 170), 1.5))
        self.setZValue(-1)
