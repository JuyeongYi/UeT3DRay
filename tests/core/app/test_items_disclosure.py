"""F12 disclosure indicator — ▶/▼ 표시·클릭 토글."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from PySide6.QtCore import QPointF

from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _node_with_struct() -> Node:
    sub_a = Pin(name="X", cpp_type="float", direction="Input")
    sub_b = Pin(name="Y", cpp_type="float", direction="Input")
    parent = Pin(name="P", cpp_type="FVector", direction="Input",
                 subpins=[sub_a, sub_b])
    leaf = Pin(name="Q", cpp_type="bool", direction="Input")
    return Node(name="N", cls="Test", pins=[parent, leaf])


def _arrows_in(item: NodeItem) -> list[str]:
    return [
        c.text() for c in item.childItems()
        if isinstance(c, QGraphicsSimpleTextItem) and c.text() in ("▶", "▼")
    ]


def test_arrow_appears_for_pin_with_subpins(qtbot) -> None:
    item = NodeItem(_node_with_struct())
    arrows = _arrows_in(item)
    # struct 핀 P 한 줄에 ▶ (접힘 상태)
    assert arrows == ["▶"]


def test_arrow_flips_to_down_when_expanded(qtbot) -> None:
    item = NodeItem(_node_with_struct(),
                    expanded_paths=frozenset({"N.P"}))
    arrows = _arrows_in(item)
    # 펼침 ▼ + 자식 두 줄에는 화살표 없음
    assert arrows == ["▼"]


def test_no_arrow_on_leaf_pin(qtbot) -> None:
    leaf_only = Node(name="N", cls="Test",
                     pins=[Pin(name="A", cpp_type="bool", direction="Input")])
    item = NodeItem(leaf_only)
    assert _arrows_in(item) == []


def test_arrow_zone_click_emits_toggle(qtbot, monkeypatch) -> None:
    item = NodeItem(_node_with_struct())
    emitted: list[str] = []
    assert item.bus is not None
    item.bus.pin_toggle_requested.connect(lambda p: emitted.append(p))
    # struct 핀 P 의 화살표 위치 추정 — input pin zone: (PIN_RADIUS+2, indent-2)
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT, PIN_RADIUS
    row_y = HEADER_HEIGHT + 0 * ROW_HEIGHT + ROW_HEIGHT / 2
    click_pos = QPointF(PIN_RADIUS + 4, row_y)  # zone 안쪽
    item.toggle_at_pos(click_pos)
    assert emitted == ["N.P"]


def test_arrow_zone_click_outside_arrow_does_not_emit(qtbot) -> None:
    item = NodeItem(_node_with_struct())
    emitted: list[str] = []
    assert item.bus is not None
    item.bus.pin_toggle_requested.connect(lambda p: emitted.append(p))
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT, NODE_WIDTH
    row_y = HEADER_HEIGHT + 0 * ROW_HEIGHT + ROW_HEIGHT / 2
    # 노드 중앙(라벨 영역)은 토글 미발사
    item.toggle_at_pos(QPointF(NODE_WIDTH / 2, row_y))
    assert emitted == []
