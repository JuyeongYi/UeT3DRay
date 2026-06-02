# batch ⑬ g9 — Link 진행 방향 화살촉 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 모든 link의 끝점(target side)에 진행 방향 화살촉 표시. 데이터 link 정적, exec link는 g4 애니메이션 위에 화살촉 함께.

**Pre-condition:** master `185b639` 이상. g4(LinkItem 시그니처) + g7(gradient) 머지 후 — LinkItem 색·color_end 정보 이미 보유.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (`LinkItem._build_path` 결과로 c2/p2 저장 + `paint()` 오버라이드) |
| `tests/app/test_link_arrowhead.py` | 신규 |

---

## Task 1: paint() 오버라이드로 화살촉 그리기 — TDD

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_link_arrowhead.py`

- [ ] **Step 1: 테스트**

```python
"""g9 — Link 화살촉 paint 검증."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPolygonF
from t3dgraph.core.app.items import LinkItem


def test_link_has_arrow_geometry() -> None:
    """LinkItem이 _arrow_polygon (또는 비슷한 API)을 노출 — 끝점 + 두 back 좌표."""
    item = LinkItem(QPointF(0, 0), QPointF(100, 0))
    poly = item._compute_arrow_polygon()
    assert isinstance(poly, QPolygonF)
    assert poly.size() == 3
    # 꼭짓점이 끝점(100,0) — 또는 가까움
    tip = poly.at(0)
    assert abs(tip.x() - 100) < 0.1 and abs(tip.y()) < 0.1


def test_arrow_size_scales_with_width() -> None:
    """두께가 큰 link의 화살촉이 더 큼."""
    thin = LinkItem(QPointF(0, 0), QPointF(100, 0), width=1.5)
    thick = LinkItem(QPointF(0, 0), QPointF(100, 0), width=3.0)
    thin_poly = thin._compute_arrow_polygon()
    thick_poly = thick._compute_arrow_polygon()
    # back distance from tip
    thin_back_dist = abs(thin_poly.at(1).x() - thin_poly.at(0).x())
    thick_back_dist = abs(thick_poly.at(1).x() - thick_poly.at(0).x())
    assert thick_back_dist > thin_back_dist


def test_arrow_direction_along_tangent() -> None:
    """수직 link → 화살촉도 수직."""
    item = LinkItem(QPointF(0, 0), QPointF(0, 100))
    poly = item._compute_arrow_polygon()
    tip = poly.at(0)
    back_mid_x = (poly.at(1).x() + poly.at(2).x()) / 2
    back_mid_y = (poly.at(1).y() + poly.at(2).y()) / 2
    # tip → back vector가 수직 (y 방향, x 거의 0)
    assert abs(tip.x() - back_mid_x) < 1.0
    # y 방향 변화 있음
    assert abs(tip.y() - back_mid_y) > 5.0


def test_short_link_arrow_clamped() -> None:
    """매우 짧은 link도 화살촉 폴리곤 생성 (degenerate 처리)."""
    item = LinkItem(QPointF(0, 0), QPointF(1, 0))
    poly = item._compute_arrow_polygon()
    assert poly.size() == 3
```

- [ ] **Step 2: 구현**

`src/t3dgraph/core/app/items.py` `LinkItem`:

```python
class LinkItem(QGraphicsPathItem):
    def __init__(self, p1: QPointF, p2: QPointF, *,
                 pen_color: QColor | None = None,
                 pen_color_end: QColor | None = None,
                 width: float = 1.5,
                 is_execution: bool = False):
        # _build_path가 c1, c2를 캐시
        path = self._build_path(p1, p2)
        super().__init__(path)
        self._p1 = p1
        self._p2 = p2
        self._c2 = self._cached_c2   # _build_path 부수 효과로 저장
        self._width = width
        self._arrow_size = max(8.0, width * 4.0)
        color = pen_color if pen_color is not None else QColor("#AAAAAA")
        self._end_color = pen_color_end if pen_color_end is not None else color
        # ... 기존 pen / gradient / dash / animation ...
        self._is_execution = is_execution
        # ...

    def _build_path(self, p1: QPointF, p2: QPointF) -> QPainterPath:
        dx = p2.x() - p1.x()
        handle = max(abs(dx) / 2.0, MIN_HANDLE_PX)
        if dx < 0:
            handle = max(handle, BACKWARD_HANDLE_PX)
        c1 = QPointF(p1.x() + handle, p1.y())
        c2 = QPointF(p2.x() - handle, p2.y())
        self._cached_c2 = c2
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        return path

    def _compute_arrow_polygon(self) -> QPolygonF:
        """끝점에 그릴 화살촉 폴리곤 (3 꼭짓점)."""
        tangent_x = self._p2.x() - self._c2.x()
        tangent_y = self._p2.y() - self._c2.y()
        length = (tangent_x ** 2 + tangent_y ** 2) ** 0.5
        if length < 0.001:
            # 수평 우향 기본
            dx, dy = 1.0, 0.0
        else:
            dx, dy = tangent_x / length, tangent_y / length
        size = self._arrow_size
        tip = self._p2
        back_x = tip.x() - dx * size
        back_y = tip.y() - dy * size
        perp_x = -dy * size * 0.5
        perp_y =  dx * size * 0.5
        return QPolygonF([
            tip,
            QPointF(back_x + perp_x, back_y + perp_y),
            QPointF(back_x - perp_x, back_y - perp_y),
        ])

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.save()
        painter.setBrush(QBrush(self._end_color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(self._compute_arrow_polygon())
        painter.restore()

    def boundingRect(self):
        # 화살촉이 path bounds 밖으로 약간 나갈 수 있어 약간 확장
        base = super().boundingRect()
        return base.adjusted(-self._arrow_size, -self._arrow_size,
                             self._arrow_size, self._arrow_size)
```

`QPolygonF`, `QBrush` import 추가.

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_link_arrowhead.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (기존 link 테스트가 paint 동작 가정 안 하므로 영향 없음).

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

링크 끝점에 삼각 화살촉 표시 — 데이터/exec 모두. exec는 dash 애니메이션 위에 화살촉 정적.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_link_arrowhead.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): LinkItem direction arrowhead at target endpoint"
```

## 완료 후

진행 방향 시각 정보 추가. batch ⑬ 사용자 피드백 + 보강 모두 마감.
