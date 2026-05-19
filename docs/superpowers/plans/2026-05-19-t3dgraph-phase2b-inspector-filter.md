# t3dgraph Phase 2b — 속성 인스펙터 & 노드 타입 필터 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 2a 뷰어에 노드 선택·속성 인스펙터(핀 기본값·연결됨 네비게이션·변경됨 휴리스틱)·노드 타입 필터를 추가해 그래프를 검사·필터할 수 있게 한다.

**Architecture:** spec §7.2·§7.4. Phase 2a의 `core/app/`(MainWindow·GraphScene·NodeItem) 위에 `ViewState`(표현 상태)와 패널 위젯을 얹는다. Model 레이어 불변. ViewState는 순수 Python(Qt 없음, 테스트 용이).

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt.

**선행 조건:** Phase 2a 완료(master, 92 테스트 통과). 리포: `C:/Users/jylee/source/UeT3DRay`.

**Spec:** `docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md`

**범위 밖 (Phase 2c):** 분석 도크(수렴점 목록·실행 순서 코드 뷰), 뷰 모드(연결된 핀만 표시·깊이 펼침·fan-in 강조). Phase 2b는 하단 분석 도크를 placeholder로 유지한다.

**참고 — Phase 2a 결정사항:** `QMainWindow`+ABC 다중상속은 metaclass 충돌 → `AbstractGraphView.register(MainWindow)` 사용. Phase 2b의 패널은 순수 `QWidget` 서브클래스(ABC 미혼합)라 이 문제 없음.

---

## File Structure (Phase 2b)

| 파일 | 변경 | 책임 |
| --- | --- | --- |
| `src/t3dgraph/core/app/view_state.py` | 생성 | `ViewState` — 선택 노드·숨긴 타입, 옵저버 |
| `src/t3dgraph/core/app/pin_status.py` | 생성 | 변경됨 휴리스틱 (타입 zero-value 비교) |
| `src/t3dgraph/core/app/inspector_panel.py` | 생성 | `InspectorPanel` — 선택 노드 핀 표시 |
| `src/t3dgraph/core/app/node_filter_panel.py` | 생성 | `NodeFilterPanel` — 노드 타입 체크박스 |
| `src/t3dgraph/core/app/scene.py` | 수정 | 선택 시그널·타입 가시성·노드 포커스 |
| `src/t3dgraph/core/app/main_window.py` | 수정 | placeholder 도크 → 실제 패널, 와이어링 |
| `tests/core/app/...` | 생성 | 각 모듈 테스트 + 통합 스모크 |

---

## Task 1: `ViewState` — 표현 상태

선택된 노드와 숨긴 노드 타입을 들고, 변경 시 옵저버에게 알린다. 순수 Python — Qt 없음, qtbot 없이 테스트.

**Files:**
- Create: `src/t3dgraph/core/app/view_state.py`
- Test: `tests/core/app/test_view_state.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_view_state.py
from t3dgraph.core.app.view_state import ViewState


def test_defaults():
    vs = ViewState()
    assert vs.selected_node is None
    assert vs.hidden_node_types == set()


def test_select_notifies():
    vs = ViewState()
    seen = []
    vs.subscribe(lambda: seen.append(vs.selected_node))
    vs.select("NodeA")
    assert vs.selected_node == "NodeA"
    assert seen == ["NodeA"]


def test_set_type_hidden_toggles_and_notifies():
    vs = ViewState()
    calls = []
    vs.subscribe(lambda: calls.append(set(vs.hidden_node_types)))
    vs.set_type_hidden("RigVMUnitNode", True)
    vs.set_type_hidden("RigVMUnitNode", False)
    assert calls == [{"RigVMUnitNode"}, set()]


def test_is_type_hidden():
    vs = ViewState()
    vs.set_type_hidden("X", True)
    assert vs.is_type_hidden("X") is True
    assert vs.is_type_hidden("Y") is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_view_state.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/view_state.py
"""뷰어 표현 상태 — 선택·필터. 순수 Python(Qt 없음)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ViewState:
    selected_node: str | None = None
    hidden_node_types: set[str] = field(default_factory=set)
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for cb in self._listeners:
            cb()

    def select(self, node: str | None) -> None:
        self.selected_node = node
        self._notify()

    def set_type_hidden(self, type_name: str, hidden: bool) -> None:
        if hidden:
            self.hidden_node_types.add(type_name)
        else:
            self.hidden_node_types.discard(type_name)
        self._notify()

    def is_type_hidden(self, type_name: str) -> bool:
        return type_name in self.hidden_node_types
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_view_state.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/view_state.py tests/core/app/test_view_state.py
git commit -m "feat(app): ViewState — selection and node-type visibility"
```

---

## Task 2: 변경됨 휴리스틱 — `core/app/pin_status.py`

핀의 `default_value`가 해당 `cpp_type`의 zero-value와 다르면 "변경됨(추정)". 데이터에 오버라이드 플래그가 없어 휴리스틱(spec §7.4). 단일 함수 = 교체 가능한 전략.

**Files:**
- Create: `src/t3dgraph/core/app/pin_status.py`
- Test: `tests/core/app/test_pin_status.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_pin_status.py
from t3dgraph.core.base.graph_model import Pin
from t3dgraph.core.app.pin_status import is_changed_from_default


def _pin(cpp, dv):
    return Pin(name="P", cpp_type=cpp, direction="Input", default_value=dv)


def test_none_default_not_changed():
    assert is_changed_from_default(_pin("double", None)) is False


def test_bool_false_not_changed():
    assert is_changed_from_default(_pin("bool", "False")) is False
    assert is_changed_from_default(_pin("bool", "false")) is False   # 표기 비일관 허용


def test_bool_true_changed():
    assert is_changed_from_default(_pin("bool", "True")) is True


def test_numeric_zero_not_changed():
    assert is_changed_from_default(_pin("double", "0.000000")) is False
    assert is_changed_from_default(_pin("int32", "0")) is False


def test_numeric_nonzero_changed():
    assert is_changed_from_default(_pin("double", "1.000000")) is True


def test_fname_none_not_changed():
    assert is_changed_from_default(_pin("FName", "None")) is False


def test_fname_value_changed():
    assert is_changed_from_default(_pin("FName", "IKTarget")) is True


def test_empty_struct_not_changed():
    assert is_changed_from_default(_pin("FVector", "()")) is False


def test_struct_with_value_changed():
    assert is_changed_from_default(_pin("FQuat", "(X=0.0,W=1.0)")) is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_pin_status.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/pin_status.py
"""핀 '변경됨' 휴리스틱 — 타입 zero-value 비교 (spec §7.4, 교체 가능 전략)."""
from __future__ import annotations
from ..base.graph_model import Pin

_NUMERIC = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float", "double",
}


def is_changed_from_default(pin: Pin) -> bool:
    """기본값이 타입의 zero-value와 다르면 '변경됨(추정)'.

    데이터에 오버라이드 플래그가 없으므로 휴리스틱이다 — 정당한 기본값도
    변경으로 오탐될 수 있어 UI는 '변경됨(추정)'으로 라벨한다.
    """
    dv = pin.default_value
    if dv is None:
        return False
    v = dv.strip()
    cpp = pin.cpp_type or ""
    if cpp == "bool":
        return v.lower() not in ("false", "")
    if cpp in _NUMERIC:
        try:
            return float(v) != 0.0
        except ValueError:
            return v not in ("", "0")
    if cpp == "FName":
        return v.lower() not in ("none", "")
    # 구조체·문자열·기타: 빈 값/빈 구조체가 아니면 변경된 것으로 본다
    return v not in ("", "()", '""')
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_pin_status.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/pin_status.py tests/core/app/test_pin_status.py
git commit -m "feat(app): pin 'changed-from-default' heuristic"
```

---

## Task 3: 속성 인스펙터 패널 — `core/app/inspector_panel.py`

`InspectorPanel(QWidget)` — 선택 노드의 핀(서브핀 포함)을 `QTreeWidget`에 표시. 컬럼: 핀 / 타입 / 방향 / 기본값 / 상태(연결됨·변경됨). 연결된 핀은 양끝 peer 노드를 보유하고 더블클릭 시 `navigate_requested(peer_node)` 시그널을 낸다.

**Files:**
- Create: `src/t3dgraph/core/app/inspector_panel.py`
- Test: `tests/core/app/test_inspector_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_inspector_panel.py
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.inspector_panel import InspectorPanel


def _graph():
    a = Node(name="A", cls="X", pins=[
        Pin(name="Out", cpp_type="exec", direction="Output"),
        Pin(name="Scale", cpp_type="double", direction="Input", default_value="1.000000"),
    ])
    b = Node(name="B", cls="X", pins=[Pin(name="In", cpp_type="exec", direction="Input")])
    return GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")])


def test_show_node_lists_pins(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    assert panel.pin_count() == 2


def test_connected_pin_marked(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    assert panel.is_pin_connected("Out") is True       # A.Out → B.In
    assert panel.is_pin_connected("Scale") is False


def test_changed_pin_marked(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    assert panel.is_pin_changed("Scale") is True        # 1.0 ≠ 0.0
    assert panel.is_pin_changed("Out") is False


def test_navigate_signal_on_connected_pin(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_pin("Out")                       # 연결된 핀 활성화
    assert sig.args == ["B"]                            # peer 노드


def test_clear_when_none(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(None, _graph())
    assert panel.pin_count() == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_inspector_panel.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/inspector_panel.py
"""속성 인스펙터 — 선택 노드의 핀·기본값·연결됨·변경됨."""
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from ..base.graph_model import GraphModel, Node, Pin
from .pin_status import is_changed_from_default

_PEER_ROLE = Qt.UserRole + 1            # 트리 아이템에 저장할 peer 노드명


def _connected_pin_paths(graph: GraphModel) -> set[str]:
    paths: set[str] = set()
    for link in graph.links:
        paths.add(link.source_path)
        paths.add(link.target_path)
    return paths


def _peer_of(path: str, graph: GraphModel) -> str | None:
    """주어진 핀 경로의 링크 반대편 노드명."""
    for link in graph.links:
        if link.source_path == path:
            return link.target_path.split(".", 1)[0]
        if link.target_path == path:
            return link.source_path.split(".", 1)[0]
    return None


class InspectorPanel(QWidget):
    navigate_requested = Signal(str)        # peer 노드명

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._title = QLabel("(노드를 선택하세요)")
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["핀", "타입", "방향", "기본값", "상태"])
        layout.addWidget(self._title)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        self._items: dict[str, QTreeWidgetItem] = {}     # pin_name → 아이템

    def show_node(self, node: Node | None, graph: GraphModel) -> None:
        self._tree.clear()
        self._items = {}
        if node is None:
            self._title.setText("(노드를 선택하세요)")
            return
        self._title.setText(f"{node.name}  [{node.cls or '?'}]")
        connected = _connected_pin_paths(graph)
        for pin in node.pins:
            self._add_pin(pin, node.name, pin.name, connected, graph, self._tree.invisibleRootItem())

    def _add_pin(self, pin: Pin, node_name: str, path: str,
                 connected: set[str], graph: GraphModel, parent: QTreeWidgetItem) -> None:
        full = f"{node_name}.{path}"
        is_conn = full in connected
        is_chg = is_changed_from_default(pin)
        status = " · ".join(
            s for s in ("연결됨" if is_conn else "", "변경됨(추정)" if is_chg else "") if s)
        item = QTreeWidgetItem(
            [pin.name, pin.cpp_type or "", pin.direction or "",
             pin.default_value or "", status])
        if is_conn:
            peer = _peer_of(full, graph)
            if peer:
                item.setData(0, _PEER_ROLE, peer)
        parent.addChild(item)
        self._items[pin.name] = item
        for sub in pin.subpins:
            self._add_pin(sub, node_name, f"{path}.{sub.name}", connected, graph, item)

    def _on_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        peer = item.data(0, _PEER_ROLE)
        if peer:
            self.navigate_requested.emit(peer)

    # --- 테스트·외부 조회용 ---
    def pin_count(self) -> int:
        return len(self._items)

    def is_pin_connected(self, pin_name: str) -> bool:
        item = self._items.get(pin_name)
        return item is not None and "연결됨" in item.text(4)

    def is_pin_changed(self, pin_name: str) -> bool:
        item = self._items.get(pin_name)
        return item is not None and "변경됨" in item.text(4)

    def activate_pin(self, pin_name: str) -> None:
        item = self._items.get(pin_name)
        if item is not None:
            self._on_activated(item, 0)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_inspector_panel.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/inspector_panel.py tests/core/app/test_inspector_panel.py
git commit -m "feat(app): InspectorPanel with connected/changed pin status"
```

---

## Task 4: 노드 타입 필터 패널 — `core/app/node_filter_panel.py`

`NodeFilterPanel(QWidget)` — 그래프의 노드 타입(클래스 suffix)별 체크박스. 체크 해제 시 `type_toggled(type_name, hidden)` 시그널.

**Files:**
- Create: `src/t3dgraph/core/app/node_filter_panel.py`
- Test: `tests/core/app/test_node_filter_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_node_filter_panel.py
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.node_filter_panel import NodeFilterPanel


def _graph():
    return GraphModel(nodes=[
        Node(name="A", cls="/Script/RigVMDeveloper.RigVMUnitNode"),
        Node(name="B", cls="/Script/RigVMDeveloper.RigVMUnitNode"),
        Node(name="C", cls="/Script/RigVMDeveloper.RigVMDispatchNode"),
    ])


def test_one_checkbox_per_distinct_type(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    assert set(panel.type_names()) == {"RigVMUnitNode", "RigVMDispatchNode"}


def test_all_checked_initially(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    assert all(panel.is_checked(t) for t in panel.type_names())


def test_uncheck_emits_toggled(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    with qtbot.waitSignal(panel.type_toggled, timeout=1000) as sig:
        panel.set_checked("RigVMUnitNode", False)
    assert sig.args == ["RigVMUnitNode", True]          # (type, hidden=True)


def test_set_graph_rebuilds(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    panel.set_graph(GraphModel(nodes=[Node(name="Z", cls="/X.RigVMRerouteNode")]))
    assert panel.type_names() == ["RigVMRerouteNode"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_node_filter_panel.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/node_filter_panel.py
"""노드 타입 필터 — 타입별 체크박스."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from ..base.graph_model import GraphModel


def _type_suffix(cls: str | None) -> str:
    return (cls or "?").rsplit(".", 1)[-1]


class NodeFilterPanel(QWidget):
    type_toggled = Signal(str, bool)        # (type_name, hidden)

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.addStretch(1)
        self._boxes: dict[str, QCheckBox] = {}

    def set_graph(self, graph: GraphModel) -> None:
        for box in self._boxes.values():
            box.setParent(None)
        self._boxes = {}
        for type_name in sorted({_type_suffix(n.cls) for n in graph.nodes}):
            box = QCheckBox(type_name)
            box.setChecked(True)
            box.toggled.connect(
                lambda checked, t=type_name: self.type_toggled.emit(t, not checked))
            self._layout.insertWidget(self._layout.count() - 1, box)
            self._boxes[type_name] = box

    def type_names(self) -> list[str]:
        return list(self._boxes.keys())

    def is_checked(self, type_name: str) -> bool:
        box = self._boxes.get(type_name)
        return box is not None and box.isChecked()

    def set_checked(self, type_name: str, checked: bool) -> None:
        box = self._boxes.get(type_name)
        if box is not None:
            box.setChecked(checked)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_node_filter_panel.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/node_filter_panel.py tests/core/app/test_node_filter_panel.py
git commit -m "feat(app): NodeFilterPanel — per-type checkboxes"
```

---

## Task 5: GraphScene — 선택·타입 가시성·포커스

`GraphScene`에 ① 선택된 노드명 조회, ② 노드 타입 가시성 적용(노드 + 그 노드에 닿는 링크 숨김), ③ 프로그램적 노드 선택을 추가한다.

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Test: `tests/core/app/test_scene.py` (기존 파일에 추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_scene.py` 에 추가:

```python
def test_selected_node_name(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    scene.select_node("B")
    assert scene.selected_node_name() == "B"


def test_apply_hidden_types_hides_nodes(qtbot):
    g = GraphModel(
        nodes=[Node(name="A", cls="/X.RigVMUnitNode", position=(0.0, 0.0)),
               Node(name="C", cls="/X.RigVMDispatchNode", position=(300.0, 0.0))],
        links=[],
    )
    scene = GraphScene()
    scene.populate(g)
    scene.apply_hidden_types({"RigVMUnitNode"})
    assert scene.node_item("A").isVisible() is False
    assert scene.node_item("C").isVisible() is True


def test_hidden_node_also_hides_its_links(qtbot):
    scene = GraphScene()
    scene.populate(_graph())                            # A.O → B.I
    scene.apply_hidden_types({_graph().nodes[0].cls.rsplit(".", 1)[-1]})
    link_items = [i for i in scene.items() if isinstance(i, LinkItem)]
    assert all(not li.isVisible() for li in link_items)
```

(`_graph()` 헬퍼는 Phase 2a Task 4에서 정의됨 — `Link("A.O", "B.I")` 포함. 두 노드 cls는 동일하므로 위 테스트가 성립.)

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_scene.py -q`
Expected: FAIL — `AttributeError: 'GraphScene' object has no attribute 'select_node'`

- [ ] **Step 3: 구현**

`core/app/scene.py` — 전체를 다음으로 교체:

```python
"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from .items import NodeItem, LinkItem


def _seg(pin_path: str, index: int) -> str:
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


def _type_suffix(cls: str | None) -> str:
    return (cls or "?").rsplit(".", 1)[-1]


class GraphScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._nodes: dict[str, NodeItem] = {}
        self._links: list[tuple[LinkItem, str, str]] = []   # (item, src_node, tgt_node)

    def node_item(self, name: str) -> NodeItem | None:
        return self._nodes.get(name)

    def populate(self, graph: GraphModel) -> None:
        self.clear()
        self._nodes = {}
        self._links = []
        for node in graph.nodes:
            item = NodeItem(node)
            self.addItem(item)
            self._nodes[node.name] = item
        for link in graph.links:
            self._add_link(link)

    def _add_link(self, link: Link) -> None:
        s_node, t_node = _seg(link.source_path, 0), _seg(link.target_path, 0)
        src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
        if src is None or dst is None:
            return
        p1 = src.pin_anchor(_seg(link.source_path, 1), "Output")
        p2 = dst.pin_anchor(_seg(link.target_path, 1), "Input")
        item = LinkItem(p1, p2)
        self.addItem(item)
        self._links.append((item, s_node, t_node))

    def select_node(self, name: str) -> None:
        """프로그램적 단일 선택."""
        self.clearSelection()
        item = self._nodes.get(name)
        if item is not None:
            item.setSelected(True)

    def selected_node_name(self) -> str | None:
        for name, item in self._nodes.items():
            if item.isSelected():
                return name
        return None

    def apply_hidden_types(self, hidden_types: set[str]) -> None:
        for item in self._nodes.values():
            item.setVisible(_type_suffix(item.node.cls) not in hidden_types)
        for link_item, s_node, t_node in self._links:
            src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
            visible = (src is not None and src.isVisible()
                       and dst is not None and dst.isVisible())
            link_item.setVisible(visible)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_scene.py -q`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/scene.py tests/core/app/test_scene.py
git commit -m "feat(app): GraphScene selection, type visibility, focus"
```

---

## Task 6: MainWindow 통합 + 연결됨 네비게이션

placeholder 좌·우 도크를 실제 패널로 교체하고 ViewState로 묶는다. 캔버스 선택 → 인스펙터 갱신, 필터 체크 → 노드 숨김, 인스펙터 연결됨 핀 활성화 → 캔버스가 peer 노드로 이동·선택.

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Test: `tests/core/app/test_main_window.py` (기존 파일에 추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_main_window.py` 에 추가:

```python
def _wired_graph():
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
    a = Node(name="A", cls="/X.RigVMUnitNode", position=(0.0, 0.0),
             pins=[Pin("Out", "exec", "Output")])
    b = Node(name="B", cls="/X.RigVMDispatchNode", position=(400.0, 0.0),
             pins=[Pin("In", "exec", "Input")])
    return GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")])


def test_docks_hold_real_panels(qtbot):
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    from t3dgraph.core.app.node_filter_panel import NodeFilterPanel
    w = MainWindow()
    qtbot.addWidget(w)
    assert isinstance(w.dock_right.widget(), InspectorPanel)
    assert isinstance(w.dock_left.widget(), NodeFilterPanel)


def test_selecting_node_updates_inspector(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.scene.select_node("A")
    assert w.inspector.pin_count() == 1                 # A의 핀 1개


def test_filter_hides_node_in_scene(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.node_filter.set_checked("RigVMUnitNode", False)
    assert w.scene.node_item("A").isVisible() is False


def test_navigate_request_selects_peer(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.scene.select_node("A")                            # 인스펙터에 A 표시
    w.inspector.activate_pin("Out")                     # A.Out → B.In, peer=B
    assert w.scene.selected_node_name() == "B"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: FAIL — `dock_right.widget()`가 `InspectorPanel`이 아님(아직 QLabel placeholder)

- [ ] **Step 3: 구현**

`core/app/main_window.py` — 전체를 다음으로 교체:

```python
"""메인 윈도우 — 메뉴·도크·중앙 그래프 캔버스."""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QDockWidget, QLabel, QFileDialog
from ..base.graph_model import GraphModel
from .contracts import AbstractGraphView
from .scene import GraphScene
from .graph_view import GraphView
from .view_state import ViewState
from .inspector_panel import InspectorPanel
from .node_filter_panel import NodeFilterPanel


class MainWindow(QMainWindow):
    """'분석 중심' 레이아웃. 하단 도크는 Phase 2c까지 placeholder."""

    def __init__(self) -> None:
        QMainWindow.__init__(self)
        self.setWindowTitle("t3dgraph viewer")
        self.resize(1200, 800)

        self.view_state = ViewState()
        self.graph: GraphModel | None = None

        self.scene = GraphScene()
        self.view = GraphView()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        # 좌: 노드 타입 필터 / 우: 속성 인스펙터 / 하: placeholder(Phase 2c)
        self.node_filter = NodeFilterPanel()
        self.inspector = InspectorPanel()
        self.dock_left = self._dock("노드 타입 필터", self.node_filter)
        self.dock_right = self._dock("속성 인스펙터", self.inspector)
        bottom_label = QLabel("(분석 — Phase 2c)")
        bottom_label.setAlignment(Qt.AlignCenter)
        self.dock_bottom = self._dock("분석", bottom_label)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_bottom)

        self._open_handler: Callable[[str], None] | None = None
        self._build_menu()
        self._wire()

    def _dock(self, title: str, widget) -> QDockWidget:
        dock = QDockWidget(title)
        dock.setWidget(widget)
        return dock

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("파일")
        file_menu.addAction("열기…").triggered.connect(self._on_open)
        file_menu.addAction("종료").triggered.connect(self.close)

    def _wire(self) -> None:
        self.scene.selectionChanged.connect(self._on_scene_selection)
        self.node_filter.type_toggled.connect(self._on_type_toggled)
        self.inspector.navigate_requested.connect(self._navigate_to)

    # --- 메뉴/파일 ---
    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "T3D 파일 열기", "", "T3D files (*.t3d *.txt);;All files (*)")
        if path:
            self.open_path(path)

    def set_open_handler(self, handler: Callable[[str], None]) -> None:
        self._open_handler = handler

    def open_path(self, path: str) -> None:
        if self._open_handler is not None:
            self._open_handler(path)

    # --- 와이어링 핸들러 ---
    def _on_scene_selection(self) -> None:
        name = self.scene.selected_node_name()
        self.view_state.select(name)
        if self.graph is not None:
            node = self.graph.node_by_name(name) if name else None
            self.inspector.show_node(node, self.graph)

    def _on_type_toggled(self, type_name: str, hidden: bool) -> None:
        self.view_state.set_type_hidden(type_name, hidden)
        self.scene.apply_hidden_types(self.view_state.hidden_node_types)

    def _navigate_to(self, node_name: str) -> None:
        self.scene.select_node(node_name)
        item = self.scene.node_item(node_name)
        if item is not None:
            self.view.centerOn(item)

    # --- AbstractGraphView ---
    def show_graph(self, graph: GraphModel) -> None:
        self.graph = graph
        self.scene.populate(graph)
        self.node_filter.set_graph(graph)
        self.inspector.show_node(None, graph)
        self.view.fit()
        self.statusBar().showMessage(
            f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}", 5000)

    def show_error(self, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "t3dgraph", message)


# QMainWindow의 Shiboken metaclass가 ABCMeta와 충돌하므로 직접 상속 대신 등록.
AbstractGraphView.register(MainWindow)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: PASS (기존 + 신규 4개)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window.py
git commit -m "feat(app): wire inspector, filter, navigation into MainWindow"
```

---

## Task 7: 통합 스모크 테스트

실제 Orion 파일로 선택→인스펙터, 필터→숨김, 연결됨 네비게이션 전 경로 검증.

**Files:**
- Test: `tests/core/app/test_phase2b_smoke.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/core/app/test_phase2b_smoke.py
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController

RIGVMMODEL = "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"


def _open(qtbot, orion_dir):
    window = MainWindow()
    qtbot.addWidget(window)
    controller = AppController(window)
    window.set_open_handler(controller.open_file)
    window.open_path(str(orion_dir / RIGVMMODEL))
    return window


def test_filter_panel_populated_from_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    assert len(window.node_filter.type_names()) > 0


def test_select_real_node_shows_pins(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    first = window.graph.nodes[0].name
    window.scene.select_node(first)
    assert window.inspector.pin_count() >= 0           # 핀 0개 노드도 있을 수 있음
    assert window.view_state.selected_node == first


def test_hiding_a_type_hides_those_nodes(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    a_type = window.node_filter.type_names()[0]
    window.node_filter.set_checked(a_type, False)
    hidden = [it for it in window.scene._nodes.values()
              if not it.isVisible()]
    assert len(hidden) > 0


def test_full_suite_unaffected(qtbot, orion_dir):
    # 뷰어가 열린 뒤에도 모델 데이터는 무손실 — 노드/링크 존재
    window = _open(qtbot, orion_dir)
    assert len(window.graph.nodes) > 0
    assert len(window.graph.links) > 0
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/core/app/test_phase2b_smoke.py -q`
Expected: PASS — 미처리 케이스가 드러나면 해당 모듈 수정 + 회귀 테스트 추가 후 재실행

- [ ] **Step 3: 전체 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS (Phase 1/1.5/2a 기존 92개 + Phase 2b 신규)

- [ ] **Step 4: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 좌측에 타입 필터, 노드 클릭 시 우측 인스펙터에 핀 표시, 연결된 핀 더블클릭 시 캔버스가 연결 노드로 이동

- [ ] **Step 5: Commit**

```bash
git add tests/core/app/test_phase2b_smoke.py
git commit -m "test(app): Phase 2b integration smoke over real Orion file"
```

---

## Self-Review

**1. Spec coverage (Phase 2b 범위)**
- spec §7.2 노드 타입 필터(좌측 도크) → Task 4·6 ✓
- spec §7.2 속성 인스펙터(우측 도크) → Task 3·6 ✓
- spec §7.4 연결됨 — 연결 핀 표시 + peer 노드로 네비게이션 → Task 3·6 ✓
- spec §7.4 변경됨 — 타입 zero-value 휴리스틱, "변경됨(추정)" 라벨, 단일 함수=교체 가능 전략 → Task 2·3 ✓
- spec §7.3 노드 타입 가시성 뷰 모드 → Task 1·5·6 ✓ (ViewState.hidden_node_types)
- **범위 밖(Phase 2c, 의도적)**: 분석 도크(수렴점·실행 순서), 뷰 모드(연결된 핀만·깊이·fan-in 강조) — Task 6에서 하단 도크는 placeholder 유지
- **백로그 유지**: improver A1(파싱 pos), improver B1(인코딩 헬퍼 통합), `--lenient`, round-trip, 에셋 resolver, CLI `--json`

**2. Placeholder scan** — "TBD/TODO" 없음. 하단 도크의 `(분석 — Phase 2c)` 라벨은 실제 위젯 표시 텍스트.

**3. Type consistency**
- `ViewState.select`/`set_type_hidden`/`hidden_node_types`/`is_type_hidden` — Task 1 정의, Task 6 사용 일치
- `is_changed_from_default(pin)` — Task 2 정의, Task 3 `InspectorPanel`에서 사용 일치
- `InspectorPanel.show_node(node, graph)`/`navigate_requested`/`activate_pin`/`pin_count`/`is_pin_connected`/`is_pin_changed` — Task 3 정의, Task 6·7 사용 일치
- `NodeFilterPanel.set_graph`/`type_toggled`/`type_names`/`set_checked` — Task 4 정의, Task 6·7 사용 일치
- `GraphScene.select_node`/`selected_node_name`/`apply_hidden_types`/`node_item`/`_nodes` — Task 5 정의, Task 6·7 사용 일치
- `MainWindow.scene`/`view`/`graph`/`inspector`/`node_filter`/`view_state` 속성 — Task 6 정의, Task 7 사용 일치
- 핀 경로 형식 `"Node.Pin"`/`"Node.Pin.Sub"` — Task 3 `_add_pin`의 path 누적과 `_connected_pin_paths`(링크 경로 원형 비교)가 일관. 단, 링크의 `source_path`가 서브핀을 가리키면 인스펙터의 서브핀 행 path와 매칭됨 — 일관.

---

## 다음 단계 — Phase 2c

Phase 2b 완료 후 planner가 별도 계획 작성:
- 분석 도크(하단) — 수렴점 목록 탭(`analyze_flow`) + 실행 순서 코드 뷰 탭(`compute_execution_order`), 행 클릭 시 캔버스 양방향 연동
- 뷰 모드 — 연결된 핀만 표시, 깊이 펼침, fan-in 강조 (NodeItem 렌더링 변경 + ViewState 확장)
- 필요 시 `plugins/rigvm/view.py` (NodeColor 등 RigVM 고유 렌더) + `plugin.view_ref` 설정
- 백로그 batch — improver A1/B1, `--lenient`, round-trip, 에셋 resolver, CLI `--json`
