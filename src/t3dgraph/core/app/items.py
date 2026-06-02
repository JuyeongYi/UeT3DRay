"""QGraphicsItem 기반 노드/핀/링크 렌더링 요소."""
from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import QObject, QRectF, QPointF, Qt, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath, QLinearGradient, QPolygonF, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsItem,
)
from ..base.graph_model import Node, Pin
from .node_profiles import NodeStyleProfile
from .pin_colors import PinColorTable


class _NodeItemBus(QObject):
    """QGraphicsRectItem은 QObject가 아니므로 Signal carrier를 별도 보관."""
    pin_toggle_requested = Signal(str)        # 핀 행 토글 (full_path)
    enter_subgraph_requested = Signal(str)    # 헤더 더블클릭 (node name)
    position_changed = Signal(str, float, float)   # F18 (node_name, x, y)
    context_menu_requested = Signal(str, object)   # F19 (node_name, QPoint)


MIN_NODE_WIDTH = 200.0
MAX_NODE_WIDTH = 400.0
NODE_HORIZONTAL_PADDING = 24.0
NODE_WIDTH = MIN_NODE_WIDTH   # legacy alias
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
    effective_direction: str = ""   # 정규화된 방향 ("input"/"output"/"io"/"hidden"/"")


def _normalize_direction(raw: str | None) -> str:
    return (raw or "").strip().lower()


def collect_pin_rows(
    node: Node,
    *,
    connected_subtree: frozenset[str],
    changed_pins: frozenset[str] = frozenset(),
    connected_only: bool,
    expanded: frozenset[str],
) -> list[PinRow]:
    rows: list[PinRow] = []

    def walk(pin: Pin, path: str, depth: int, parent_dir: str) -> bool:
        my_dir = _normalize_direction(pin.direction)
        if not my_dir:
            my_dir = parent_dir
        include_self = (not connected_only) or (path in connected_subtree) or (path in changed_pins)
        my_idx: int | None = None
        if include_self:
            my_idx = len(rows)
            rows.append(PinRow(pin=pin, path=path, depth=depth, has_dot=True,
                               has_children=bool(pin.subpins),
                               effective_direction=my_dir))
        children_added = False
        if path in expanded:
            for sp in pin.subpins:
                child_path = f"{path}.{sp.name}"
                if walk(sp, child_path, depth + 1, my_dir):
                    children_added = True
        if my_idx is not None and children_added:
            cur = rows[my_idx]
            rows[my_idx] = PinRow(pin=cur.pin, path=cur.path,
                                  depth=cur.depth, has_dot=False,
                                  has_children=cur.has_children,
                                  effective_direction=cur.effective_direction)
        return include_self or children_added

    for pin in node.pins:
        walk(pin, f"{node.name}.{pin.name}", 0, "")
    return rows


class NodeItem(QGraphicsRectItem):
    """노드 1개 — 헤더 + 핀 행. 렌더 옵션으로 필터·서브핀·강조 제어."""

    def __init__(
        self, node: Node, *,
        connected_paths: frozenset[str] = frozenset(),
        changed_paths: frozenset[str] = frozenset(),
        connected_only: bool = False,
        expanded_paths: frozenset[str] = frozenset(),
        highlighted: bool = False,
        pin_colors: "PinColorTable | None" = None,
        profile: "NodeStyleProfile | None" = None,
    ):
        self._profile: NodeStyleProfile = profile if profile is not None else NodeStyleProfile()
        # w1-C: 인스턴스 상태 보존 — set_expanded_paths() 에서 재사용
        self._connected_paths = connected_paths
        self._changed_paths = changed_paths
        self._connected_only = connected_only
        self._expanded_paths = expanded_paths
        self._pin_colors = pin_colors
        rows = collect_pin_rows(node, connected_subtree=connected_paths,
                                changed_pins=changed_paths,
                                connected_only=connected_only,
                                expanded=expanded_paths)
        self._node_width = self._compute_width(node, rows)
        if self._profile.layout_hint == "passthrough":
            height = HEADER_HEIGHT + ROW_HEIGHT
        else:
            height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
        super().__init__(QRectF(0, 0, self._node_width, height))
        self.node = node
        self._bus: _NodeItemBus = _NodeItemBus()
        x, y = node.position if node.position else (0.0, 0.0)
        self.setPos(x, y)
        if highlighted:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))
        else:
            self.setPen(QPen(QColor(40, 40, 40)))
        self.setBrush(QBrush(QColor(70, 70, 80) if not node.is_generic
                              else QColor(90, 60, 60)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)              # F18
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        title = QGraphicsSimpleTextItem(node.display_name or node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)

        _state = self._function_entry_state()
        if _state in ("subgraph", "funcref"):
            chev = QGraphicsSimpleTextItem("▶", self)
            if _state == "subgraph":
                chev.setBrush(QBrush(QColor("#4CAF50")))
            else:
                chev.setBrush(QBrush(QColor("#FFC107")))
            chev.setPos(self._node_width - 16, 5)
            self.setCursor(Qt.PointingHandCursor)
            tooltip = (self._profile.tooltip_when_no_subgraph
                       if _state == "funcref" and self._profile.tooltip_when_no_subgraph
                       else "더블클릭하여 서브그래프 진입")
            self.setToolTip(tooltip)

        # F16: 변수 노드 헤더 우측에 'var' 배지
        if self._profile.show_var_badge:
            var_color = QColor("#9966FF")
            if pin_colors is not None:
                var_color = pin_colors._palette.get("variable", var_color)
            badge_w, badge_h = 24.0, 14.0
            badge_x = self._node_width - badge_w - 6
            badge_y = (HEADER_HEIGHT - badge_h) / 2
            badge_bg = QGraphicsRectItem(badge_x, badge_y, badge_w, badge_h, self)
            badge_bg.setBrush(QBrush(var_color))
            badge_bg.setPen(QPen(Qt.NoPen))
            badge_text = QGraphicsSimpleTextItem("var", self)
            badge_text.setBrush(QBrush(QColor(255, 255, 255)))
            badge_text.setPos(badge_x + 5, badge_y + 1)

        self._rows: dict[str, float] = {}
        self._row_paths: list[str] = [r.path for r in rows]
        self._arrow_zones: dict[str, tuple[float, float, float]] = {}  # path -> (x0, x1, cy)
        self._row_children: list = []
        self._install_rows(rows)

    @staticmethod
    def _compute_width(node: "Node", rows: "list[PinRow]") -> float:
        """타이틀·핀 라벨 폭 기반 노드 폭 계산 (MIN_NODE_WIDTH ~ MAX_NODE_WIDTH)."""
        fm = QFontMetrics(QFont())
        title_text = node.display_name or node.name or "?"
        title_w = fm.horizontalAdvance(title_text) + 40.0
        pin_w = MIN_NODE_WIDTH
        for row in rows:
            label_text = row.pin.name
            if row.pin.variable_source:
                label_text = f"{row.pin.name} (var: {row.pin.variable_source})"
            lw = fm.horizontalAdvance(label_text)
            per_side = lw + 30 + row.depth * 12
            pin_w = max(pin_w, per_side * 2 + NODE_HORIZONTAL_PADDING)
        return min(max(MIN_NODE_WIDTH, title_w, pin_w), MAX_NODE_WIDTH)

    _FUNCREF_CLS_SUFFIX = "RigVMFunctionReferenceNode"

    def _function_entry_state(self) -> str:
        """chevron 색 결정용 상태 분류.

        Returns:
            "subgraph"  — subgraph 보유 (초록 chevron)
            "funcref"   — chevron_state_aware이지만 subgraph 없음 (노랑 chevron)
            "none"      — 해당 없음 (chevron 표시 안 함)
        """
        if not self._profile.always_show_chevron:
            return "none"
        if self.node.subgraph is not None:
            return "subgraph"
        if self._profile.chevron_state_aware:
            return "funcref"
        return "subgraph"  # always_show_chevron but not state_aware → 항상 초록

    @property
    def bus(self) -> _NodeItemBus:
        return self._bus

    def toggle_pin_at_row(self, row_index: int) -> None:
        if 0 <= row_index < len(self._row_paths):
            self._bus.pin_toggle_requested.emit(self._row_paths[row_index])

    def _try_emit_enter_subgraph(self, y: float) -> bool:
        """헤더 영역에서 subgraph 보유 노드일 때만 enter_subgraph_requested 발사.

        리턴: 발사했으면 True (Qt 이벤트를 accept해야 함), 아니면 False.

        subgraph가 없는 노드는 시그널을 발사하지 않는다 — 수신측 noop이라도
        사용자가 무반응을 인지하기보다 호출 자체가 없는 편이 명확.
        """
        if y < HEADER_HEIGHT and self.node.subgraph is not None:
            self._bus.enter_subgraph_requested.emit(self.node.name)
            return True
        return False

    def toggle_at_pos(self, pos: QPointF) -> bool:
        """화살표 zone 좌표에 있으면 토글 발사. 발사 여부 반환."""
        for path, (x0, x1, cy) in self._arrow_zones.items():
            if x0 <= pos.x() <= x1 and abs(pos.y() - cy) <= ROW_HEIGHT / 2:
                self._bus.pin_toggle_requested.emit(path)
                return True
        return False

    def itemChange(self, change, value):  # noqa: N802 (Qt override)
        if change == QGraphicsItem.ItemPositionHasChanged:
            p = self.pos()
            self._bus.position_changed.emit(self.node.name, p.x(), p.y())
        return super().itemChange(change, value)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._bus.context_menu_requested.emit(self.node.name, event.screenPos())
        event.accept()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.toggle_at_pos(event.pos()):
            event.accept()
            return
        super().mousePressEvent(event)

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
        if self.node.subgraph is not None:
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
            return self.mapToScene(QPointF(self._node_width / 2, self.rect().height() / 2))
        lx = self._node_width if (direction or "").lower() == "output" else 0.0
        return self.mapToScene(QPointF(lx, cy))


    def _install_rows(self, rows: "list[PinRow]") -> None:
        for i, row in enumerate(rows):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[row.path] = cy
            direction = row.effective_direction
            is_hidden = direction == "hidden"
            is_io = direction == "io"
            is_output = direction == "output"
            _hint = self._profile.layout_hint
            if _hint == "outputs_only":
                is_input_side = False
            elif _hint == "inputs_only":
                is_input_side = True
            else:
                is_input_side = not is_output and not is_io
            label_color = QColor(150, 150, 150) if is_hidden else QColor(210, 210, 210)
            dot_r = 6.0 if row.pin.is_execution else PIN_RADIUS
            if row.has_dot and not is_hidden:
                def _make_dot(mx: float, _row=row, _r=dot_r, _cy=cy) -> QGraphicsEllipseItem:
                    dot = QGraphicsEllipseItem(mx - _r, _cy - _r, 2 * _r, 2 * _r, self)
                    if self._pin_colors is not None:
                        resolved = self._pin_colors.resolve(_row.pin.cpp_type)
                        dot.setBrush(QBrush(resolved.color))
                        if resolved.is_array:
                            dot.setPen(QPen(QColor(40, 40, 40), 1.5))
                        else:
                            dot.setPen(QPen(Qt.NoPen))
                    else:
                        dot.setBrush(QBrush(QColor(200, 200, 120)))
                        dot.setPen(QPen(Qt.NoPen))
                    self._row_children.append(dot)
                    return dot
                if _hint == "outputs_only":
                    _make_dot(self._node_width)
                elif _hint == "inputs_only":
                    _make_dot(0.0)
                elif is_output:
                    _make_dot(self._node_width)
                elif is_io:
                    _make_dot(0.0)
                    _make_dot(self._node_width)
                else:
                    _make_dot(0.0)
            indent = 18 + row.depth * 12
            arrow_w = 0.0
            if row.has_children:
                arrow_char = "▼" if row.path in self._expanded_paths else "▶"
                arrow = QGraphicsSimpleTextItem(arrow_char, self)
                self._row_children.append(arrow)
                arrow.setBrush(QBrush(QColor(210, 210, 210)))
                arrow_w = arrow.boundingRect().width()
                if is_input_side:
                    ax = indent - 14
                    zone = (PIN_RADIUS + 2, indent - 2)
                else:
                    ax = self._node_width - indent + 2
                    zone = (self._node_width - indent + 2, self._node_width - PIN_RADIUS - 2)
                arrow.setPos(ax, cy - ROW_HEIGHT / 2 + 2)
                self._arrow_zones[row.path] = (zone[0], zone[1], cy)
            # sequence 노드는 핀 라벨 숨김 (dot만 표시)
            if self.node.kind != "sequence":
                label_text = row.pin.name
                if row.pin.variable_source:
                    label_text = f"{row.pin.name} (var: {row.pin.variable_source})"
                label = QGraphicsSimpleTextItem(label_text, self)
                self._row_children.append(label)
                label.setBrush(QBrush(label_color))
                is_modified = (row.path in self._connected_paths) or (row.path in self._changed_paths)
                if row.pin.is_execution or is_modified:
                    f = label.font()
                    f.setBold(True)
                    label.setFont(f)
                if is_input_side:
                    lx = indent
                else:
                    lx = self._node_width - 8 - label.boundingRect().width() - arrow_w
                label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)

    def _clear_rows(self) -> None:
        sc = self.scene()
        for child in self._row_children:
            child.setParentItem(None)
            if sc is not None:
                sc.removeItem(child)
        self._row_children.clear()
        self._rows.clear()
        self._arrow_zones.clear()

    def set_expanded_paths(self, expanded: frozenset[str]) -> None:
        if expanded == self._expanded_paths:
            return
        self._expanded_paths = expanded
        rows = collect_pin_rows(self.node,
                                connected_subtree=self._connected_paths,
                                changed_pins=self._changed_paths,
                                connected_only=self._connected_only,
                                expanded=expanded)
        self._node_width = self._compute_width(self.node, rows)
        if self._profile.layout_hint == "passthrough":
            height = HEADER_HEIGHT + ROW_HEIGHT
        else:
            height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
        self.prepareGeometryChange()
        self.setRect(QRectF(0, 0, self._node_width, height))
        self._clear_rows()
        self._row_paths = [r.path for r in rows]
        self._install_rows(rows)

    def set_highlighted(self, on: bool) -> None:
        if on:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))
        else:
            self.setPen(QPen(QColor(40, 40, 40)))


MIN_HANDLE_PX = 40.0
BACKWARD_HANDLE_PX = 120.0


class LinkItem(QGraphicsPathItem):
    """두 핀 앵커를 잇는 cubic bezier 선."""

    def __init__(self, p1: QPointF, p2: QPointF, *,
                 pen_color: "QColor | None" = None,
                 pen_color_end: "QColor | None" = None,
                 width: float = 1.5,
                 is_execution: bool = False):
        super().__init__(self._build_path(p1, p2))
        self._p1 = p1
        self._p2 = p2
        self._width = width
        self._arrow_size = max(8.0, width * 4.0)
        color = pen_color if pen_color is not None else QColor("#AAAAAA")
        self._end_color = pen_color_end if pen_color_end is not None else color
        if is_execution or pen_color_end is None or pen_color_end == color:
            pen = QPen(color, width)
        else:
            gradient = QLinearGradient(p1, p2)
            gradient.setColorAt(0.0, color)
            gradient.setColorAt(1.0, pen_color_end)
            pen = QPen(QBrush(gradient), width)
        if is_execution:
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([4, 3])
        self.setPen(pen)
        self.setZValue(-1)
        self._is_execution = is_execution
        self._dash_phase = 0.0
        if is_execution:
            self._setup_animation()

    def _setup_animation(self) -> None:
        from PySide6.QtCore import QTimer
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(50)
        self._anim_timer.timeout.connect(self._advance_dash)
        self._anim_timer.start()

    def _advance_dash(self) -> None:
        self._dash_phase -= 0.5
        pen = self.pen()
        pen.setDashOffset(self._dash_phase)
        self.setPen(pen)
        self.update()

    def _build_path(self, p1: QPointF, p2: QPointF) -> QPainterPath:
        dx = p2.x() - p1.x()
        handle = max(abs(dx) / 2.0, MIN_HANDLE_PX)
        if dx < 0:
            handle = max(handle, BACKWARD_HANDLE_PX)
        c1 = QPointF(p1.x() + handle, p1.y())
        c2 = QPointF(p2.x() - handle, p2.y())
        self._cached_c2 = c2
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        return path

    def _compute_arrow_polygon(self) -> QPolygonF:
        """끝점에 그릴 화살촉 폴리곤 (3 꼭짓점)."""
        tangent_x = self._p2.x() - self._cached_c2.x()
        tangent_y = self._p2.y() - self._cached_c2.y()
        length = (tangent_x ** 2 + tangent_y ** 2) ** 0.5
        if length < 0.001:
            dx, dy = 1.0, 0.0
        else:
            dx, dy = tangent_x / length, tangent_y / length
        size = self._arrow_size
        tip = self._p2
        back_x = tip.x() - dx * size
        back_y = tip.y() - dy * size
        perp_x = -dy * size * 0.5
        perp_y = dx * size * 0.5
        return QPolygonF([
            tip,
            QPointF(back_x + perp_x, back_y + perp_y),
            QPointF(back_x - perp_x, back_y - perp_y),
        ])

    def paint(self, painter, option, widget=None) -> None:  # noqa: N802
        super().paint(painter, option, widget)
        painter.save()
        painter.setBrush(QBrush(self._end_color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(self._compute_arrow_polygon())
        painter.restore()

    def boundingRect(self):  # noqa: N802
        base = super().boundingRect()
        return base.adjusted(-self._arrow_size, -self._arrow_size,
                             self._arrow_size, self._arrow_size)

    def update_endpoints(self, p1: QPointF, p2: QPointF) -> None:
        self.prepareGeometryChange()
        self._p1 = p1
        self._p2 = p2
        self.setPath(self._build_path(p1, p2))
