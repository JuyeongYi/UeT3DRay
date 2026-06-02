"""g7 — LinkItem source→target 색 보간."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QLinearGradient
from t3dgraph.core.app.items import LinkItem


def test_link_gradient_pen_when_colors_differ() -> None:
    """source/target 색이 다르면 QLinearGradient pen 사용."""
    item = LinkItem(
        QPointF(0, 0), QPointF(100, 0),
        pen_color=QColor("#FF0000"),
        pen_color_end=QColor("#00FF00"),
    )
    brush = item.pen().brush()
    assert brush.gradient() is not None


def test_link_solid_when_colors_same() -> None:
    """같은 색이면 solid (gradient 불필요)."""
    c = QColor("#FF0000")
    item = LinkItem(QPointF(0, 0), QPointF(100, 0),
                    pen_color=c, pen_color_end=c)
    assert item.pen().color() == c


def test_link_solid_when_end_not_specified() -> None:
    """pen_color_end 미지정 → 기존 단색 (g4 호환)."""
    c = QColor("#0000FF")
    item = LinkItem(QPointF(0, 0), QPointF(100, 0), pen_color=c)
    assert item.pen().color() == c


def test_link_exec_no_gradient() -> None:
    """exec link는 단색 + 애니메이션 (g4 동작) — 색 보간 무관."""
    item = LinkItem(
        QPointF(0, 0), QPointF(100, 0),
        pen_color=QColor("#FFB000"),
        pen_color_end=QColor("#FF0000"),
        is_execution=True,
    )
    assert item.pen().color() == QColor("#FFB000")
