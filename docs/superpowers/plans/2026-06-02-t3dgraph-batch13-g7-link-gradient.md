# batch ⑬ g7 — Link 색 시작→끝 보간 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Link이 source pin 색에서 target pin 색으로 좌표 따라 보간(`QLinearGradient`). 데이터 link만 적용 (exec link는 g4의 단색 + 애니메이션 유지).

**Pre-condition:** master `f167973` 이상. g4 머지 후 진입(LinkItem 시그니처 이미 확장됨) — 또는 g4와 함께 rebase.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (`LinkItem`에 `pen_color_end` 인자 + `QLinearGradient` 펜) |
| `src/t3dgraph/core/app/scene.py` | 수정 (`_add_link`에서 target pin 색도 룩업·전달) |
| `tests/app/test_link_gradient.py` | 신규 |

---

## Task 1: LinkItem QLinearGradient pen

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_link_gradient.py`

- [ ] **Step 1: 테스트**

```python
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
    # Brush가 LinearGradientPattern
    assert brush.style().name == "LinearGradientPattern" or brush.gradient() is not None


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
        pen_color_end=QColor("#FF0000"),   # 무시되어야
        is_execution=True,
    )
    # exec은 시작색 단색 (Dash + animation)
    assert item.pen().color() == QColor("#FFB000")
```

- [ ] **Step 2: LinkItem 확장**

`src/t3dgraph/core/app/items.py`:

```python
class LinkItem(QGraphicsPathItem):
    def __init__(self, p1: QPointF, p2: QPointF, *,
                 pen_color: QColor | None = None,
                 pen_color_end: QColor | None = None,
                 width: float = 1.5,
                 is_execution: bool = False):
        super().__init__(self._build_path(p1, p2))
        self._p1 = p1
        self._p2 = p2
        color = pen_color if pen_color is not None else QColor("#AAAAAA")
        # exec link 또는 두 색이 같으면 단색
        if is_execution or pen_color_end is None or pen_color_end == color:
            pen = QPen(color, width)
        else:
            gradient = QLinearGradient(p1, p2)
            gradient.setColorAt(0.0, color)
            gradient.setColorAt(1.0, pen_color_end)
            pen = QPen(QBrush(gradient), width)
        if is_execution:
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([4, 3])
        self.setPen(pen)
        self.setZValue(-1)
        self._is_execution = is_execution
        self._dash_phase = 0.0
        if is_execution:
            self._setup_animation()
```

`QLinearGradient` import 추가 (상단 `from PySide6.QtGui import ...`).

- [ ] **Step 3: scene._add_link이 target pin 색도 룩업**

`src/t3dgraph/core/app/scene.py::_add_link`:

```python
def _add_link(self, link) -> None:
    # ... (기존 source 룩업)
    color_src = color   # 위에서 계산된 source 색
    color_dst = None
    if self._graph is not None and self._pin_colors is not None:
        dst_pin = self._graph.find_pin(link.target_path)
        if dst_pin is not None:
            color_dst = self._pin_colors.resolve(dst_pin.cpp_type).color
    item = LinkItem(p1, p2,
                    pen_color=color_src,
                    pen_color_end=color_dst,
                    width=width,
                    is_execution=is_exec)
    self.addItem(item)
    self._links.append((item, s_node, s_sub, t_node, t_sub))
```

- [ ] **Step 4: 실행 — 통과**

Run: `pytest tests/app/test_link_gradient.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (g4 테스트도 그대로).

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

데이터 link가 source pin 색에서 target pin 색으로 흐르는지 확인 (동일 타입이면 단색).

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_link_gradient.py src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py
git commit -m "feat(app): LinkItem source→target color gradient (data links)"
```

## 완료 후

데이터 link 색 보간 완료. exec link는 단색 + 애니메이션 유지 (g4 동작).
