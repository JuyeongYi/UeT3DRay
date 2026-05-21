import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.base.graph_model import Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_node_title_uses_display_name_when_set(qapp):
    node = Node(name="RigUnit_BeginExecution", cls=None,
                display_name="Begin Execution")
    item = NodeItem(node)
    titles = [c.text() for c in item.childItems()
              if c.__class__.__name__ == "QGraphicsSimpleTextItem"]
    assert titles[0] == "Begin Execution"


def test_node_title_fallback_to_name(qapp):
    node = Node(name="X", cls=None, display_name=None)
    item = NodeItem(node)
    titles = [c.text() for c in item.childItems()
              if c.__class__.__name__ == "QGraphicsSimpleTextItem"]
    assert titles[0] == "X"
