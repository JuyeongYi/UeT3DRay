import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_open_pipeline_populates_data_flow_panel(qapp):
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[Pin(name="Out", cpp_type="float", direction="Output")]),
            Node(name="B", cls=None,
                 pins=[Pin(name="In", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )
    win = MainWindow()
    win.show_graph(g)
    from t3dgraph.core.analysis.data_flow import analyze_data_flow
    win.show_data_flow(analyze_data_flow(g))
    assert win.data_flow_panel.shown_node_names() >= {"A", "B"}
