"""서브그래프 진입 시그널 + MainWindow/Controller 통합 (F5/F6)."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _graph_with_subgraph() -> GraphModel:
    inner = GraphModel(label="P/inner", parent_node="P",
                       nodes=[Node(name="I", cls=None)])
    return GraphModel(label="root",
                      nodes=[Node(name="P", cls=None, subgraph=inner)])


def test_double_click_header_emits_enter_subgraph(qapp):
    g = _graph_with_subgraph()
    scene = GraphScene()
    scene.populate(g)
    received: list[str] = []
    scene.enter_subgraph_requested.connect(received.append)
    item = scene.node_item("P")
    assert item is not None
    item.simulate_header_double_click()
    assert received == ["P"]
