from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.contracts import AbstractGraphView
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_main_window_is_graph_view(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert isinstance(w, AbstractGraphView)


def test_show_graph_populates_scene(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(
        nodes=[Node(name="A", cls="X", position=(0.0, 0.0),
                    pins=[Pin("O", "exec", "Output")]),
               Node(name="B", cls="X", position=(300.0, 0.0),
                    pins=[Pin("I", "exec", "Input")])],
        links=[Link("A.O", "B.I")],
    )
    w.show_graph(g)
    assert w.scene.node_item("A") is not None
    assert w.scene.node_item("B") is not None


def test_open_callback_invoked(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    captured = []
    w.set_open_handler(lambda path: captured.append(path))
    w.open_path("C:/some/file.t3d.txt")
    assert captured == ["C:/some/file.t3d.txt"]


def test_has_three_docks(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert {w.dock_left.windowTitle(), w.dock_right.windowTitle(),
            w.dock_bottom.windowTitle()} == {"노드 타입 필터", "속성 인스펙터", "분석"}
