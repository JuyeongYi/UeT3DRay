# batch ⑨ ν (nu) — 링크·레이아웃 (F13 + F18 + F19) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 연결선을 UE 스타일 cubic bezier로 교체(F13)하고, 노드 드래그 이동 + 세션 메모리 영속(F18), 노드 헤더 우클릭 컨텍스트 메뉴(F19)를 도입한다.

**Architecture:** `LinkItem`이 `QGraphicsLineItem` → `QGraphicsPathItem`. 신규 `LayoutOverrides`가 그래프 단위 위치 오버라이드 보관. `NodeItem`에 `ItemIsMovable` + `itemChange` 훅 + `contextMenuEvent`. `ViewState`에 노드 단위 펼침/접기 helper.

**Tech Stack:** PySide6 (`QGraphicsPathItem`, `QPainterPath`, `QGraphicsItem` flags, `QMenu`), pytest + pytest-qt.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-1-vis-rendering-design.md` §5·§7·§8

**Pre-condition:** 슬라이스 μ 머지 완료 (items.py 충돌 회피).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/layout_overrides.py` | 신규 (순수 Python `LayoutOverrides`) |
| `src/t3dgraph/core/app/items.py` | 수정 (`LinkItem` 베지어, `NodeItem` flags + itemChange + contextMenuEvent, `_NodeItemBus` 신호 2개 추가) |
| `src/t3dgraph/core/app/scene.py` | 수정 (`populate(..., layout_overrides=..., graph_key=...)`) |
| `src/t3dgraph/core/app/view_state.py` | 수정 (`expand_node_pins`, `collapse_node_pins`) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`LayoutOverrides` 보유, `_current_graph_key`, 컨텍스트 메뉴, position_changed 와이어링) |
| `tests/app/test_scene_bezier.py` | 신규 |
| `tests/app/test_layout_overrides.py` | 신규 |
| `tests/app/test_items_drag.py` | 신규 |
| `tests/app/test_view_state_node_pins.py` | 신규 |
| `tests/app/test_main_window_node_menu.py` | 신규 |

---

## Task 1: `LinkItem` 큐빅 베지어 — 테스트 + 구현 (F13)

**Files:**
- Create: `tests/app/test_scene_bezier.py`
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_scene_bezier.py`:

```python
"""F13 LinkItem cubic bezier — path 모양·백워드 핸들 가산."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem

from t3dgraph.core.app.items import LinkItem, BACKWARD_HANDLE_PX


def test_link_item_is_path_item(qtbot) -> None:
    p1 = QPointF(0, 0)
    p2 = QPointF(200, 50)
    item = LinkItem(p1, p2)
    assert isinstance(item, QGraphicsPathItem)


def test_path_has_cubic_segment(qtbot) -> None:
    p1 = QPointF(0, 0)
    p2 = QPointF(200, 50)
    item = LinkItem(p1, p2)
    path = item.path()
    # moveTo + 3 cubic points (c1, c2, end)
    assert path.elementCount() == 4
    # 시작·끝 좌표
    start = path.elementAt(0)
    end = path.elementAt(3)
    assert (start.x, start.y) == (p1.x(), p1.y())
    assert (end.x, end.y) == (p2.x(), p2.y())


def test_forward_handle_length(qtbot) -> None:
    """앞으로 흐르는 링크는 dx/2 길이의 수평 핸들."""
    p1 = QPointF(0, 0)
    p2 = QPointF(200, 0)
    item = LinkItem(p1, p2)
    path = item.path()
    c1 = path.elementAt(1)
    c2 = path.elementAt(2)
    # 양쪽 endpoint에서 수평 (y 동일)
    assert c1.y == p1.y()
    assert c2.y == p2.y()
    # dx=200 → handle=100
    assert c1.x == pytest.approx(100.0)
    assert c2.x == pytest.approx(100.0)


def test_backward_handle_extended(qtbot) -> None:
    """역방향(dx<0)에선 핸들 길이가 BACKWARD_HANDLE_PX 이상."""
    p1 = QPointF(200, 0)
    p2 = QPointF(0, 0)
    item = LinkItem(p1, p2)
    path = item.path()
    c1 = path.elementAt(1)
    # 핸들이 p1에서 BACKWARD_HANDLE_PX 만큼 + 방향(오른쪽)
    handle_len = c1.x - p1.x()
    assert handle_len >= BACKWARD_HANDLE_PX


def test_short_link_has_minimum_handle(qtbot) -> None:
    """짧은 거리(dx<MIN_HANDLE)에서도 최소 핸들 보장."""
    p1 = QPointF(0, 0)
    p2 = QPointF(10, 0)
    item = LinkItem(p1, p2)
    path = item.path()
    c1 = path.elementAt(1)
    assert c1.x - p1.x() >= 40.0  # MIN_HANDLE_PX
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/app/test_scene_bezier.py -v`
Expected: FAIL — `BACKWARD_HANDLE_PX` 미정의, `LinkItem`이 `QGraphicsPathItem` 아님.

- [ ] **Step 3: `LinkItem` 베지어로 교체**

`items.py` 상단 imports:

```python
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsItem,
)
```

기존 `QGraphicsLineItem` import 제거.

상수 추가 (`PIN_RADIUS` 아래):

```python
MIN_HANDLE_PX = 40.0
BACKWARD_HANDLE_PX = 120.0
```

기존 `class LinkItem(QGraphicsLineItem):` 블록 전체를 다음으로 교체:

```python
class LinkItem(QGraphicsPathItem):
    """두 핀 앵커를 잇는 cubic bezier."""

    def __init__(self, p1: QPointF, p2: QPointF):
        super().__init__(self._build_path(p1, p2))
        self.setPen(QPen(QColor(170, 170, 170), 1.5))
        self.setZValue(-1)

    @staticmethod
    def _build_path(p1: QPointF, p2: QPointF) -> QPainterPath:
        dx = p2.x() - p1.x()
        handle = max(abs(dx) / 2.0, MIN_HANDLE_PX)
        if dx < 0:
            handle = max(handle, BACKWARD_HANDLE_PX)
        c1 = QPointF(p1.x() + handle, p1.y())
        c2 = QPointF(p2.x() - handle, p2.y())
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        return path
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/app/test_scene_bezier.py -v`
Expected: 5 passed

- [ ] **Step 5: 통합 회귀 확인**

Run: `pytest tests/app -v`
Expected: 전체 통과 (LinkItem 생성자 시그니처 동일이므로 scene._add_link 호출부 영향 없음).

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_scene_bezier.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): LinkItem cubic bezier with backward-handle extend (F13)"
```

---

## Task 2: `LayoutOverrides` 자료구조 — TDD

**Files:**
- Create: `tests/app/test_layout_overrides.py`
- Create: `src/t3dgraph/core/app/layout_overrides.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_layout_overrides.py`:

```python
"""F18 LayoutOverrides 단위 — 그래프 단위 노드 위치 보관."""
from __future__ import annotations

from t3dgraph.core.app.layout_overrides import LayoutOverrides


def test_get_missing_returns_none() -> None:
    lo = LayoutOverrides()
    assert lo.get("graph-A", "Node1") is None


def test_set_then_get() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    assert lo.get("graph-A", "Node1") == (100.0, 50.0)


def test_independent_graphs() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-B", "Node1", 200.0, 80.0)
    assert lo.get("graph-A", "Node1") == (100.0, 50.0)
    assert lo.get("graph-B", "Node1") == (200.0, 80.0)


def test_clear_node() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-A", "Node2", 30.0, 30.0)
    lo.clear_node("graph-A", "Node1")
    assert lo.get("graph-A", "Node1") is None
    assert lo.get("graph-A", "Node2") == (30.0, 30.0)


def test_clear_graph() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-B", "Node1", 200.0, 80.0)
    lo.clear_graph("graph-A")
    assert lo.get("graph-A", "Node1") is None
    assert lo.get("graph-B", "Node1") == (200.0, 80.0)


def test_all_for_graph() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-A", "Node2", 30.0, 30.0)
    assert lo.all_for_graph("graph-A") == {
        "Node1": (100.0, 50.0),
        "Node2": (30.0, 30.0),
    }


def test_all_for_graph_empty() -> None:
    lo = LayoutOverrides()
    assert lo.all_for_graph("none") == {}
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_layout_overrides.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: `LayoutOverrides` 구현**

`src/t3dgraph/core/app/layout_overrides.py`:

```python
"""그래프별 노드 위치 오버라이드 — F18 드래그 결과 세션 보관."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class LayoutOverrides:
    """graph_key → {node_name → (x, y)} 의 두 단계 dict."""

    _by_graph: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)

    def set(self, graph_key: str, node: str, x: float, y: float) -> None:
        self._by_graph.setdefault(graph_key, {})[node] = (x, y)

    def get(self, graph_key: str, node: str) -> tuple[float, float] | None:
        return self._by_graph.get(graph_key, {}).get(node)

    def clear_node(self, graph_key: str, node: str) -> None:
        graph = self._by_graph.get(graph_key)
        if graph is not None:
            graph.pop(node, None)

    def clear_graph(self, graph_key: str) -> None:
        self._by_graph.pop(graph_key, None)

    def all_for_graph(self, graph_key: str) -> dict[str, tuple[float, float]]:
        return dict(self._by_graph.get(graph_key, {}))
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_layout_overrides.py -v`
Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_layout_overrides.py src/t3dgraph/core/app/layout_overrides.py
git commit -m "feat(app): LayoutOverrides per-graph node position store (F18 prep)"
```

---

## Task 3: `NodeItem` 드래그 + position 신호 (F18)

**Files:**
- Create: `tests/app/test_items_drag.py`
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_items_drag.py`:

```python
"""F18 NodeItem 드래그 — ItemIsMovable + position_changed 신호."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene

from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _node() -> Node:
    return Node(name="N", cls="Test",
                pins=[Pin(name="A", cpp_type="bool", direction="Input")])


def test_node_item_has_movable_flag(qtbot) -> None:
    item = NodeItem(_node())
    assert item.flags() & QGraphicsItem.ItemIsMovable


def test_set_pos_emits_position_changed(qtbot) -> None:
    scene = QGraphicsScene()
    item = NodeItem(_node())
    scene.addItem(item)
    received: list[tuple[str, float, float]] = []
    assert item.bus is not None
    item.bus.position_changed.connect(
        lambda name, x, y: received.append((name, x, y)))
    item.setPos(QPointF(150.0, 75.0))
    assert received == [("N", 150.0, 75.0)]


def test_position_changed_carries_node_name(qtbot) -> None:
    scene = QGraphicsScene()
    n = Node(name="Distinct", cls="T", pins=[])
    item = NodeItem(n)
    scene.addItem(item)
    received: list[str] = []
    assert item.bus is not None
    item.bus.position_changed.connect(lambda name, *_: received.append(name))
    item.setPos(QPointF(10.0, 20.0))
    assert received == ["Distinct"]
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_items_drag.py -v`
Expected: FAIL — `position_changed` 미존재.

- [ ] **Step 3: `_NodeItemBus`에 신호 추가**

`items.py` `_NodeItemBus` 클래스:

```python
class _NodeItemBus(QObject):
    pin_toggle_requested = Signal(str)
    enter_subgraph_requested = Signal(str)
    position_changed = Signal(str, float, float)              # F18
    context_menu_requested = Signal(str, object)              # F19 (str, QPoint)
```

- [ ] **Step 4: `NodeItem`에 flags + itemChange**

`__init__` 본문 `self.setFlag(QGraphicsItem.ItemIsSelectable, True)` 다음 두 줄:

```python
self.setFlag(QGraphicsItem.ItemIsMovable, True)              # F18
self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
```

`mouseDoubleClickEvent` 위에 `itemChange` 메서드 추가:

```python
def itemChange(self, change, value):  # noqa: N802 (Qt override)
    if change == QGraphicsItem.ItemPositionHasChanged and self._bus is not None:
        p = self.pos()
        self._bus.position_changed.emit(self.node.name, p.x(), p.y())
    return super().itemChange(change, value)
```

- [ ] **Step 5: 실행 — 통과 확인**

Run: `pytest tests/app/test_items_drag.py -v`
Expected: 3 passed

- [ ] **Step 6: 회귀 확인**

Run: `pytest tests/app -v`

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_items_drag.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem drag + position_changed bus signal (F18)"
```

---

## Task 4: `scene.populate` — LayoutOverrides 적용

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`

- [ ] **Step 1: `populate` 시그니처 확장**

`scene.py` 상단 import:

```python
from .layout_overrides import LayoutOverrides
```

`populate` 시그니처를 다음과 같이 변경 (μ에서 추가된 `pin_colors` 유지):

```python
def populate(self, graph: GraphModel, *,
             view_state: ViewState | None = None,
             flow: FlowResult | None = None,
             pin_colors: "PinColorTable | None" = None,
             layout_overrides: LayoutOverrides | None = None,
             graph_key: str = "") -> None:
```

`item.setPos((fallback_i % 8) * 240.0, ...)` 블록을 다음으로 교체:

```python
override = (layout_overrides.get(graph_key, node.name)
            if layout_overrides is not None else None)
if override is not None:
    item.setPos(*override)
elif node.position is None:
    item.setPos((fallback_i % 8) * 240.0, (fallback_i // 8) * 200.0)
    fallback_i += 1
# else: NodeItem __init__이 이미 node.position 적용
```

- [ ] **Step 2: 회귀 확인**

Run: `pytest tests/app -v`

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/core/app/scene.py
git commit -m "feat(app): GraphScene.populate applies LayoutOverrides (F18)"
```

---

## Task 5: `ViewState` — 노드 단위 펼침/접기 helper (F19)

**Files:**
- Create: `tests/app/test_view_state_node_pins.py`
- Modify: `src/t3dgraph/core/app/view_state.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_view_state_node_pins.py`:

```python
"""F19 ViewState 노드 단위 펼침/접기 helper."""
from __future__ import annotations

from t3dgraph.core.app.view_state import ViewState


def test_expand_node_pins_adds_paths() -> None:
    vs = ViewState()
    vs.expand_node_pins("N1", ["N1.P", "N1.P.X", "N1.P.Y"])
    assert vs.expanded_pin_paths == {"N1.P", "N1.P.X", "N1.P.Y"}


def test_collapse_node_pins_removes_node_paths_only() -> None:
    vs = ViewState()
    vs.expand_node_pins("N1", ["N1.P", "N1.P.X"])
    vs.expand_node_pins("N2", ["N2.Q"])
    vs.collapse_node_pins("N1")
    assert vs.expanded_pin_paths == {"N2.Q"}


def test_collapse_node_pins_noop_when_absent() -> None:
    vs = ViewState()
    vs.expand_node_pins("N2", ["N2.Q"])
    vs.collapse_node_pins("N1")
    assert vs.expanded_pin_paths == {"N2.Q"}
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_view_state_node_pins.py -v`
Expected: FAIL — 메서드 미존재.

- [ ] **Step 3: 메서드 추가**

`view_state.py` `ViewState` 클래스, `collapse_all_pins` 아래:

```python
def expand_node_pins(self, node_name: str, all_paths: list[str]) -> None:
    """노드의 모든 핀 path(서브핀 포함)를 expanded set에 추가."""
    self.expanded_pin_paths.update(all_paths)

def collapse_node_pins(self, node_name: str) -> None:
    """노드 prefix에 해당하는 path를 expanded set에서 제거."""
    prefix = f"{node_name}."
    self.expanded_pin_paths = {
        p for p in self.expanded_pin_paths if not p.startswith(prefix)
    }
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_view_state_node_pins.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_view_state_node_pins.py src/t3dgraph/core/app/view_state.py
git commit -m "feat(app): ViewState per-node expand/collapse helpers (F19)"
```

---

## Task 6: `NodeItem.contextMenuEvent` (F19)

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 메서드 추가**

`items.py` `NodeItem` 클래스 `itemChange` 아래:

```python
def contextMenuEvent(self, event):  # noqa: N802 (Qt override)
    if self._bus is not None:
        self._bus.context_menu_requested.emit(self.node.name, event.screenPos())
        event.accept()
```

- [ ] **Step 2: 회귀 확인**

Run: `pytest tests/app -v`

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem contextMenuEvent → bus signal (F19)"
```

---

## Task 7: MainWindow — 컨텍스트 메뉴 + LayoutOverrides 와이어링 (F18 + F19)

**Files:**
- Create: `tests/app/test_main_window_node_menu.py`
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_main_window_node_menu.py`:

```python
"""F18 + F19 MainWindow 통합 — 노드 컨텍스트 메뉴 액션 및 LayoutOverrides 흐름."""
from __future__ import annotations
from PySide6.QtCore import QPointF, QPoint

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin
from t3dgraph.core.app.main_window import MainWindow


def _graph() -> GraphModel:
    sub_a = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="P", cpp_type="FVector", direction="Input", subpins=[sub_a])
    n1 = Node(name="N1", cls="T", pins=[parent], position=(0.0, 0.0))
    n2 = Node(name="N2", cls="T", pins=[], position=(300.0, 0.0))
    return GraphModel(nodes=[n1, n2], label="root")


def test_expand_node_pins_via_action(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    w._invoke_node_action("N1", "expand_all")
    assert "N1.P" in w.view_state.expanded_pin_paths
    assert "N1.P.X" in w.view_state.expanded_pin_paths


def test_collapse_node_pins_via_action(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    w._invoke_node_action("N1", "expand_all")
    w._invoke_node_action("N1", "collapse_all")
    assert not any(p.startswith("N1.") for p in w.view_state.expanded_pin_paths)


def test_reset_position_clears_override(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    key = w._current_graph_key()
    w.layout_overrides.set(key, "N1", 500.0, 500.0)
    w._invoke_node_action("N1", "reset_position")
    assert w.layout_overrides.get(key, "N1") is None


def test_position_changed_updates_overrides(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    item = w.scene.node_item("N1")
    assert item is not None
    item.setPos(QPointF(123.0, 45.0))
    key = w._current_graph_key()
    assert w.layout_overrides.get(key, "N1") == (123.0, 45.0)


def test_override_survives_rebuild(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    item = w.scene.node_item("N1")
    assert item is not None
    item.setPos(QPointF(123.0, 45.0))
    w._rebuild_scene()
    item2 = w.scene.node_item("N1")
    assert item2 is not None
    assert item2.pos() == QPointF(123.0, 45.0)
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_main_window_node_menu.py -v`
Expected: FAIL — `LayoutOverrides`/`_current_graph_key`/`_invoke_node_action` 미존재.

- [ ] **Step 3: MainWindow 변경**

`main_window.py` 상단 imports:

```python
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QFileDialog, QTabBar, QTabWidget, QVBoxLayout, QWidget,
    QMenu,
)
from .layout_overrides import LayoutOverrides
```

`__init__` 본문 (`self.pin_colors = PinColorTable.load()` 다음 줄, μ 슬라이스 결과 가정):

```python
self.layout_overrides = LayoutOverrides()
```

`_wire` 메서드에 NodeItem 신호 연결. 단, `NodeItem` 인스턴스는 scene.populate 안에서 생성되므로 scene 시그니처를 통해 패스스루해야 함. 가장 간단한 방법: scene이 NodeItem.bus 시그널을 자기 시그널로 재발사. `GraphScene`에 시그널 + connect를 추가.

`scene.py` `GraphScene` 클래스 시그널 추가:

```python
class GraphScene(QGraphicsScene):
    pin_toggle_requested = Signal(str)
    enter_subgraph_requested = Signal(str)
    node_position_changed = Signal(str, float, float)   # F18
    node_context_menu_requested = Signal(str, object)   # F19
```

`populate` 안 `item.bus.pin_toggle_requested.connect(...)` 다음 두 줄 추가:

```python
item.bus.position_changed.connect(self.node_position_changed)
item.bus.context_menu_requested.connect(self.node_context_menu_requested)
```

`main_window.py` `_wire`:

```python
self.scene.node_position_changed.connect(self._on_node_moved)
self.scene.node_context_menu_requested.connect(self._on_node_context_menu)
```

- [ ] **Step 4: MainWindow 슬롯 및 helper 메서드 추가**

`main_window.py`에 추가 (메서드 위치는 `_render_current` 위가 적절):

```python
def _current_graph_key(self) -> str:
    current = self.graph_stack.current()
    if current is None:
        return ""
    label = current.label or "(unlabeled)"
    parent = current.parent_node or ""
    return f"{label}/{parent}"

def _collect_node_pin_paths(self, node) -> list[str]:
    paths: list[str] = []

    def walk(pin, prefix: str) -> None:
        path = f"{prefix}.{pin.name}"
        paths.append(path)
        for sp in pin.subpins:
            walk(sp, path)

    for p in node.pins:
        walk(p, node.name)
    return paths

def _on_node_moved(self, node_name: str, x: float, y: float) -> None:
    self.layout_overrides.set(self._current_graph_key(), node_name, x, y)

def _on_node_context_menu(self, node_name: str, screen_pos) -> None:
    menu = QMenu(self)
    act_expand = menu.addAction("이 노드 모두 펼침")
    act_collapse = menu.addAction("이 노드 모두 접기")
    menu.addSeparator()
    act_reset = menu.addAction("원래 위치로 되돌리기")
    chosen = menu.exec(screen_pos.toPoint() if hasattr(screen_pos, "toPoint")
                       else screen_pos)
    if chosen is act_expand:
        self._invoke_node_action(node_name, "expand_all")
    elif chosen is act_collapse:
        self._invoke_node_action(node_name, "collapse_all")
    elif chosen is act_reset:
        self._invoke_node_action(node_name, "reset_position")

def _invoke_node_action(self, node_name: str, action: str) -> None:
    """컨텍스트 메뉴 액션 실행 — 테스트가 메뉴 popup 없이 직접 호출 가능."""
    if action == "expand_all":
        if self.graph is None:
            return
        node = self.graph.node_by_name(node_name)
        if node is None:
            return
        paths = self._collect_node_pin_paths(node)
        self.view_state.expand_node_pins(node_name, paths)
        self._rebuild_scene()
    elif action == "collapse_all":
        self.view_state.collapse_node_pins(node_name)
        self._rebuild_scene()
    elif action == "reset_position":
        self.layout_overrides.clear_node(self._current_graph_key(), node_name)
        self._rebuild_scene()
```

- [ ] **Step 5: `_rebuild_scene` / `_render_current`에 layout_overrides 주입**

`_rebuild_scene`:

```python
def _rebuild_scene(self) -> None:
    if self.graph is not None:
        self.scene.populate(self.graph, view_state=self.view_state,
                            flow=self._flow, pin_colors=self.pin_colors,
                            layout_overrides=self.layout_overrides,
                            graph_key=self._current_graph_key())
```

`_render_current` 안 populate 호출도 동일 인자 추가:

```python
self.scene.populate(current, view_state=self.view_state,
                    flow=bundle.flow, pin_colors=self.pin_colors,
                    layout_overrides=self.layout_overrides,
                    graph_key=self._current_graph_key())
```

- [ ] **Step 6: 실행 — 통과 확인**

Run: `pytest tests/app/test_main_window_node_menu.py -v`
Expected: 5 passed

- [ ] **Step 7: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 8: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

샘플 그래프 열어:
- 노드 드래그 가능
- 노드 우클릭 → "이 노드 모두 펼침" 동작
- "원래 위치로 되돌리기" 동작
- 다른 토글 후에도 드래그한 위치 유지
- 연결선이 곡선으로 그려짐

- [ ] **Step 9: 커밋**

```bash
git add tests/app/test_main_window_node_menu.py src/t3dgraph/core/app/main_window.py src/t3dgraph/core/app/scene.py
git commit -m "feat(app): MainWindow node context menu + LayoutOverrides wiring (F18+F19)"
```

---

## Self-Review 체크리스트

- Spec §5 cubic bezier — Task 1 ✅
- Spec §5 백워드 핸들 확장 — Task 1 Step 1 `test_backward_handle_extended` ✅
- Spec §7.2 LayoutOverrides 클래스 — Task 2 ✅
- Spec §7.3 NodeItem flags + itemChange — Task 3 ✅
- Spec §7.4 scene.populate override 적용 — Task 4 ✅
- Spec §7.5 MainWindow 보유 + 와이어링 — Task 7 ✅
- Spec §7.6 컨텍스트 메뉴 "원래 위치로" — Task 7 ✅
- Spec §8.2 contextMenuEvent — Task 6 ✅
- Spec §8.3 ViewState helper — Task 5 ✅
- Spec §8.4 메뉴 슬롯 — Task 7 ✅
- Spec §9.2 graph_key 도출 — Task 7 Step 4 `_current_graph_key` ✅
- PRESERVE-ALL — 위치/펼침 set 변경만, 모델 무변경 ✅

---

## 완료 후

머지 후:
- 슬라이스 ξ 플랜 (F15) — 인스펙터 레이아웃
- F11(Spec 2 진입 시)에서 `_current_graph_key`를 공용 모듈로 추출 검토
