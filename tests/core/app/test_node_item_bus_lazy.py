"""_NodeItemBus lazy-init — 필요한 노드만 버스 생성 (C-B3)."""
from __future__ import annotations
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.base.graph_model import Node, Pin, GraphModel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_bus_always_created(qapp):
    """F18: bus는 드래그 신호가 필요하므로 모든 노드에 생성."""
    node = Node(name="X", cls=None)
    item = NodeItem(node)
    assert item._bus is not None


def test_bus_created_for_subgraph_node(qapp):
    node = Node(name="P", cls=None, subgraph=GraphModel())
    item = NodeItem(node)
    assert item._bus is not None
    assert hasattr(item._bus, "enter_subgraph_requested")


def test_bus_created_for_pinned_node(qapp):
    node = Node(name="N", cls=None,
                pins=[Pin(name="P", cpp_type="int", direction="Input")])
    item = NodeItem(node)
    assert item._bus is not None


def test_bare_node_double_click_does_not_raise(qapp):
    """bus 없는 노드의 더블클릭은 AttributeError 없이 통과."""
    from PySide6.QtCore import QPointF, QEvent, Qt
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent
    node = Node(name="X", cls=None)
    item = NodeItem(node)
    event = QGraphicsSceneMouseEvent(QEvent.GraphicsSceneMouseDoubleClick)
    event.setPos(QPointF(10, 10))
    event.setButton(Qt.LeftButton)
    item.mouseDoubleClickEvent(event)  # 예외 없이 통과
