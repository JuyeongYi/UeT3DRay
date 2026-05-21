# Slice C: ContainedGraph 재귀 + 그래프 스택 + 브레드크럼 (F6 내부, F5) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CollapseNode/FunctionReferenceNode 내부의 `ContainedGraph`를 재귀 파싱해 `Node.subgraph`에 부착(F6 — 같은 에셋 한정). MainWindow에 그래프 스택 + 브레드크럼 바를 추가해 서브그래프 드릴다운과 여러 파일 동시 열기를 지원(F5).

**Architecture:** `Node.subgraph: GraphModel | None` 슬롯. interpreter가 노드의 child object 중 RigVMGraph 컨테이너를 발견하면 동일 로직으로 재귀 호출. `core/app/graph_stack.py`(신규)가 `list[GraphModel]` 스택과 현재 인덱스 보관. `BreadcrumbBar` 위젯이 스택 세그먼트를 클릭 가능한 한 줄로 렌더. MainWindow는 단일 캔버스 + 상단 브레드크럼 바.

**Tech Stack:** Python 3.11+, PySide6, pytest, pytest-qt.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-user-feedback-batch-design.md` §5.4, §5.5, §7.4.

**의존:** Slice B 완료 후 — 브레드크럼 세그먼트 라벨이 `Node.display_name`을 사용. B 미완 상태에서도 동작은 하나(name fallback), 라벨이 클래스명이라 가독성 떨어짐.

**노드 보존 불변식(PRESERVE-ALL):**
- 부모 그래프의 노드 리스트는 자식 그래프 추출 시 그대로 유지. 자식 노드들은 *별도* GraphModel로.
- 그래프 스택 push/pop이 그래프 인스턴스를 변형(mutate)하지 않음 — 항상 같은 GraphModel 인스턴스를 가리킴.

---

## 파일 구조

| 파일 | 책임 | 변경 종류 |
|---|---|---|
| `src/t3dgraph/core/base/graph_model.py` | `Node.subgraph`, `GraphModel.label`/`parent_node`/`boundary_refs` | 수정 |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | ContainedGraph 자식 객체 재귀 → `Node.subgraph` 부착 | 수정 |
| `src/t3dgraph/plugins/rigvm/types.py` | `RigVMGraph` 클래스 접미사 상수 추가 | 수정 |
| `src/t3dgraph/core/app/graph_stack.py` | 스택 + 히스토리 자료구조 | 신규 |
| `src/t3dgraph/core/app/breadcrumb_bar.py` | 브레드크럼 위젯 (QToolBar 또는 QWidget) | 신규 |
| `src/t3dgraph/core/app/main_window.py` | 브레드크럼 통합 + 노드 더블클릭 시 push | 수정 |
| `src/t3dgraph/core/app/scene.py` | 노드 더블클릭 시그널 (서브그래프 진입 트리거) | 수정 |
| `src/t3dgraph/core/app/items.py` | 서브그래프 보유 노드 표시(아이콘/뱃지) — 옵셔널 | 수정 |
| `src/t3dgraph/core/app/controller.py` | `open_file`이 스택에 push (replace 아님) | 수정 |
| `tests/plugins/rigvm/test_interpreter_subgraph.py` | ContainedGraph 추출 단위 | 신규 |
| `tests/core/app/test_graph_stack.py` | 스택 API 단위 | 신규 |
| `tests/core/app/test_breadcrumb.py` | 브레드크럼 표시·클릭 | 신규 |
| `tests/core/app/test_subgraph_navigation.py` | end-to-end 진입/탈출 통합 | 신규 |

---

### Task 1: graph_model — Node.subgraph + GraphModel 메타 슬롯

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`

- [ ] **Step 1: Test**

`tests/core/base/test_graph_model.py`에 추가:

```python
from t3dgraph.core.base.graph_model import GraphModel, Node


def test_node_subgraph_default_none():
    n = Node(name="X", cls=None)
    assert n.subgraph is None


def test_node_subgraph_can_attach_graph_model():
    inner = GraphModel(label="inner")
    n = Node(name="Outer", cls=None, subgraph=inner)
    assert n.subgraph is inner
    assert n.subgraph.label == "inner"


def test_graph_model_meta_defaults():
    g = GraphModel()
    assert g.label is None
    assert g.parent_node is None
    assert g.boundary_refs == []
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/base/test_graph_model.py -v
```
Expected: FAIL.

- [ ] **Step 3: 변경**

`src/t3dgraph/core/base/graph_model.py`:

```python
@dataclass
class Node:
    name: str
    cls: str | None
    pins: list[Pin] = field(default_factory=list)
    position: tuple[float, float] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    is_generic: bool = False
    kind: str = "node"
    display_name: str | None = None           # B에서 추가
    role_summary: str | None = None           # B
    role_category: str | None = None          # B
    subgraph: "GraphModel | None" = None      # NEW (C)


@dataclass
class GraphModel:
    nodes: list[Node] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    variable_refs: list[VariableRef] = field(default_factory=list)
    external_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    label: str | None = None                  # NEW (C)
    parent_node: str | None = None            # NEW (C)
    boundary_refs: list[str] = field(default_factory=list)   # NEW (C, §7.4)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/base/test_graph_model.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/base/graph_model.py tests/core/base/test_graph_model.py
git commit -m "feat(graph_model): subgraph slot + label/parent_node/boundary_refs (F6, F5)"
```

---

### Task 2: rigvm types — RigVMGraph 상수

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/types.py`

- [ ] **Step 1: 변경**

```python
GRAPH_CLASS_SUFFIX = "RigVMGraph"   # NEW

def is_graph_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) == GRAPH_CLASS_SUFFIX
```

- [ ] **Step 2: 단위 테스트**

`tests/plugins/rigvm/test_types.py`에 추가:

```python
from t3dgraph.plugins.rigvm.types import is_graph_class

def test_is_graph_class_true():
    assert is_graph_class("/Script/RigVMDeveloper.RigVMGraph") is True

def test_is_graph_class_false_for_node():
    assert is_graph_class("/Script/RigVMDeveloper.RigVMUnitNode") is False
```

```
pytest tests/plugins/rigvm/test_types.py -v
```
Expected: PASS.

- [ ] **Step 3: Commit**

```
git add src/t3dgraph/plugins/rigvm/types.py tests/plugins/rigvm/test_types.py
git commit -m "feat(rigvm): is_graph_class helper (F6 prep)"
```

---

### Task 3: interpreter — ContainedGraph 재귀

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Create: `tests/plugins/rigvm/test_interpreter_subgraph.py`

- [ ] **Step 1: Failing test — 단순 합성 케이스**

```python
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _unit_node(name):
    return T3DObject(
        name=name,
        cls="/Script/RigVMDeveloper.RigVMUnitNode",
        properties={},
        children=[],
    )


def test_collapse_node_subgraph_extracted():
    inner_node = _unit_node("Inner1")
    contained = T3DObject(
        name="CollapseNode_ContainedGraph",
        cls="/Script/RigVMDeveloper.RigVMGraph",
        properties={},
        children=[inner_node],
    )
    collapse = T3DObject(
        name="MyCollapse",
        cls="/Script/RigVMDeveloper.RigVMCollapseNode",
        properties={},
        children=[contained],
    )
    doc = T3DDocument(objects=[collapse])

    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1, "부모 그래프엔 collapse 노드 1개만"
    parent = g.nodes[0]
    assert parent.name == "MyCollapse"
    assert parent.subgraph is not None
    assert [n.name for n in parent.subgraph.nodes] == ["Inner1"]
    assert parent.subgraph.parent_node == "MyCollapse"
    assert parent.subgraph.label  # 비어 있지 않음


def test_preserves_parent_node_when_subgraph_extracted():
    """PRESERVE-ALL: 자식 추출이 부모를 절대 사라지게 하지 않음."""
    inner_node = _unit_node("Inner1")
    contained = T3DObject(name="X_ContainedGraph",
                          cls="/Script/RigVMDeveloper.RigVMGraph",
                          properties={}, children=[inner_node])
    collapse = T3DObject(name="P",
                         cls="/Script/RigVMDeveloper.RigVMCollapseNode",
                         properties={}, children=[contained])
    doc = T3DDocument(objects=[collapse])

    g = RigVMGraphInterpreter().interpret(doc)
    parent_names = {n.name for n in g.nodes}
    assert "P" in parent_names                   # 부모는 그대로
    assert "Inner1" not in parent_names          # 자식은 부모 그래프에 들어가지 않음
    # 자식은 subgraph에만 존재
    assert "Inner1" in {n.name for n in g.nodes[0].subgraph.nodes}


def test_subgraph_recursion_depth():
    """N단계 중첩 — 폭주 없이 추출."""
    leaf = _unit_node("Leaf")
    level3 = T3DObject(name="L3_ContainedGraph",
                       cls="/Script/RigVMDeveloper.RigVMGraph",
                       properties={}, children=[leaf])
    mid_collapse = T3DObject(name="Mid",
                             cls="/Script/RigVMDeveloper.RigVMCollapseNode",
                             properties={}, children=[level3])
    level2 = T3DObject(name="L2_ContainedGraph",
                       cls="/Script/RigVMDeveloper.RigVMGraph",
                       properties={}, children=[mid_collapse])
    outer_collapse = T3DObject(name="Outer",
                               cls="/Script/RigVMDeveloper.RigVMCollapseNode",
                               properties={}, children=[level2])
    doc = T3DDocument(objects=[outer_collapse])

    g = RigVMGraphInterpreter().interpret(doc)
    outer = g.nodes[0]
    mid = outer.subgraph.nodes[0]
    assert mid.name == "Mid"
    assert mid.subgraph.nodes[0].name == "Leaf"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/plugins/rigvm/test_interpreter_subgraph.py -v
```
Expected: FAIL (`subgraph` is None).

- [ ] **Step 3: Implement — interpreter 재귀**

`src/t3dgraph/plugins/rigvm/interpreter.py`:

리팩터: 객체 리스트 → GraphModel 변환을 별도 메서드로 추출, top-level과 ContainedGraph 양쪽이 재사용.

```python
class RigVMGraphInterpreter(AbstractGraphInterpreter):
    def interpret(self, doc: T3DDocument) -> GraphModel:
        return self._interpret_objects(doc.objects, label=None, parent_node=None)

    def _interpret_objects(
        self,
        objects: list[T3DObject],
        *,
        label: str | None,
        parent_node: str | None,
    ) -> GraphModel:
        g = GraphModel(label=label, parent_node=parent_node)
        for obj in objects:
            if t.is_link_class(obj.cls):
                self._add_link(obj, g)
            elif t.is_node_class(obj.cls):
                self._add_node(obj, g)
            elif obj.cls is None:
                continue
            elif t.is_graph_class(obj.cls):
                continue   # 자식 RigVMGraph는 _add_node가 처리
            else:
                self._add_generic(obj, g)
        # external_refs 채움 (기존 로직 그대로)
        known = {n.name for n in g.nodes}
        for link in g.links:
            for path in (link.source_path, link.target_path):
                node = node_of(path)
                if node not in known and path not in g.external_refs:
                    g.external_refs.append(path)
        return g

    def _add_node(self, obj: T3DObject, g: GraphModel) -> None:
        summary, category = role_for(obj)
        node = Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children if t.is_pin_class(c.cls) or c.cls is None],
            position=_position(obj),
            raw=dict(obj.properties),
            kind=_classify_kind(obj),
            display_name=display_name_for(obj),
            role_summary=summary,
            role_category=category,
        )
        # ContainedGraph 자식 발견 → 재귀
        for child in obj.children:
            if t.is_graph_class(child.cls):
                node.subgraph = self._interpret_objects(
                    child.children,
                    label=f"{node.display_name or node.name}/{child.name or 'graph'}",
                    parent_node=node.name,
                )
                break
        g.nodes.append(node)
        if obj.cls and obj.cls.rsplit(".", 1)[-1] == "RigVMVariableNode":
            self._add_variable_ref(node, g)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/plugins/rigvm/test_interpreter_subgraph.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: 전체 회귀**

```
pytest tests/ -v
```
Expected: PASS — 기존 RigVMModel 통합 테스트(Phase 2c smoke 등)도 OK여야 함.

- [ ] **Step 6: Commit**

```
git add src/t3dgraph/plugins/rigvm/interpreter.py tests/plugins/rigvm/test_interpreter_subgraph.py
git commit -m "feat(rigvm): recurse ContainedGraph into Node.subgraph (F6 — internal; PRESERVE-ALL)"
```

---

### Task 4: graph_stack — 스택 자료구조

**Files:**
- Create: `src/t3dgraph/core/app/graph_stack.py`
- Create: `tests/core/app/test_graph_stack.py`

- [ ] **Step 1: Failing tests**

```python
from t3dgraph.core.app.graph_stack import GraphStack
from t3dgraph.core.base.graph_model import GraphModel


def test_initial_empty():
    s = GraphStack()
    assert s.current() is None
    assert s.segments() == []


def test_push_and_current():
    g = GraphModel(label="root")
    s = GraphStack()
    s.push(g)
    assert s.current() is g
    assert s.segments() == ["root"]


def test_push_child_and_pop():
    a = GraphModel(label="A")
    b = GraphModel(label="A/B", parent_node="N")
    s = GraphStack()
    s.push(a)
    s.push(b)
    assert s.current() is b
    assert s.segments() == ["A", "A/B"]
    s.pop()
    assert s.current() is a


def test_pop_at_root_noop():
    g = GraphModel(label="A")
    s = GraphStack()
    s.push(g)
    s.pop()                       # 루트는 유지
    assert s.current() is g


def test_jump_to_index():
    s = GraphStack()
    a = GraphModel(label="A")
    b = GraphModel(label="B")
    c = GraphModel(label="C")
    s.push(a); s.push(b); s.push(c)
    s.jump_to(0)
    assert s.current() is a
    assert s.segments() == ["A"]


def test_open_new_root_adds_to_stack_list():
    """파일 여러 개 열기 — 별도 루트를 스택 리스트에 추가."""
    s = GraphStack()
    s.open_root(GraphModel(label="file1"))
    s.open_root(GraphModel(label="file2"))
    roots = s.roots()
    assert [r.label for r in roots] == ["file1", "file2"]
    assert s.current().label == "file2"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_graph_stack.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement**

`src/t3dgraph/core/app/graph_stack.py`:

```python
"""그래프 스택 — 서브그래프 드릴다운 + 멀티 파일 루트."""
from __future__ import annotations
from ..base.graph_model import GraphModel


class GraphStack:
    """루트별 진입 경로를 갖는 스택.

    - `open_root(g)`: 새 루트 그래프(새 파일) 추가. 현재 루트가 됨.
    - `push(g)`: 현재 루트의 진입 경로에 child 그래프 push.
    - `pop()`: 한 단계 back (루트면 noop).
    - `jump_to(i)`: 현재 루트의 진입 경로 i번째로 점프.
    - `roots()`: 모든 루트.
    - `current()`: 가장 깊은 현재 그래프 또는 None.
    - `segments()`: 현재 루트의 진입 경로 label 시퀀스.
    """

    def __init__(self) -> None:
        self._roots: list[GraphModel] = []
        self._paths: list[list[GraphModel]] = []
        self._cur_root: int = -1

    def open_root(self, g: GraphModel) -> None:
        self._roots.append(g)
        self._paths.append([g])
        self._cur_root = len(self._roots) - 1

    def push(self, g: GraphModel) -> None:
        if self._cur_root < 0:
            self.open_root(g)
            return
        self._paths[self._cur_root].append(g)

    def pop(self) -> None:
        if self._cur_root < 0:
            return
        path = self._paths[self._cur_root]
        if len(path) > 1:
            path.pop()

    def jump_to(self, index: int) -> None:
        if self._cur_root < 0:
            return
        path = self._paths[self._cur_root]
        if 0 <= index < len(path):
            del path[index + 1:]

    def current(self) -> GraphModel | None:
        if self._cur_root < 0:
            return None
        return self._paths[self._cur_root][-1]

    def segments(self) -> list[str]:
        if self._cur_root < 0:
            return []
        return [g.label or "?" for g in self._paths[self._cur_root]]

    # 단순 push - 이 스택은 push가 호출되어도 부모 GraphModel 인스턴스를 *변형하지 않음*.
    # 자식 인스턴스를 그대로 가리킬 뿐.

    def roots(self) -> list[GraphModel]:
        return list(self._roots)

    def select_root(self, index: int) -> None:
        if 0 <= index < len(self._roots):
            self._cur_root = index
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_graph_stack.py -v
```
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/graph_stack.py tests/core/app/test_graph_stack.py
git commit -m "feat(app): GraphStack with multi-root + drilldown (F5)"
```

---

### Task 5: BreadcrumbBar 위젯

**Files:**
- Create: `src/t3dgraph/core/app/breadcrumb_bar.py`
- Create: `tests/core/app/test_breadcrumb.py`

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.breadcrumb_bar import BreadcrumbBar


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_set_segments_renders_buttons(qapp):
    bar = BreadcrumbBar()
    bar.set_segments(["root", "Physics", "Inner"])
    assert bar.segment_labels() == ["root", "Physics", "Inner"]


def test_segment_click_emits_index(qapp):
    bar = BreadcrumbBar()
    bar.set_segments(["A", "B", "C"])
    received: list[int] = []
    bar.segment_clicked.connect(received.append)
    bar.click_segment(1)
    assert received == [1]


def test_empty_segments(qapp):
    bar = BreadcrumbBar()
    bar.set_segments([])
    assert bar.segment_labels() == []
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_breadcrumb.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement**

`src/t3dgraph/core/app/breadcrumb_bar.py`:

```python
"""브레드크럼 바 — 그래프 스택 진입 경로 표시."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel


class BreadcrumbBar(QWidget):
    segment_clicked = Signal(int)              # 클릭한 세그먼트 인덱스

    def __init__(self) -> None:
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._buttons: list[QPushButton] = []

    def set_segments(self, labels: list[str]) -> None:
        # 기존 위젯 제거
        for b in self._buttons:
            self._layout.removeWidget(b)
            b.deleteLater()
        self._buttons = []
        # 분리기 (QLabel) 제거
        while self._layout.count():
            it = self._layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()

        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.clicked.connect(lambda _checked, idx=i: self.segment_clicked.emit(idx))
            self._layout.addWidget(btn)
            self._buttons.append(btn)
            if i < len(labels) - 1:
                self._layout.addWidget(QLabel(">"))
        self._layout.addStretch(1)

    def segment_labels(self) -> list[str]:
        return [b.text() for b in self._buttons]

    def click_segment(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].click()
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_breadcrumb.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/breadcrumb_bar.py tests/core/app/test_breadcrumb.py
git commit -m "feat(app): BreadcrumbBar widget (F5)"
```

---

### Task 6: scene — 노드 더블클릭 시그널

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `src/t3dgraph/core/app/items.py` (이미 Slice A에서 mouseDoubleClick 추가됨 — 핀 vs 노드 영역 분기)

Slice A의 `NodeItem.mouseDoubleClickEvent`는 핀 행 영역에서 핀 토글. 본 Task는 **헤더 영역** 더블클릭을 서브그래프 진입으로 전용.

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_double_click_header_emits_enter_subgraph(qapp):
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    g = GraphModel(label="root", nodes=[Node(name="P", cls=None, subgraph=inner)])
    win = MainWindow()
    win.show_graph(g)

    received: list[str] = []
    win.scene.enter_subgraph_requested.connect(received.append)

    item = win.scene.node_item("P")
    item.simulate_header_double_click()
    assert received == ["P"]
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

`src/t3dgraph/core/app/items.py` `NodeItem`:

```python
HEADER_DOUBLE_CLICK_REGION = (0.0, 0.0, NODE_WIDTH, HEADER_HEIGHT)


def mouseDoubleClickEvent(self, event):
    y = event.pos().y()
    if y < HEADER_HEIGHT:
        # 헤더 — 서브그래프 진입
        self.bus.enter_subgraph_requested.emit(self.node.name)
        event.accept()
        return
    # 행 — 핀 토글 (기존 동작)
    row = int((y - HEADER_HEIGHT) / ROW_HEIGHT)
    if 0 <= row < len(self._row_paths):
        self.toggle_pin_at_row(row)
        event.accept()
        return
    super().mouseDoubleClickEvent(event)


def simulate_header_double_click(self) -> None:
    self.bus.enter_subgraph_requested.emit(self.node.name)
```

`_NodeItemBus`에 시그널 추가:

```python
class _NodeItemBus(QObject):
    pin_toggle_requested = Signal(str)
    enter_subgraph_requested = Signal(str)        # NEW
```

`GraphScene`에 라우팅:

```python
class GraphScene(QGraphicsScene):
    pin_toggle_requested = Signal(str)
    enter_subgraph_requested = Signal(str)        # NEW

    # populate 안 NodeItem 추가 부분
    item.bus.enter_subgraph_requested.connect(self.enter_subgraph_requested)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_subgraph_navigation.py::test_double_click_header_emits_enter_subgraph -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py \
        tests/core/app/test_subgraph_navigation.py
git commit -m "feat(scene): header double-click emits enter_subgraph (F5/F6)"
```

---

### Task 7: MainWindow + Controller — 스택 통합

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `src/t3dgraph/core/app/controller.py`

- [ ] **Step 1: Test — end-to-end**

`tests/core/app/test_subgraph_navigation.py`에 추가:

```python
def test_enter_and_exit_subgraph(qapp):
    inner = GraphModel(label="P/inner", parent_node="P",
                       nodes=[Node(name="I", cls=None)])
    g = GraphModel(label="root",
                   nodes=[Node(name="P", cls=None, subgraph=inner)])

    win = MainWindow()
    win.open_graph(g, label="root")    # 새 API — controller가 호출하는 형태와 동일
    assert win.scene.node_item("P") is not None

    # 헤더 더블클릭 → 진입
    win.scene.node_item("P").simulate_header_double_click()
    # inner 그래프 노드가 보여야
    assert win.scene.node_item("I") is not None
    # P 노드는 inner 그래프에 없으므로 캔버스에서 사라짐 — 단, 부모 그래프 모델엔 그대로
    assert win.scene.node_item("P") is None

    # 브레드크럼 segments
    assert win.breadcrumb.segment_labels() == ["root", "P/inner"]

    # 첫 세그먼트 클릭 → 루트 복귀
    win.breadcrumb.click_segment(0)
    assert win.scene.node_item("P") is not None
    assert win.scene.node_item("I") is None


def test_multi_file_multi_root(qapp):
    g1 = GraphModel(label="file1.t3d", nodes=[Node(name="A", cls=None)])
    g2 = GraphModel(label="file2.t3d", nodes=[Node(name="B", cls=None)])
    win = MainWindow()
    win.open_graph(g1, label="file1.t3d")
    win.open_graph(g2, label="file2.t3d")
    assert win.scene.node_item("B") is not None
    # roots는 두 개
    assert len(win.graph_stack.roots()) == 2


def test_preserve_all_nodes_after_drilldown(qapp):
    """PRESERVE-ALL: 자식 진입 후에도 부모 그래프 모델은 변경되지 않음."""
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    parent_g = GraphModel(label="root",
                          nodes=[Node(name="P", cls=None, subgraph=inner)])
    parent_node_count_before = len(parent_g.nodes)
    win = MainWindow()
    win.open_graph(parent_g, label="root")
    win.scene.node_item("P").simulate_header_double_click()
    win.breadcrumb.click_segment(0)         # 루트 복귀
    assert len(parent_g.nodes) == parent_node_count_before
    assert parent_g.nodes[0].subgraph is inner   # 자식 참조 유지
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_subgraph_navigation.py -v
```
Expected: FAIL (`open_graph` missing, breadcrumb missing).

- [ ] **Step 3: Implement — MainWindow**

`src/t3dgraph/core/app/main_window.py`:

```python
# import
from .graph_stack import GraphStack
from .breadcrumb_bar import BreadcrumbBar

# __init__
self.graph_stack = GraphStack()
self.breadcrumb = BreadcrumbBar()

# central — 브레드크럼을 상단에 둘 컨테이너
from PySide6.QtWidgets import QWidget, QVBoxLayout
central = QWidget()
vlay = QVBoxLayout(central)
vlay.setContentsMargins(0, 0, 0, 0)
vlay.addWidget(self.breadcrumb)
vlay.addWidget(self.view)
self.setCentralWidget(central)

# _wire 추가
self.scene.enter_subgraph_requested.connect(self._on_enter_subgraph)
self.breadcrumb.segment_clicked.connect(self._on_breadcrumb_clicked)


def open_graph(self, graph: GraphModel, *, label: str | None = None) -> None:
    """새 루트 그래프 추가(파일 열기 진입점)."""
    if label and not graph.label:
        graph.label = label
    self.graph_stack.open_root(graph)
    self._render_current()


def _on_enter_subgraph(self, node_name: str) -> None:
    current = self.graph_stack.current()
    if current is None:
        return
    node = current.node_by_name(node_name)
    if node is None or node.subgraph is None:
        return
    self.graph_stack.push(node.subgraph)
    self._render_current()


def _on_breadcrumb_clicked(self, index: int) -> None:
    self.graph_stack.jump_to(index)
    self._render_current()


def _render_current(self) -> None:
    current = self.graph_stack.current()
    if current is None:
        return
    self.graph = current
    self.scene.populate(current, view_state=self.view_state, flow=None)
    self.node_filter.set_graph(current)
    self.inspector.show_node(None, current)
    self.view.fit()
    self.breadcrumb.set_segments(self.graph_stack.segments())
    self.statusBar().showMessage(
        f"노드 {len(current.nodes)} · 링크 {len(current.links)}", 5000)
    # 분석은 현재 그래프 기준으로 (Slice D 흐름 살아 있음)
    from ..analysis.flow import analyze_flow
    from ..analysis.execution_order import compute_execution_order
    flow = analyze_flow(current)
    order = compute_execution_order(current, flow)
    self.show_analysis(flow, order)
    # data flow도 (Slice D 적용된 경우)
    try:
        from ..analysis.data_flow import analyze_data_flow
        self.show_data_flow(analyze_data_flow(current))
    except Exception:
        pass


# 기존 show_graph 호환: open_graph로 위임
def show_graph(self, graph: GraphModel) -> None:
    self.open_graph(graph)
```

- [ ] **Step 4: Implement — controller**

`src/t3dgraph/core/app/controller.py`:

```python
def open_file(self, path: str) -> None:
    p = Path(path)
    if not p.is_file():
        self._fail(f"파일을 찾을 수 없습니다: {path}")
        return
    try:
        doc = parse_document(read_t3d_text(p))
    except (UnicodeDecodeError, T3DParseError) as e:
        self._fail(f"파싱 실패: {e}")
        return
    try:
        plugin = default_registry().detect(doc)
    except LookupError as e:
        self._fail(str(e))
        return
    graph = plugin.interpreter_factory().interpret(doc)
    open_graph = getattr(self.view, "open_graph", None)
    if callable(open_graph):
        open_graph(graph, label=p.name)
    else:
        self.view.show_graph(graph)
    # 분석 호출은 _render_current가 담당하므로 제거
```

- [ ] **Step 5: Run — pass**

```
pytest tests/core/app/test_subgraph_navigation.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 6: 전체 회귀**

```
pytest tests/ -v
```
Expected: PASS — 기존 통합 테스트가 show_graph만 호출하면 `open_graph`로 위임되어 동일 동작.

- [ ] **Step 7: Commit**

```
git add src/t3dgraph/core/app/main_window.py src/t3dgraph/core/app/controller.py \
        tests/core/app/test_subgraph_navigation.py
git commit -m "feat(main_window): graph stack + breadcrumb integration (F5/F6)"
```

---

### Task 8: 서브그래프 보유 표시 (UX 보조, 옵셔널)

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`

서브그래프 보유 노드는 시각적으로 구분(작은 chevron 또는 다른 헤더 색). 필수는 아니지만 사용자가 어디서 진입 가능한지 알 수 있어야 한다.

- [ ] **Step 1: 변경 — 헤더에 표시**

`NodeItem.__init__`에:

```python
if node.subgraph is not None:
    # 헤더 우측 ▶ 표시 (서브그래프 진입 가능)
    chev = QGraphicsSimpleTextItem("▶", self)
    chev.setBrush(QBrush(QColor(200, 200, 120)))
    chev.setPos(NODE_WIDTH - 16, 5)
```

- [ ] **Step 2: smoke 확인 — 인스턴스 만들고 chevron child가 있는지**

```python
def test_subgraph_node_shows_chevron(qapp):
    node = Node(name="P", cls=None,
                subgraph=GraphModel(label="x"))
    item = NodeItem(node)
    chevrons = [c for c in item.childItems()
                if c.__class__.__name__ == "QGraphicsSimpleTextItem"
                and c.text() == "▶"]
    assert len(chevrons) == 1
```

- [ ] **Step 3: Run — PASS**

- [ ] **Step 4: Commit**

```
git add src/t3dgraph/core/app/items.py tests/core/app/test_subgraph_node_chevron.py
git commit -m "feat(items): chevron on subgraph-bearing nodes (F5 UX)"
```

---

### Task 9: Orion 샘플 검증 + 회귀

**Files:**
- Run: `pytest tests/ -v`

- [ ] **Step 1: smoke — Physics CollapseNode subgraph 추출 확인**

`tests/smoke_subgraph_orion.py`(신규):

```python
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from pathlib import Path

p = Path("Orion_WorkStation_Rig_Analysis/"
         "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
g = default_registry().detect(parse_document(read_t3d_text(p))).interpreter_factory().interpret(parse_document(read_t3d_text(p)))

subgraph_holders = [n for n in g.nodes if n.subgraph is not None]
print(f"전체 {len(g.nodes)} 중 {len(subgraph_holders)} 노드가 서브그래프 보유")
for h in subgraph_holders:
    print(f"  - {h.name}: 내부 노드 {len(h.subgraph.nodes)} · 링크 {len(h.subgraph.links)}")
assert subgraph_holders, "최소 1개 CollapseNode가 서브그래프를 가져야 함"
```

실행: `python tests/smoke_subgraph_orion.py`

기대: Physics 등이 서브그래프 보유, 내부 노드/링크 양수.

- [ ] **Step 2: 전체 회귀**

```
pytest tests/ -v
```
Expected: PASS.

- [ ] **Step 3: Commit (smoke)**

```
git add tests/smoke_subgraph_orion.py
git commit -m "test: smoke for subgraph extraction on Orion RigVMModel"
```

---

## 완료 정의

- [ ] 모든 Task 1-9 체크박스 PASS
- [ ] Orion `Physics` CollapseNode의 ContainedGraph가 자식 GraphModel로 추출 — 부모 그래프 nodes 리스트는 변경 없음
- [ ] 헤더 더블클릭 시 서브그래프로 진입, 브레드크럼 세그먼트 증가
- [ ] 브레드크럼 세그먼트 클릭 시 해당 깊이로 점프
- [ ] 파일 메뉴 "열기"가 새 루트로 push (이전 그래프 유지)
- [ ] PRESERVE-ALL — 진입·복귀 후에도 GraphModel 인스턴스/노드 리스트 그대로
- [ ] 서브그래프 보유 노드에 ▶ chevron 표시
