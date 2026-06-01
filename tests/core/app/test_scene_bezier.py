"""F13 LinkItem cubic bezier — path 모양·백워드 핸들 가산."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem

from t3dgraph.core.app.items import LinkItem, BACKWARD_HANDLE_PX


def test_link_item_is_path_item(qtbot) -> None:
    p1 = QPointF(0, 0)
    p2 = QPointF(200, 50)
    item = LinkItem(p1, p2)
    assert isinstance(item, QGraphicsPathItem)


def test_path_has_cubic_segment(qtbot) -> None:
    p1 = QPointF(0, 0)
    p2 = QPointF(200, 50)
    item = LinkItem(p1, p2)
    path = item.path()
    # moveTo + 3 cubic points (c1, c2, end)
    assert path.elementCount() == 4
    # 시작·끝 좌표
    start = path.elementAt(0)
    end = path.elementAt(3)
    assert (start.x, start.y) == (p1.x(), p1.y())
    assert (end.x, end.y) == (p2.x(), p2.y())


def test_forward_handle_length(qtbot) -> None:
    """앞으로 흐르는 링크는 dx/2 길이의 수평 핸들."""
    p1 = QPointF(0, 0)
    p2 = QPointF(200, 0)
    item = LinkItem(p1, p2)
    path = item.path()
    c1 = path.elementAt(1)
    c2 = path.elementAt(2)
    # 양쪽 endpoint에서 수평 (y 동일)
    assert c1.y == p1.y()
    assert c2.y == p2.y()
    # dx=200 → handle=100
    assert c1.x == pytest.approx(100.0)
    assert c2.x == pytest.approx(100.0)


def test_backward_handle_extended(qtbot) -> None:
    """역방향(dx<0)에선 핸들 길이가 BACKWARD_HANDLE_PX 이상."""
    p1 = QPointF(200, 0)
    p2 = QPointF(0, 0)
    item = LinkItem(p1, p2)
    path = item.path()
    c1 = path.elementAt(1)
    # 핸들이 p1에서 BACKWARD_HANDLE_PX 만큼 + 방향(오른쪽)
    handle_len = c1.x - p1.x()
    assert handle_len >= BACKWARD_HANDLE_PX


def test_short_link_has_minimum_handle(qtbot) -> None:
    """짧은 거리(dx<MIN_HANDLE)에서도 최소 핸들 보장."""
    p1 = QPointF(0, 0)
    p2 = QPointF(10, 0)
    item = LinkItem(p1, p2)
    path = item.path()
    c1 = path.elementAt(1)
    assert c1.x - p1.x() >= 40.0  # MIN_HANDLE_PX
