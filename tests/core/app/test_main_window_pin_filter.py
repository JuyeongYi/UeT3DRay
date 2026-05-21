import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _graph_with_struct_pin():
    return GraphModel(
        nodes=[
            Node(name="N", cls=None, pins=[
                Pin(name="V", cpp_type="FVector", direction="Input", subpins=[
                    Pin(name="X", cpp_type="float", direction="Input"),
                    Pin(name="Y", cpp_type="float", direction="Input"),
                ]),
            ]),
        ],
        links=[],
    )


def test_pin_double_click_toggles_expand(qapp):
    win = MainWindow()
    g = _graph_with_struct_pin()
    win.show_graph(g)
    item = win.scene.node_item("N")
    assert item is not None
    assert "N.V" in item._rows
    assert "N.V.X" not in item._rows
    item.toggle_pin_at_row(0)
    win._rebuild_scene()
    item2 = win.scene.node_item("N")
    assert "N.V.X" in item2._rows


def test_preserve_all_nodes_after_expand(qapp):
    win = MainWindow()
    g = _graph_with_struct_pin()
    win.show_graph(g)
    win._on_expand_all_pins()
    assert set(win.scene._nodes.keys()) >= {n.name for n in g.nodes}
