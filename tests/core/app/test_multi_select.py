"""g12 (F33) — 다중 선택 + 인스펙터 표시."""
from PySide6.QtWidgets import QGraphicsView

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow


def test_graph_view_rubber_band_mode(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.view.dragMode() == QGraphicsView.RubberBandDrag


def test_inspector_shows_multi_selection_label(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(nodes=[
        Node(name="A", cls="T"),
        Node(name="B", cls="T"),
        Node(name="C", cls="T"),
    ])
    w.open_graph(g)
    a = w.scene.node_item("A")
    b = w.scene.node_item("B")
    a.setSelected(True)
    b.setSelected(True)
    w._on_scene_selection()
    assert "다중 선택" in w.inspector._title.text()
    assert "2" in w.inspector._title.text()


def test_inspector_single_selection_unchanged(qtbot) -> None:
    """1개 선택은 기존 show_node 동작."""
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(nodes=[Node(name="OnlyOne", cls="T")])
    w.open_graph(g)
    item = w.scene.node_item("OnlyOne")
    item.setSelected(True)
    w._on_scene_selection()
    assert "다중 선택" not in w.inspector._title.text()
    assert "OnlyOne" in w.inspector._title.text()
