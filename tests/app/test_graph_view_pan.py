"""u1 — GraphView 가운데 클릭 패닝."""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from t3dgraph.core.app.graph_view import GraphView


def _press(view, button, pos):
    ev = QMouseEvent(QMouseEvent.MouseButtonPress, pos, view.mapToGlobal(pos),
                     button, button, Qt.NoModifier)
    view.mousePressEvent(ev)


def _move(view, pos, buttons):
    ev = QMouseEvent(QMouseEvent.MouseMove, pos, view.mapToGlobal(pos),
                     Qt.NoButton, buttons, Qt.NoModifier)
    view.mouseMoveEvent(ev)


def _release(view, button, pos):
    ev = QMouseEvent(QMouseEvent.MouseButtonRelease, pos, view.mapToGlobal(pos),
                     button, Qt.NoButton, Qt.NoModifier)
    view.mouseReleaseEvent(ev)


def test_middle_click_starts_pan(qtbot) -> None:
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(QGraphicsScene())
    view.resize(400, 300)
    view.show()
    qtbot.waitExposed(view)
    _press(view, Qt.MiddleButton, QPoint(100, 100))
    assert view._panning is True


def test_middle_drag_pans_view(qtbot) -> None:
    view = GraphView()
    qtbot.addWidget(view)
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 2000, 2000)
    view.setScene(scene)
    view.resize(400, 300)
    view.show()
    qtbot.waitExposed(view)
    initial_h = view.horizontalScrollBar().value()
    initial_v = view.verticalScrollBar().value()
    _press(view, Qt.MiddleButton, QPoint(200, 150))
    _move(view, QPoint(150, 100), Qt.MiddleButton)
    # 스크롤바가 음수 delta만큼 이동
    assert view.horizontalScrollBar().value() > initial_h
    assert view.verticalScrollBar().value() > initial_v


def test_middle_release_ends_pan(qtbot) -> None:
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(QGraphicsScene())
    view.resize(400, 300)
    view.show()
    qtbot.waitExposed(view)
    _press(view, Qt.MiddleButton, QPoint(100, 100))
    _release(view, Qt.MiddleButton, QPoint(100, 100))
    assert view._panning is False


def test_left_click_unaffected(qtbot) -> None:
    """좌클릭은 패닝 모드 진입 X (RubberBand 그대로)."""
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(QGraphicsScene())
    view.resize(400, 300)
    view.show()
    qtbot.waitExposed(view)
    _press(view, Qt.LeftButton, QPoint(100, 100))
    assert view._panning is False
