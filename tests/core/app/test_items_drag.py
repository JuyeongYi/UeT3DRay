"""F18 NodeItem 드래그 — ItemIsMovable + position_changed 신호."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene

from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _node() -> Node:
    return Node(name="N", cls="Test",
                pins=[Pin(name="A", cpp_type="bool", direction="Input")])


def test_node_item_has_movable_flag(qtbot) -> None:
    item = NodeItem(_node())
    assert item.flags() & QGraphicsItem.ItemIsMovable


def test_set_pos_emits_position_changed(qtbot) -> None:
    scene = QGraphicsScene()
    item = NodeItem(_node())
    scene.addItem(item)
    received: list[tuple[str, float, float]] = []
    assert item.bus is not None
    item.bus.position_changed.connect(
        lambda name, x, y: received.append((name, x, y)))
    item.setPos(QPointF(150.0, 75.0))
    assert received == [("N", 150.0, 75.0)]


def test_position_changed_carries_node_name(qtbot) -> None:
    scene = QGraphicsScene()
    n = Node(name="Distinct", cls="T", pins=[])
    item = NodeItem(n)
    scene.addItem(item)
    received: list[str] = []
    assert item.bus is not None
    item.bus.position_changed.connect(lambda name, *_: received.append(name))
    item.setPos(QPointF(10.0, 20.0))
    assert received == ["Distinct"]
