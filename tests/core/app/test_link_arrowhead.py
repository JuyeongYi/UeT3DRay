"""g9 — Link 화살촉 paint 검증."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPolygonF
from t3dgraph.core.app.items import LinkItem


def test_link_has_arrow_geometry() -> None:
    """LinkItem이 _compute_arrow_polygon을 노출 — 끝점 + 두 back 좌표."""
    item = LinkItem(QPointF(0, 0), QPointF(100, 0))
    poly = item._compute_arrow_polygon()
    assert isinstance(poly, QPolygonF)
    assert poly.size() == 3
    tip = poly.at(0)
    assert abs(tip.x() - 100) < 0.1 and abs(tip.y()) < 0.1


def test_arrow_size_scales_with_width() -> None:
    """두께가 큰 link의 화살촉이 더 큼."""
    thin = LinkItem(QPointF(0, 0), QPointF(100, 0), width=1.5)
    thick = LinkItem(QPointF(0, 0), QPointF(100, 0), width=3.0)
    thin_back_dist = abs(thin._compute_arrow_polygon().at(1).x() - thin._compute_arrow_polygon().at(0).x())
    thick_back_dist = abs(thick._compute_arrow_polygon().at(1).x() - thick._compute_arrow_polygon().at(0).x())
    assert thick_back_dist > thin_back_dist


def test_arrow_direction_along_tangent() -> None:
    """bezier c2->p2 접선 방향 — back midpoint이 tip 왼쪽 (좌->우 접선)."""
    item = LinkItem(QPointF(0, 0), QPointF(100, 50))
    poly = item._compute_arrow_polygon()
    tip = poly.at(0)
    back_mid_x = (poly.at(1).x() + poly.at(2).x()) / 2
    # 좌->우 link: 접선이 오른쪽 -> back은 tip의 왼쪽
    assert back_mid_x < tip.x()
    assert abs(tip.x() - 100) < 0.1
    assert abs(tip.y() - 50) < 0.1


def test_short_link_arrow_clamped() -> None:
    """매우 짧은 link도 화살촉 폴리곤 생성 (degenerate 처리)."""
    item = LinkItem(QPointF(0, 0), QPointF(1, 0))
    poly = item._compute_arrow_polygon()
    assert poly.size() == 3
