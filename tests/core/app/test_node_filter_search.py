import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.node_filter_panel import NodeFilterPanel
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_match_node_by_name(qapp):
    g = GraphModel(nodes=[
        Node(name="RigUnit_BeginExecution", cls=None, display_name="Begin Execution"),
        Node(name="StepPhysicsSolver", cls=None, display_name="Step Physics Solver"),
    ])
    panel = NodeFilterPanel()
    panel.set_graph(g)
    panel.set_search_text("step")
    hits = panel.matched_node_names()
    assert "StepPhysicsSolver" in hits
    assert "RigUnit_BeginExecution" not in hits


def test_match_node_by_display_name(qapp):
    g = GraphModel(nodes=[
        Node(name="RigUnit_BeginExecution", cls=None, display_name="Begin Execution"),
    ])
    panel = NodeFilterPanel()
    panel.set_graph(g)
    panel.set_search_text("begin")
    hits = panel.matched_node_names()
    assert "RigUnit_BeginExecution" in hits


def test_empty_search_returns_all(qapp):
    g = GraphModel(nodes=[
        Node(name="A", cls=None), Node(name="B", cls=None),
    ])
    panel = NodeFilterPanel()
    panel.set_graph(g)
    panel.set_search_text("")
    hits = panel.matched_node_names()
    assert hits == {"A", "B"}
