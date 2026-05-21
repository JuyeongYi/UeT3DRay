# Slice γ: UX·API 잡정리 (C-A3 + C-B1 + C-B2 + C-B3 + D-B1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** improver 백로그에서 작고 독립적인 정리 5건을 묶음 처리. UX 어포던스(chevron 마우스 hover/툴팁), API 의미 정돈(`GraphStack.push` 사전조건·테스트 전용 API private), 메모리/시그널 비용(`_NodeItemBus` lazy), 타입힌트(`show_data_flow`).

**Architecture:** 각 항목이 독립 파일·독립 동작. 한 슬라이스에 묶었지만 task별로 Commit boundary 분리.

**Tech Stack:** Python 3.11+, PySide6, pytest, pytest-qt.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-batch-3-info-preservation-design.md` §5.4.

**의존:** slice α와 git 충돌 영역 없음(α는 data_flow·paths·panel을 건드림, γ는 items·scene·graph_stack·breadcrumb·contracts·main_window의 *다른 부분*). β와도 독립.

---

## 파일 구조

| 파일 | 책임 | 변경 |
|---|---|---|
| `src/t3dgraph/core/app/items.py` | chevron 어포던스 + `_NodeItemBus` lazy | 수정 |
| `src/t3dgraph/core/app/graph_stack.py` | `push` 빈-스택 폴백 제거 | 수정 |
| `src/t3dgraph/core/app/breadcrumb_bar.py` | `click_segment` → `_click_for_test` | 수정 |
| `src/t3dgraph/core/app/contracts.py` · `main_window.py` | `show_data_flow` 타입힌트 (slice α에서 처리 안 된 잔여 — α와 겹치면 skip) | 수정 |
| `tests/core/app/test_subgraph_node_chevron.py` | 어포던스 단위 | 수정 |
| `tests/core/app/test_graph_stack.py` | push 사전조건 | 수정 |
| `tests/core/app/test_node_item_bus_lazy.py` | lazy bus | 신규 |

---

### Task 1: chevron 어포던스 (C-A3)

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `tests/core/app/test_subgraph_node_chevron.py`

- [ ] **Step 1: Test**

`tests/core/app/test_subgraph_node_chevron.py`에 추가:

```python
from PySide6.QtCore import Qt
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.base.graph_model import Node, GraphModel


def test_subgraph_node_uses_pointing_hand_cursor(qapp):
    node = Node(name="P", cls=None, subgraph=GraphModel(label="x"))
    item = NodeItem(node)
    assert item.cursor().shape() == Qt.PointingHandCursor


def test_subgraph_node_has_drilldown_tooltip(qapp):
    node = Node(name="P", cls=None, subgraph=GraphModel(label="x"))
    item = NodeItem(node)
    tooltip = item.toolTip()
    assert "더블클릭" in tooltip


def test_non_subgraph_node_no_special_cursor(qapp):
    node = Node(name="X", cls=None)
    item = NodeItem(node)
    # 기본 커서(ArrowCursor) 또는 셋 안 함
    shape = item.cursor().shape()
    assert shape != Qt.PointingHandCursor
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: 변경**

`items.py` `NodeItem.__init__` 끝에 chevron 분기와 함께:

```python
if node.subgraph is not None:
    chev = QGraphicsSimpleTextItem("▶", self)
    chev.setBrush(QBrush(QColor(200, 200, 120)))
    chev.setPos(NODE_WIDTH - 16, 5)
    self.setCursor(Qt.PointingHandCursor)
    self.setToolTip("더블클릭하여 서브그래프 진입")
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/items.py tests/core/app/test_subgraph_node_chevron.py
git commit -m "feat(items): pointing-hand cursor + tooltip on subgraph nodes (C-A3)"
```

---

### Task 2: `_NodeItemBus` lazy-init (C-B3)

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/core/app/test_node_item_bus_lazy.py`

- [ ] **Step 1: Test**

```python
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.base.graph_model import Node, Pin, GraphModel


def test_bus_not_created_for_bare_node(qapp):
    node = Node(name="X", cls=None)        # 핀 없음, subgraph 없음
    item = NodeItem(node)
    assert item._bus is None


def test_bus_created_for_subgraph_node(qapp):
    node = Node(name="P", cls=None, subgraph=GraphModel())
    item = NodeItem(node)
    assert item._bus is not None
    assert hasattr(item._bus, "enter_subgraph_requested")


def test_bus_created_for_pinned_node(qapp):
    node = Node(name="N", cls=None,
                pins=[Pin(name="P", cpp_type="int", direction="Input")])
    item = NodeItem(node)
    assert item._bus is not None


def test_bare_node_double_click_does_not_emit_signals(qapp):
    """bus 없는 노드의 double click은 super()로 통과 — 시그널 발사 안 함."""
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent
    from PySide6.QtCore import QEvent, Qt
    node = Node(name="X", cls=None)
    item = NodeItem(node)
    # bus 미존재 — 호출이 AttributeError 안 나야 함
    event = QGraphicsSceneMouseEvent(QEvent.GraphicsSceneMouseDoubleClick)
    event.setPos(QPointF(10, 10))
    event.setButton(Qt.LeftButton)
    try:
        item.mouseDoubleClickEvent(event)
    except AttributeError as e:
        pytest_fail = e
        raise
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: 변경**

`items.py`:

```python
class NodeItem(QGraphicsRectItem):
    def __init__(self, node, *, ...):
        ...
        self._bus: _NodeItemBus | None = None
        if node.subgraph is not None or any(...):    # 핀 보유 등 시그널 필요 조건
            self._bus = _NodeItemBus()
        ...

    @property
    def bus(self) -> _NodeItemBus | None:
        return self._bus

    def mouseDoubleClickEvent(self, event):
        if self._bus is None:
            super().mouseDoubleClickEvent(event)
            return
        y = event.pos().y()
        if y < HEADER_HEIGHT and self.node.subgraph is not None:
            self._bus.enter_subgraph_requested.emit(self.node.name)
            event.accept()
            return
        # 핀 행 영역
        row = int((y - HEADER_HEIGHT) / ROW_HEIGHT)
        if 0 <= row < len(self._row_paths):
            self._bus.pin_toggle_requested.emit(self._row_paths[row])
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
```

`GraphScene.populate`도 bus가 있을 때만 연결:

```python
if item.bus is not None:
    item.bus.enter_subgraph_requested.connect(self.enter_subgraph_requested)
    item.bus.pin_toggle_requested.connect(self.pin_toggle_requested)
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py \
        tests/core/app/test_node_item_bus_lazy.py
git commit -m "perf(items): lazy-init _NodeItemBus (C-B3)"
```

---

### Task 3: `GraphStack.push` 빈-스택 폴백 제거 (C-B1)

**Files:**
- Modify: `src/t3dgraph/core/app/graph_stack.py`
- Modify: `tests/core/app/test_graph_stack.py`

- [ ] **Step 1: Test**

```python
import pytest
from t3dgraph.core.app.graph_stack import GraphStack
from t3dgraph.core.base.graph_model import GraphModel


def test_push_on_empty_stack_raises():
    s = GraphStack()
    with pytest.raises(RuntimeError, match="open_root"):
        s.push(GraphModel(label="x"))


def test_push_after_open_root_works():
    s = GraphStack()
    s.open_root(GraphModel(label="root"))
    s.push(GraphModel(label="child"))
    assert s.current().label == "child"
```

기존 `test_initial_empty`·`test_push_and_current` 중 `push`만 단독 호출하는 케이스가 있으면 `open_root` 호출 추가하도록 갱신.

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: 변경**

`graph_stack.py` `push`:

```python
def push(self, g: GraphModel) -> None:
    if self._cur_root < 0:
        raise RuntimeError(
            "GraphStack.push 전에 open_root가 호출되어야 합니다 "
            "(빈 스택 폴백 제거 — C-B1)"
        )
    self._paths[self._cur_root].append(g)
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/graph_stack.py tests/core/app/test_graph_stack.py
git commit -m "refactor(graph_stack): push requires open_root precondition (C-B1)"
```

---

### Task 4: 테스트 전용 API → private (C-B2)

**Files:**
- Modify: `src/t3dgraph/core/app/breadcrumb_bar.py`
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: 호출 테스트 파일들

- [ ] **Step 1: 변경 — 두 메서드 rename**

`breadcrumb_bar.py`:

```python
def _click_for_test(self, index: int) -> None:
    """테스트 전용 — 헤드리스에서 시그널 트리거. 프로덕션 코드는 호출 금지."""
    if 0 <= index < len(self._buttons):
        self._buttons[index].click()
```

기존 `click_segment` 제거.

`items.py`:

```python
def _emit_enter_subgraph_for_test(self) -> None:
    """테스트 전용 — 헤더 더블클릭 시그널 직접 발사."""
    if self._bus is not None and self.node.subgraph is not None:
        self._bus.enter_subgraph_requested.emit(self.node.name)
```

기존 `simulate_header_double_click` 제거.

- [ ] **Step 2: 호출 테스트 일괄 치환**

```
grep -rln "simulate_header_double_click\|\.click_segment(" tests
```

각 파일에서 호출명 갱신:
- `bar.click_segment(i)` → `bar._click_for_test(i)`
- `item.simulate_header_double_click()` → `item._emit_enter_subgraph_for_test()`

- [ ] **Step 3: Run — pass**

```
pytest tests/ -x
```

- [ ] **Step 4: Commit**

```
git add src/t3dgraph/core/app/breadcrumb_bar.py src/t3dgraph/core/app/items.py tests/
git commit -m "refactor: mark test-only widget hooks as _private (C-B2)"
```

---

### Task 5: `show_data_flow` 타입힌트 (D-B1) — α와 중복 시 skip

**Files:**
- Modify: `src/t3dgraph/core/app/contracts.py` (있다면)
- Modify: `src/t3dgraph/core/app/main_window.py`

slice α Task 6에서 이미 처리한 경우 git diff로 확인 후 skip.

- [ ] **Step 1: 상태 확인**

```
grep -n "show_data_flow" src/t3dgraph/core/app/contracts.py src/t3dgraph/core/app/main_window.py
```

타입힌트가 `result: DataFlowResult`로 되어 있으면 본 Task PASS, 다음으로.

- [ ] **Step 2: 변경 (필요 시)**

`from ..analysis.data_flow import DataFlowResult` import 후:

```python
def show_data_flow(self, result: DataFlowResult) -> None:
    ...
```

- [ ] **Step 3: 회귀**

```
pytest tests/ -x
```

- [ ] **Step 4: Commit (변경 있었으면)**

```
git add src/t3dgraph/core/app/contracts.py src/t3dgraph/core/app/main_window.py
git commit -m "refactor(contracts): type-hint show_data_flow(DataFlowResult) (D-B1)"
```

---

### Task 6: 전체 회귀

- [ ] **Step 1**

```
pytest tests/ -v
```
Expected: PASS.

- [ ] **Step 2**: 변경 없으면 commit 안 함.

---

## 완료 정의

- [ ] Task 1-6 PASS
- [ ] subgraph 보유 노드에 hand cursor + tooltip
- [ ] `_NodeItemBus`가 필요한 노드(subgraph/핀)만 생성
- [ ] `GraphStack.push`가 사전조건 위반 시 RuntimeError
- [ ] 테스트 전용 API가 `_` prefix
- [ ] `show_data_flow` 타입힌트 반영
