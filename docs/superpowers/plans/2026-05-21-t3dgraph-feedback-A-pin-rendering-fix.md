# Slice A: 핀 렌더링 버그 정정 (F7, F8, F9 일부) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "연결된 핀만" 옵션의 부정확성(F7)·핀 행 2배(F8)를 고치고, 깊이 펼침을 per-pin 단위로 분리(F9)한다.

**Architecture:** `_collect_rows`를 재작성하되, `view_state.expand_subpins`(전역) 대신 `ViewState.expanded_pin_paths` set으로 per-pin 펼침 상태를 보관. `_connected_paths_by_node`는 sub-pin 연결을 prefix 클로저로 부모까지 승급. 펼쳐진 부모 행은 dot/anchor 없이 라벨만 — 자식 행이 anchor 역할.

**Tech Stack:** Python 3.11+, PySide6 (Qt6), pytest, pytest-qt.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-user-feedback-batch-design.md` §5.7, §5.8.

**노드 보존 불변식(PRESERVE-ALL):** 본 슬라이스의 어떤 코드 경로도 그래프 모델의 노드를 드롭하지 않는다. 필터·뷰모드·펼침 — 가시성 토글로만 표현.

---

## 파일 구조

| 파일 | 책임 | 변경 종류 |
|---|---|---|
| `src/t3dgraph/core/app/view_state.py` | per-pin 펼침 상태 보관 + connected_only 토글 | 수정 |
| `src/t3dgraph/core/app/items.py` | `_collect_rows` 재작성 + 부모/자식 dot 정책 | 수정 |
| `src/t3dgraph/core/app/scene.py` | `_connected_paths_by_node` prefix closure + 펼침 클릭 라우팅 | 수정 |
| `src/t3dgraph/core/app/main_window.py` | 툴바: "깊이 펼침"(전역 토글) → "전체 펼침"/"전체 접기" 2 액션 | 수정 |
| `tests/core/app/test_view_state.py` | per-pin expand state 단위 | 수정 |
| `tests/core/app/test_items_rows.py` | `_collect_rows` 케이스 단위 | 신규 |
| `tests/core/app/test_main_window_pin_filter.py` | "연결된 핀만"+"펼침" 통합 (pytest-qt) | 신규 |

---

### Task 1: ViewState — per-pin 펼침 상태 추가

**Files:**
- Modify: `src/t3dgraph/core/app/view_state.py`
- Test: `tests/core/app/test_view_state.py`

- [ ] **Step 1: Write the failing test**

`tests/core/app/test_view_state.py`에 추가 (파일 없으면 신규):

```python
from t3dgraph.core.app.view_state import ViewState


def test_pin_expand_toggle_round_trip():
    vs = ViewState()
    path = "MyNode.MyPin"
    assert vs.is_pin_expanded(path) is False
    vs.toggle_pin_expanded(path)
    assert vs.is_pin_expanded(path) is True
    vs.toggle_pin_expanded(path)
    assert vs.is_pin_expanded(path) is False


def test_expand_all_and_collapse_all():
    vs = ViewState()
    vs.expand_all_pins(["N.A", "N.B", "N.A.X"])
    assert vs.is_pin_expanded("N.A") is True
    assert vs.is_pin_expanded("N.B") is True
    assert vs.is_pin_expanded("N.A.X") is True
    vs.collapse_all_pins()
    assert vs.is_pin_expanded("N.A") is False
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/core/app/test_view_state.py -k "pin_expand" -v
```
Expected: FAIL (`AttributeError: 'ViewState' object has no attribute 'is_pin_expanded'`).

- [ ] **Step 3: Implement**

`src/t3dgraph/core/app/view_state.py` — 기존 `expand_subpins: bool`은 **하위호환을 위해 유지**(상위 토글 액션에서 변환 처리). `expanded_pin_paths: set[str]`을 추가하고 메서드 3개:

```python
# 클래스 본문에 추가 (기존 필드 옆)
expanded_pin_paths: set[str] = field(default_factory=set)

def is_pin_expanded(self, full_path: str) -> bool:
    return full_path in self.expanded_pin_paths

def toggle_pin_expanded(self, full_path: str) -> None:
    if full_path in self.expanded_pin_paths:
        self.expanded_pin_paths.remove(full_path)
    else:
        self.expanded_pin_paths.add(full_path)

def expand_all_pins(self, paths: list[str]) -> None:
    self.expanded_pin_paths.update(paths)

def collapse_all_pins(self) -> None:
    self.expanded_pin_paths.clear()
```

`@dataclass`이면 `field`는 이미 import 되어 있을 것 — 없으면 `from dataclasses import field` 확인.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/core/app/test_view_state.py -k "pin_expand or expand_all" -v
```
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/view_state.py tests/core/app/test_view_state.py
git commit -m "feat(view_state): per-pin expand state (F9 prep)"
```

---

### Task 2: Scene — 연결 경로의 prefix closure

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py:54-59` (메서드 `_connected_paths_by_node`)
- Test: `tests/core/app/test_items_rows.py` (신규, Task 3에서 채움)

이 Task에서는 **헬퍼 함수만** 추가/수정한다(테스트는 Task 3 단위 테스트와 함께).

- [ ] **Step 1: Inline test (scene 내부 함수만 빠르게 검증)**

`tests/core/app/test_scene_helpers.py`(신규):

```python
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.base.graph_model import GraphModel, Node, Link


def test_connected_paths_includes_parent_prefixes():
    g = GraphModel(
        nodes=[Node(name="A", cls=None), Node(name="B", cls=None)],
        links=[Link(source_path="A.OutPin.Sub", target_path="B.InPin")],
    )
    by_node = GraphScene._connected_paths_by_node(g)
    # sub-pin 연결이 부모로 승급되어야 함
    assert "A.OutPin.Sub" in by_node["A"]
    assert "A.OutPin" in by_node["A"]            # ← prefix closure
    assert "B.InPin" in by_node["B"]
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_scene_helpers.py -v
```
Expected: FAIL (`A.OutPin` not in set).

- [ ] **Step 3: Modify `_connected_paths_by_node`**

`src/t3dgraph/core/app/scene.py`:

```python
@staticmethod
def _connected_paths_by_node(graph: GraphModel) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for link in graph.links:
        for path in (link.source_path, link.target_path):
            node = pin_segment(path, 0)
            bucket = out.setdefault(node, set())
            # 전체 경로 + 그 위 모든 prefix를 등록 — sub-pin 연결을 부모로 승급
            parts = path.split(".")
            for i in range(2, len(parts) + 1):       # "Node.Pin" 부터 전체까지
                bucket.add(".".join(parts[:i]))
    return out
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_scene_helpers.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/scene.py tests/core/app/test_scene_helpers.py
git commit -m "fix(scene): connected paths include parent prefixes (F7)"
```

---

### Task 3: items — `_collect_rows` 재작성 + 부모/자식 dot 정책

**Files:**
- Modify: `src/t3dgraph/core/app/items.py:61-91` (메서드 `_collect_rows`, `__init__` dot 그리기 부분)
- Test: `tests/core/app/test_items_rows.py` (신규)

`NodeItem.__init__`는 PySide6 QGraphicsRectItem 상속 — 단위 테스트는 그리기를 우회하기 어렵다. 따라서 `_collect_rows`를 **모듈 함수**로 추출해 단위 테스트하고, `__init__`는 그 함수를 호출하도록 변경한다.

- [ ] **Step 1: Failing tests**

`tests/core/app/test_items_rows.py`:

```python
from t3dgraph.core.app.items import collect_pin_rows
from t3dgraph.core.base.graph_model import Node, Pin


def _make_node():
    return Node(
        name="N",
        cls=None,
        pins=[
            Pin(name="ExecIn", cpp_type="FRigVMExecuteContext", direction="Input"),
            Pin(name="Struct", cpp_type="FVector", direction="Input",
                subpins=[
                    Pin(name="X", cpp_type="float", direction="Input"),
                    Pin(name="Y", cpp_type="float", direction="Input"),
                ]),
        ],
    )


def test_collect_rows_default_top_level_only():
    node = _make_node()
    rows = collect_pin_rows(node, connected_subtree=frozenset(),
                            connected_only=False, expanded=frozenset())
    # 펼침 0개 — top-level만
    paths = [r.path for r in rows]
    assert paths == ["N.ExecIn", "N.Struct"]
    # 모두 dot/anchor 가짐
    assert all(r.has_dot for r in rows)


def test_collect_rows_expanded_parent_has_no_dot():
    node = _make_node()
    rows = collect_pin_rows(node, connected_subtree=frozenset(),
                            connected_only=False,
                            expanded=frozenset({"N.Struct"}))
    paths = [r.path for r in rows]
    assert paths == ["N.ExecIn", "N.Struct", "N.Struct.X", "N.Struct.Y"]
    # 부모(N.Struct)는 자식이 펼쳐졌으므로 dot 제거 (F8)
    by_path = {r.path: r for r in rows}
    assert by_path["N.Struct"].has_dot is False
    assert by_path["N.Struct.X"].has_dot is True
    assert by_path["N.Struct.Y"].has_dot is True


def test_connected_only_includes_parent_when_sub_connected():
    node = _make_node()
    # sub-pin이 연결 — prefix closure로 "N.Struct"도 포함되어 있다고 가정
    rows = collect_pin_rows(
        node,
        connected_subtree=frozenset({"N.Struct", "N.Struct.X"}),
        connected_only=True,
        expanded=frozenset(),
    )
    paths = [r.path for r in rows]
    # 부모는 포함, exec/미연결은 제외 (F7)
    assert paths == ["N.Struct"]


def test_connected_only_with_expand_shows_both_but_no_dup_dot():
    node = _make_node()
    rows = collect_pin_rows(
        node,
        connected_subtree=frozenset({"N.Struct", "N.Struct.X"}),
        connected_only=True,
        expanded=frozenset({"N.Struct"}),
    )
    paths = [r.path for r in rows]
    assert paths == ["N.Struct", "N.Struct.X"]   # Y는 미연결 → 제외
    by_path = {r.path: r for r in rows}
    assert by_path["N.Struct"].has_dot is False  # 부모 dot 제거 (F8)
    assert by_path["N.Struct.X"].has_dot is True
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_items_rows.py -v
```
Expected: FAIL (`ImportError: cannot import name 'collect_pin_rows'`).

- [ ] **Step 3: Refactor items.py**

`src/t3dgraph/core/app/items.py` 상단에 추가:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PinRow:
    pin: Pin
    path: str        # full path "Node.Pin..."
    depth: int
    has_dot: bool    # anchor dot 그릴지 여부 — 자식 펼쳐진 부모는 False


def collect_pin_rows(
    node: Node,
    *,
    connected_subtree: frozenset[str],
    connected_only: bool,
    expanded: frozenset[str],
) -> list[PinRow]:
    """노드의 핀 트리를 행 시퀀스로 평탄화.

    - `connected_only`: True일 때 `connected_subtree`에 path가 있을 때만 행 포함.
      (subtree set은 sub-pin 연결을 부모로 승급한 closure — 호출부에서 보장.)
    - `expanded`: 펼쳐진 pin path set. 부모 path가 들어있을 때만 자식 행 추가.
    - 부모 행은 자기 path가 expanded에 있고 *자식 행이 실제로 추가됐을 때*
      `has_dot=False` — 자식이 anchor 역할(F8 dot 중복 방지).
    """
    rows: list[PinRow] = []

    def walk(pin: Pin, path: str, depth: int) -> bool:
        """리턴: 이 pin 자신 또는 자손이 행으로 추가됐는가?"""
        include_self = (not connected_only) or (path in connected_subtree)
        children_added = False
        if path in expanded:
            for sp in pin.subpins:
                child_path = f"{path}.{sp.name}"
                if walk(sp, child_path, depth + 1):
                    children_added = True
        if include_self:
            has_dot = not children_added
            rows.append(PinRow(pin=pin, path=path, depth=depth, has_dot=has_dot))
            return True
        return children_added

    # walk가 children → self 순으로 추가하므로 자식이 부모보다 먼저 들어감.
    # 부모를 자식보다 먼저 보이게 하려면 row 리스트를 후처리해야 함.
    # → 구현을 self-first로 바꾸되, "부모 dot 결정"은 자식 walk 후 알 수 있으므로
    #   행을 일단 placeholder로 넣고, walk 끝나면 patch.
    rows.clear()

    def walk2(pin: Pin, path: str, depth: int) -> bool:
        include_self = (not connected_only) or (path in connected_subtree)
        my_idx: int | None = None
        if include_self:
            my_idx = len(rows)
            rows.append(PinRow(pin=pin, path=path, depth=depth, has_dot=True))
        children_added = False
        if path in expanded:
            for sp in pin.subpins:
                child_path = f"{path}.{sp.name}"
                if walk2(sp, child_path, depth + 1):
                    children_added = True
        if my_idx is not None and children_added:
            cur = rows[my_idx]
            rows[my_idx] = PinRow(pin=cur.pin, path=cur.path,
                                  depth=cur.depth, has_dot=False)
        return include_self or children_added

    for pin in node.pins:
        walk2(pin, f"{node.name}.{pin.name}", 0)
    return rows
```

그리고 `NodeItem.__init__`에서 기존 `_collect_rows` 호출을 `collect_pin_rows`로 교체:

```python
def __init__(self, node, *, connected_paths=frozenset(), connected_only=False,
             expanded_paths=frozenset(), highlighted=False):
    self.node = node
    rows = collect_pin_rows(node, connected_subtree=connected_paths,
                            connected_only=connected_only,
                            expanded=expanded_paths)
    height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
    super().__init__(QRectF(0, 0, NODE_WIDTH, height))
    # … 기존 헤더 코드 …
    self._rows: dict[str, float] = {}
    for i, row in enumerate(rows):
        cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
        self._rows[row.path] = cy
        is_input = (row.pin.direction or "").lower() != "output"
        mx = 0.0 if is_input else NODE_WIDTH
        if row.has_dot:
            dot = QGraphicsEllipseItem(
                mx - PIN_RADIUS, cy - PIN_RADIUS,
                2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
            dot.setBrush(QBrush(QColor(200, 200, 120)))
            dot.setPen(QPen(Qt.NoPen))
        label = QGraphicsSimpleTextItem(row.pin.name, self)
        label.setBrush(QBrush(QColor(210, 210, 210)))
        indent = 8 + row.depth * 12
        lx = indent if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
        label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)
```

기존 `_collect_rows` 정적 메서드는 **삭제**.

기존 `show_subpins` 파라미터는 호출부 모두 정리 — Task 4에서 scene.populate 시그니처 변경.

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_items_rows.py -v
```
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/items.py tests/core/app/test_items_rows.py
git commit -m "refactor(items): extract collect_pin_rows; fix parent dot (F7, F8)"
```

---

### Task 4: Scene — `expanded_paths` 전달 + populate 시그니처 정리

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py` (`populate` 본문 NodeItem 호출부)

- [ ] **Step 1: 변경**

`populate`의 NodeItem 생성부:

```python
for node in graph.nodes:
    item = NodeItem(
        node,
        connected_paths=frozenset(connected.get(node.name, set())),
        connected_only=vs.connected_pins_only,
        expanded_paths=frozenset(
            p for p in vs.expanded_pin_paths if p.startswith(f"{node.name}.")
        ),
        highlighted=vs.fan_in_highlight and node.name in convergence,
    )
    ...
```

기존 `show_subpins=vs.expand_subpins`는 **제거**. `vs.expand_subpins` 필드 자체도 다음 Task에서 처리.

- [ ] **Step 2: Run 전체 테스트 (회귀 확인)**

```
pytest tests/ -x
```
Expected: 일부 기존 통합 테스트가 시그니처 변경/expand_subpins 의존으로 실패할 수 있음 — 다음 Task에서 처리.

- [ ] **Step 3: Commit (회귀가 남아 있어도 일단 — 다음 Task에서 마무리)**

```
git add src/t3dgraph/core/app/scene.py
git commit -m "refactor(scene): pass expanded_paths to NodeItem"
```

---

### Task 5: MainWindow — 툴바 액션 재배치 + `expand_subpins` 제거

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py:63-86`
- Modify: `src/t3dgraph/core/app/view_state.py` (`expand_subpins`·`set_expand_subpins` 제거)

- [ ] **Step 1: 변경 — toolbar**

`_build_view_mode_toolbar` 재작성:

```python
def _build_view_mode_toolbar(self) -> None:
    from PySide6.QtGui import QAction
    toolbar = self.addToolBar("뷰 모드")
    self._view_mode_actions: dict[str, QAction] = {}

    # 토글 액션 — 상태 보유
    toggles = (
        ("connected_only", "연결된 핀만",
         self.view_state.set_connected_pins_only, False),
        ("fan_in_highlight", "fan-in 강조",
         self.view_state.set_fan_in_highlight, True),
    )
    for mode_id, label, setter, in_place in toggles:
        action = QAction(label, self)
        action.setCheckable(True)
        action.toggled.connect(
            lambda checked, s=setter, ip=in_place: self._on_view_mode(s, checked, ip))
        toolbar.addAction(action)
        self._view_mode_actions[mode_id] = action

    # 명령(non-stateful) — 전체 펼침/접기
    expand_all = QAction("전체 펼침", self)
    expand_all.triggered.connect(self._on_expand_all_pins)
    toolbar.addAction(expand_all)
    self._view_mode_actions["expand_all"] = expand_all

    collapse_all = QAction("전체 접기", self)
    collapse_all.triggered.connect(self._on_collapse_all_pins)
    toolbar.addAction(collapse_all)
    self._view_mode_actions["collapse_all"] = collapse_all

def _on_expand_all_pins(self) -> None:
    if self.graph is None:
        return
    paths: list[str] = []
    def walk(node_name, pin, prefix):
        path = f"{prefix}.{pin.name}"
        paths.append(path)
        for sp in pin.subpins:
            walk(node_name, sp, path)
    for n in self.graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    self.view_state.expand_all_pins(paths)
    self._rebuild_scene()

def _on_collapse_all_pins(self) -> None:
    self.view_state.collapse_all_pins()
    self._rebuild_scene()
```

`set_view_mode` 메서드의 mode_id 목록 갱신 (`connected_only` / `fan_in_highlight` 만 토글; `expand_all`/`collapse_all`은 트리거).

- [ ] **Step 2: ViewState 정리**

`src/t3dgraph/core/app/view_state.py`에서:
- `expand_subpins: bool` 필드 제거
- `set_expand_subpins` 메서드 제거

- [ ] **Step 3: Run 전체 회귀 테스트**

```
pytest tests/ -x
```
Expected: PASS — `expand_subpins` 의존 기존 테스트가 있으면 적절히 `expanded_pin_paths`로 갱신.

회귀 잡힌 테스트는 인라인 수정 (예: `view_state.expand_subpins = True` 호출이 있다면 `view_state.expand_all_pins([...])`로).

- [ ] **Step 4: Commit**

```
git add src/t3dgraph/core/app/main_window.py src/t3dgraph/core/app/view_state.py tests/
git commit -m "feat(main_window): expand-all/collapse-all actions; drop global expand_subpins (F9)"
```

---

### Task 6: pin label 클릭 — per-pin 토글

**Files:**
- Modify: `src/t3dgraph/core/app/items.py` (라벨 클릭 시그널)
- Modify: `src/t3dgraph/core/app/scene.py` (시그널 라우팅 → ViewState 토글 → populate 재실행)
- Modify: `src/t3dgraph/core/app/main_window.py` (scene 시그널 연결)

`QGraphicsSimpleTextItem`은 시그널이 없는 plain item. 클릭 받으려면 `QGraphicsItem.mousePressEvent`를 override 한 subclass 필요. 또는 NodeItem 자체의 mousePressEvent에서 클릭 좌표 → 어떤 핀인지 결정.

가장 단순한 방법: `NodeItem.mouseDoubleClickEvent` 사용 — 더블클릭으로 펼침/접힘 토글. (단일 클릭은 선택용으로 유지.)

- [ ] **Step 1: Test (pytest-qt — 더블클릭으로 펼침 토글)**

`tests/core/app/test_main_window_pin_filter.py` (신규):

```python
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _graph_with_struct_pin():
    return GraphModel(
        nodes=[
            Node(name="N", cls=None, pins=[
                Pin(name="V", cpp_type="FVector", direction="Input", subpins=[
                    Pin(name="X", cpp_type="float", direction="Input"),
                    Pin(name="Y", cpp_type="float", direction="Input"),
                ]),
            ]),
        ],
        links=[],
    )


def test_pin_double_click_toggles_expand(qapp):
    win = MainWindow()
    g = _graph_with_struct_pin()
    win.show_graph(g)
    item = win.scene.node_item("N")
    assert item is not None
    # 초기엔 V만 (자식 미펼침)
    assert "N.V" in item._rows
    assert "N.V.X" not in item._rows
    # V 라벨 영역(top-left ~ NODE_WIDTH 사이 첫 row) 더블클릭 시뮬레이션
    item.toggle_pin_at_row(0)               # row index 0 = V
    win._rebuild_scene()
    item2 = win.scene.node_item("N")
    assert "N.V.X" in item2._rows


def test_preserve_all_nodes_after_expand(qapp):
    win = MainWindow()
    g = _graph_with_struct_pin()
    win.show_graph(g)
    win._on_expand_all_pins()
    # 노드 보존 불변식
    assert set(win.scene._nodes.keys()) >= {n.name for n in g.nodes}
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_main_window_pin_filter.py -v
```
Expected: FAIL (`toggle_pin_at_row` missing).

- [ ] **Step 3: items.py — toggle hook + double-click handler**

`NodeItem`에 추가:

```python
from PySide6.QtCore import QObject, Signal


# 모듈 레벨에 시그널 owner — NodeItem이 QGraphicsItem이라 Signal 직접 못 가짐
class _NodeItemBus(QObject):
    pin_toggle_requested = Signal(str)   # full_path


# NodeItem.__init__ 끝 부분에:
    self.bus = _NodeItemBus()
    self._row_paths: list[str] = [r.path for r in rows]

def toggle_pin_at_row(self, row_index: int) -> None:
    if 0 <= row_index < len(self._row_paths):
        self.bus.pin_toggle_requested.emit(self._row_paths[row_index])

def mouseDoubleClickEvent(self, event):  # QGraphicsItem hook
    # event.pos() — item local coord
    y = event.pos().y()
    row = int((y - HEADER_HEIGHT) / ROW_HEIGHT)
    if 0 <= row < len(self._row_paths):
        self.toggle_pin_at_row(row)
        event.accept()
        return
    super().mouseDoubleClickEvent(event)
```

`Signal`은 `QObject`만 보유 가능. `_NodeItemBus`를 NodeItem 멤버로 두는 패턴.

- [ ] **Step 4: scene + main_window 시그널 연결**

`GraphScene`에 시그널:

```python
from PySide6.QtCore import Signal, QObject

class GraphScene(QGraphicsScene):
    pin_toggle_requested = Signal(str)

    # populate 끝부분 — NodeItem 추가 후
    for node in graph.nodes:
        item = NodeItem(...)
        ...
        item.bus.pin_toggle_requested.connect(self.pin_toggle_requested)
```

`MainWindow._wire`에:

```python
self.scene.pin_toggle_requested.connect(self._on_pin_toggle)

def _on_pin_toggle(self, full_path: str) -> None:
    self.view_state.toggle_pin_expanded(full_path)
    self._rebuild_scene()
```

- [ ] **Step 5: Run — pass**

```
pytest tests/core/app/test_main_window_pin_filter.py -v
```
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```
git add src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py \
        src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window_pin_filter.py
git commit -m "feat(items): double-click pin row to toggle expand (F9)"
```

---

### Task 7: 통합 회귀 + Orion 샘플 smoke

**Files:**
- Run: `pytest tests/ -v` (전체)
- Optional: `tests/test_integration_orion.py` 가 있으면 확인

- [ ] **Step 1: 전체 테스트 실행**

```
pytest tests/ -v
```
Expected: 모든 테스트 PASS. 노드 수가 변경되어 깨지는 단위 테스트가 있으면 expected count 갱신(노드 개수 변경 아니라 *행* 개수 변경 — 단위가 view 결과면 그에 맞춰).

- [ ] **Step 2: smoke — Orion RigVMModel 열기 (스크립트로 처리)**

`tests/smoke_open_rigvmmodel.py`(신규, 별도 실행):

```python
"""smoke — 샘플 파일을 로드해 노드 수가 보존되는지 확인."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from pathlib import Path

p = Path("Orion_WorkStation_Rig_Analysis/"
         "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
doc = parse_document(read_t3d_text(p))
plugin = default_registry().detect(doc)
graph = plugin.interpreter_factory().interpret(doc)
print(f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}")
assert len(graph.nodes) > 0
```

실행: `python tests/smoke_open_rigvmmodel.py`

Expected: 양수 노드 수 출력, AssertionError 없음.

- [ ] **Step 3: Commit (smoke 추가했으면)**

```
git add tests/smoke_open_rigvmmodel.py
git commit -m "test: smoke for Orion RigVMModel load (preserve-all check)"
```

---

## 완료 정의

- [ ] 모든 Task 1-7 체크박스 PASS
- [ ] 새/기존 테스트 전체 PASS
- [ ] PRESERVE-ALL 불변식 — `len(scene._nodes) >= len(graph.nodes)` 어서션이 통합 테스트에 존재
- [ ] "연결된 핀만" + "펼침" 조합에서 부모 행 dot이 자식 dot과 중복되지 않음
- [ ] 노드 더블클릭이 아닌 *핀 행* 더블클릭으로 per-pin 펼침 토글
- [ ] 툴바에 "전체 펼침", "전체 접기" 2개 액션 존재; "깊이 펼침" 토글 제거
