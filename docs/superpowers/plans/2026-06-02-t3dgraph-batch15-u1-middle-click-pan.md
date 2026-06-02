# batch ⑮ u1 — 가운데 클릭 그래프 패닝 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 그래프 뷰에서 가운데 마우스 버튼 누른 채 드래그로 패닝. UE Blueprint·표준 노드 에디터 컨벤션.

**Pre-condition:** master 최신.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/graph_view.py` | 수정 (`mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` 오버라이드) |
| `tests/app/test_graph_view_pan.py` | 신규 |

---

## Task 1: 미들 버튼 패닝

**Files:**
- Modify: `src/t3dgraph/core/app/graph_view.py`
- Create: `tests/app/test_graph_view_pan.py`

- [ ] **Step 1: 테스트**

```python
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
```

- [ ] **Step 2: GraphView 변경**

`src/t3dgraph/core/app/graph_view.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsView


class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHints(...)   # 기존 그대로
        self.setDragMode(QGraphicsView.RubberBandDrag)   # g12에서 추가됨
        self._panning = False
        self._pan_anchor = None
        self._previous_drag_mode = QGraphicsView.RubberBandDrag

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_anchor = event.pos()
            self._previous_drag_mode = self.dragMode()
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning and self._pan_anchor is not None:
            delta = event.pos() - self._pan_anchor
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self._pan_anchor = event.pos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self._pan_anchor = None
            self.setDragMode(self._previous_drag_mode)
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)
```

(기존 GraphView 메서드들과 합쳐 — fit·zoom·etc. 등 보존.)

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_graph_view_pan.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

큰 그래프 열고 가운데 마우스 누른 채 드래그 → 그래프 패닝. 커서가 손 모양으로 변환. 좌클릭은 기존 선택(RubberBand) 그대로.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_graph_view_pan.py src/t3dgraph/core/app/graph_view.py
git commit -m "feat(app): middle-button pan in GraphView (UE Blueprint style)"
```

## 완료 후

그래프 탐색 UX 표준 컨벤션 확보. 좌클릭 RubberBand 선택, 가운데 클릭 패닝, 휠 줌(이미 있음).
