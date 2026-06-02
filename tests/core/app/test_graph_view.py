from t3dgraph.core.app.graph_view import GraphView
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.base.graph_model import GraphModel, Node


def test_view_holds_scene(qtbot):
    scene = GraphScene()
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(scene)
    assert view.scene() is scene


def test_view_drag_mode_is_rubber_band(qtbot):
    from PySide6.QtWidgets import QGraphicsView
    view = GraphView()
    qtbot.addWidget(view)
    assert view.dragMode() == QGraphicsView.RubberBandDrag


def test_fit_does_not_raise_on_populated_scene(qtbot):
    scene = GraphScene()
    scene.populate(GraphModel(nodes=[Node(name="A", cls="X", position=(0.0, 0.0))], links=[]))
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(scene)
    view.fit()
