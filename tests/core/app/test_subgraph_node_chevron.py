"""서브그래프 보유 노드에 chevron(▶) 표시 (F5 UX)."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QGraphicsSimpleTextItem

from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_subgraph_node_shows_chevron(qapp):
    inner = GraphModel(label="x")
    node = Node(name="P", cls=None, subgraph=inner)
    item = NodeItem(node)
    chevrons = [c for c in item.childItems()
                if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "▶"]
    assert len(chevrons) == 1


def test_no_chevron_when_no_subgraph(qapp):
    node = Node(name="Q", cls=None)
    item = NodeItem(node)
    chevrons = [c for c in item.childItems()
                if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "▶"]
    assert chevrons == []
