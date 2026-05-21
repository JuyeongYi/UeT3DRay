"""MainWindow.show_analyses — AnalysisBundle 단일 호출 (D-B3)."""
from __future__ import annotations
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_show_analyses_populates_all_panels(qapp):
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None, pins=[Pin(name="O", cpp_type="float", direction="Output")]),
            Node(name="B", cls=None, pins=[Pin(name="I", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.O", target_path="B.I")],
    )
    win = MainWindow()
    win.open_graph(g, label="t")
    assert {"A", "B"}.issubset(win.data_flow_panel.shown_node_names())
