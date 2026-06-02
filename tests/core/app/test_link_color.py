"""g4 (F25/F27) — Link 색·두께·exec 애니메이션."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from t3dgraph.core.app.items import LinkItem


def test_link_uses_specified_color() -> None:
    item = LinkItem(QPointF(0, 0), QPointF(100, 0),
                    pen_color=QColor("#FF0000"))
    assert item.pen().color() == QColor("#FF0000")


def test_link_default_color() -> None:
    item = LinkItem(QPointF(0, 0), QPointF(100, 0))
    assert item.pen().color() == QColor("#AAAAAA")


def test_link_exec_thicker() -> None:
    item = LinkItem(QPointF(0, 0), QPointF(100, 0),
                    is_execution=True, width=3.0)
    assert item.pen().widthF() == 3.0


def test_link_exec_has_dash() -> None:
    from PySide6.QtCore import Qt
    item = LinkItem(QPointF(0, 0), QPointF(100, 0), is_execution=True)
    assert item.pen().style() == Qt.DashLine or len(item.pen().dashPattern()) > 0
