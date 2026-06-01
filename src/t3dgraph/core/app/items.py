"""QGraphicsItem 기반 노드/핀/링크 렌더링 요소."""
from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import QObject, QRectF, QPointF, Qt, Signal
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsItem,
)
from ..base.graph_model import Node, Pin


class _NodeItemBus(QObject):
    """QGraphicsRectItem은 QObject가 아니므로 Signal carrier를 별도 보관."""
    pin_toggle_requested = Signal(str)        # Slice A: 핀 행 토글 (full_path)
    enter_subgraph_requested = Signal(str)    # Slice C: 헤더 더블클릭 (node name)


NODE_WIDTH = 200.0
ROW_HEIGHT = 20.0
HEADER_HEIGHT = 26.0
PIN_RADIUS = 4.0


@dataclass(frozen=True)
class PinRow:
    pin: Pin
    path: str
    depth: int
    has_dot: bool
    has_children: bool = False   # subpins가 비어있지 않으면 True (F12 disclosure 표시)


def collect_pin_rows(
    node: Node,
    *,
    connected_subtree: frozenset[str],
    connected_only: bool,
    expanded: frozenset[str],
) -> list[PinRow]:
    rows: list[PinRow] = []

    def walk(pin: Pin, path: str, depth: int) -> bool:
        include_self = (not connected_only) or (path in connected_subtree)
        my_idx: int | None = None
        if include_self:
            my_idx = len(rows)
            rows.append(PinRow(pin=pin, path=path, depth=depth, has_dot=True,
                               has_children=bool(pin.subpins)))
        children_added = False
        if path in expanded:
            for sp in pin.subpins:
                child_path = f"{path}.{sp.name}"
                if walk(sp, child_path, depth + 1):
                    children_added = True
        if my_idx is not None and children_added:
            cur = rows[my_idx]
            rows[my_idx] = PinRow(pin=cur.pin, path=cur.path,
                                  depth=cur.depth, has_dot=False,
                                  has_children=cur.has_children)
        return include_self or children_added

    for pin in node.pins:
        walk(pin, f"{node.name}.{pin.name}", 0)
    return rows


class NodeItem(QGraphicsRectItem):
    """노드 1개 — 헤더 + 핀 행. 렌더 옵션으로 필터·서브핀·강조 제어."""

    def __init__(
        self, node: Node, *,
        connected_paths: frozenset[str] = frozenset(),
        connected_only: bool = False,
        expanded_paths: frozenset[str] = frozenset(),
        highlighted: bool = False,
    ):
        rows = collect_pin_rows(node, connected_subtree=connected_paths,
                                connected_only=connected_only,
                                expanded=expanded_paths)
        height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
        super().__init__(QRectF(0, 0, NODE_WIDTH, height))
        self.node = node
        needs_bus = node.subgraph is not None or bool(node.pins)
        self._bus: _NodeItemBus | None = _NodeItemBus() if needs_bus else None
        x, y = node.position if node.position else (0.0, 0.0)
        self.setPos(x, y)
        if highlighted:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))
        else:
            self.setPen(QPen(QColor(40, 40, 40)))
        self.setBrush(QBrush(QColor(70, 70, 80) if not node.is_generic
                              else QColor(90, 60, 60)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        title = QGraphicsSimpleTextItem(node.display_name or node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)

        if node.subgraph is not None:
            chev = QGraphicsSimpleTextItem("▶", self)
            chev.setBrush(QBrush(QColor(200, 200, 120)))
            chev.setPos(NODE_WIDTH - 16, 5)
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("더블클릭하여 서브그래프 진입")

        self._rows: dict[str, float] = {}
        self._row_paths: list[str] = [r.path for r in rows]
        for i, row in enumerate(rows):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[row.path] = cy
            is_input = (row.pin.direction or "").lower() != "output"
            mx = 0.0 if is_input else NODE_WIDTH
            if row.has_dot:
                dot = QGraphicsEllipseItem(
                    mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
                dot.setBrush(QBrush(QColor(200, 200, 120)))
                dot.setPen(QPen(Qt.NoPen))
            label = QGraphicsSimpleTextItem(row.pin.name, self)
            label.setBrush(QBrush(QColor(210, 210, 210)))
            indent = 8 + row.depth * 12
            lx = indent if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
            label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)

    @property
    def bus(self) -> _NodeItemBus | None:
        return self._bus

    def toggle_pin_at_row(self, row_index: int) -> None:
        if self._bus is not None and 0 <= row_index < len(self._row_paths):
            self._bus.pin_toggle_requested.emit(self._row_paths[row_index])

    def _try_emit_enter_subgraph(self, y: float) -> bool:
        """헤더 영역에서 subgraph 보유 노드일 때만 enter_subgraph_requested 발사.

        리턴: 발사했으면 True (Qt 이벤트를 accept해야 함), 아니면 False.

        subgraph가 없는 노드는 시그널을 발사하지 않는다 — 수신측 noop이라도
        사용자가 무반응을 인지하기보다 호출 자체가 없는 편이 명확.
        """
        if y < HEADER_HEIGHT and self.node.subgraph is not None and self._bus is not None:
            self._bus.enter_subgraph_requested.emit(self.node.name)
            return True
        return False

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt override)
        y = event.pos().y()
        # 헤더 영역 (subgraph 보유) 더블클릭 → 서브그래프 진입 (Slice C, F5/F6, M3 가드)
        if self._try_emit_enter_subgraph(y):
            event.accept()
            return
        # 행 영역 더블클릭 → 핀 expand 토글 (Slice A, F9)
        row = int((y - HEADER_HEIGHT) / ROW_HEIGHT)
        if 0 <= row < len(self._row_paths):
            self.toggle_pin_at_row(row)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _emit_enter_subgraph_for_test(self) -> None:
        """테스트 전용 — 헤더 더블클릭 시그널 직접 발사."""
        if self._bus is not None and self.node.subgraph is not None:
            self._bus.enter_subgraph_requested.emit(self.node.name)

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


    def set_highlighted(self, on: bool) -> None:
        if on:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))
        else:
            self.setPen(QPen(QColor(40, 40, 40)))


class LinkItem(QGraphicsLineItem):
    """두 핀 앵커를 잇는 선."""

    def __init__(self, p1: QPointF, p2: QPointF):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y())
        self.setPen(QPen(QColor(170, 170, 170), 1.5))
        self.setZValue(-1)
