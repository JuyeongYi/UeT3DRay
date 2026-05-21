import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.inspector_panel import InspectorPanel
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_inspector_header_includes_role_summary(qapp):
    panel = InspectorPanel()
    g = GraphModel(nodes=[Node(
        name="RigUnit_BeginExecution", cls="...RigVMUnitNode",
        display_name="Begin Execution",
        role_summary="RigUnit_BeginExecution",
        role_category="Unit",
    )])
    panel.show_node(g.nodes[0], g)
    assert "Begin Execution" in panel._title.text()
    assert "Unit" in panel._title.text()
    assert "RigUnit_BeginExecution" in panel._title.text()


def test_inspector_header_skips_role_when_absent(qapp):
    panel = InspectorPanel()
    g = GraphModel(nodes=[Node(name="X", cls=None)])
    panel.show_node(g.nodes[0], g)
    assert "X" in panel._title.text()
