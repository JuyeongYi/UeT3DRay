"""QGraphicsItem 기반 노드/핀/링크 렌더링 요소."""
from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsItem,
)
from ..base.graph_model import Node, Pin

NODE_WIDTH = 200.0
ROW_HEIGHT = 20.0
HEADER_HEIGHT = 26.0
PIN_RADIUS = 4.0


class NodeItem(QGraphicsRectItem):
    """노드 1개 — 헤더 + 핀 행. 렌더 옵션으로 필터·서브핀·강조 제어."""

    def __init__(
        self, node: Node, *,
        connected_paths: frozenset[str] = frozenset(),
        connected_only: bool = False,
        show_subpins: bool = False,
        highlighted: bool = False,
    ):
        self.node = node
        rows = self._collect_rows(node, connected_paths, connected_only, show_subpins)
        height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
        super().__init__(QRectF(0, 0, NODE_WIDTH, height))
        x, y = node.position if node.position else (0.0, 0.0)
        self.setPos(x, y)
        if highlighted:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))
        else:
            self.setPen(QPen(QColor(40, 40, 40)))
        self.setBrush(QBrush(QColor(70, 70, 80) if not node.is_generic
                              else QColor(90, 60, 60)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        title = QGraphicsSimpleTextItem(node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)

        self._rows: dict[str, float] = {}
        for i, (pin, path, depth) in enumerate(rows):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[path] = cy
            is_input = (pin.direction or "").lower() != "output"
            mx = 0.0 if is_input else NODE_WIDTH
            dot = QGraphicsEllipseItem(
                mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
            dot.setBrush(QBrush(QColor(200, 200, 120)))
            dot.setPen(QPen(Qt.NoPen))
            label = QGraphicsSimpleTextItem(pin.name, self)
            label.setBrush(QBrush(QColor(210, 210, 210)))
            indent = 8 + depth * 12
            lx = indent if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
            label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)

    @staticmethod
    def _collect_rows(node: Node, connected_paths: frozenset[str],
                      connected_only: bool, show_subpins: bool) -> list[tuple]:
        rows: list[tuple] = []

        def walk(pin: Pin, path: str, depth: int) -> None:
            if (not connected_only) or (path in connected_paths):
                rows.append((pin, path, depth))
            if show_subpins:
                for sp in pin.subpins:
                    walk(sp, f"{path}.{sp.name}", depth + 1)

        for pin in node.pins:
            walk(pin, f"{node.name}.{pin.name}", 0)
        return rows

    def has_pin_row(self, full_path: str) -> bool:
        return full_path in self._rows

    def pin_anchor(self, pin_subpath: str, direction: str) -> QPointF:
        """핀 앵커. pin_subpath는 노드 이후 경로('Pin' 또는 'Pin.Sub').
        펼쳐진 서브핀 행이 있으면 거기에, 없으면 최상위 핀 행, 그것도 없으면 노드 중앙."""
        full = f"{self.node.name}.{pin_subpath}"
        cy = self._rows.get(full)
        if cy is None:
            top = pin_subpath.split(".", 1)[0]
            cy = self._rows.get(f"{self.node.name}.{top}")
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
