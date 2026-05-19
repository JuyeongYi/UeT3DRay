# t3dgraph Phase 2d — 뷰 모드 (연결된 핀만 · 깊이 펼침 · fan-in 강조) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 2a~2c 뷰어에 3가지 뷰 모드를 추가해 spec §7의 뷰어를 완성한다 — 연결된 핀만 표시, 깊이(서브핀) 펼침, fan-in 수렴점 강조. 뷰 모드 툴바로 토글.

**Architecture:** spec §7.3. `NodeItem`을 렌더 옵션을 받도록 개편하고, `GraphScene.populate`를 `ViewState`+`FlowResult`를 받는 단일 렌더 경로로 통합한다. 뷰 모드 토글 시 씬을 재구성(선택 보존). Model·분석 레이어 불변.

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt.

**선행 조건:** Phase 2c 완료(master, 141 테스트 통과). 리포: `C:/Users/jylee/source/UeT3DRay`.

**Spec:** `docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md`

**범위 밖 (백로그):** improver findings(`docs/superpowers/backlog.md` P1.5/P2a/P2b 12건) + 기능 아이디어 4건. Phase 2d 완료 후 정리 batch로 처리 — 착수 시 당시 코드 기준 재검토.

---

## File Structure (Phase 2d)

| 파일 | 변경 | 책임 |
| --- | --- | --- |
| `src/t3dgraph/core/app/view_state.py` | 수정 | 뷰 모드 3개 플래그 추가 |
| `src/t3dgraph/core/app/items.py` | 수정 | `NodeItem` 렌더 옵션(연결 필터·서브핀·강조) |
| `src/t3dgraph/core/app/scene.py` | 수정 | `populate`를 ViewState+Flow 단일 렌더 경로로 |
| `src/t3dgraph/core/app/main_window.py` | 수정 | 뷰 모드 툴바, 토글 시 씬 재구성 |
| `tests/core/app/...` | 수정/생성 | 각 모듈 테스트 + 통합 스모크 |

---

## Task 1: ViewState — 뷰 모드 플래그

`ViewState`에 3개 뷰 모드 플래그와 setter를 추가한다.

**Files:**
- Modify: `src/t3dgraph/core/app/view_state.py`
- Modify: `tests/core/app/test_view_state.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_view_state.py` 에 추가:

```python
def test_view_mode_defaults_false():
    vs = ViewState()
    assert vs.connected_pins_only is False
    assert vs.expand_subpins is False
    assert vs.fan_in_highlight is False


def test_set_connected_only_notifies():
    vs = ViewState()
    seen = []
    vs.subscribe(lambda: seen.append(vs.connected_pins_only))
    vs.set_connected_pins_only(True)
    assert vs.connected_pins_only is True
    assert seen == [True]


def test_set_expand_subpins_and_fan_in():
    vs = ViewState()
    vs.set_expand_subpins(True)
    vs.set_fan_in_highlight(True)
    assert vs.expand_subpins is True
    assert vs.fan_in_highlight is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_view_state.py -q`
Expected: FAIL — `AttributeError: 'ViewState' object has no attribute 'connected_pins_only'`

- [ ] **Step 3: 구현**

`core/app/view_state.py` — `ViewState` 데이터클래스에 필드 추가(`hidden_node_types` 다음, `_listeners` 앞)와 setter 메서드 추가:

```python
@dataclass
class ViewState:
    selected_node: str | None = None
    hidden_node_types: set[str] = field(default_factory=set)
    connected_pins_only: bool = False
    expand_subpins: bool = False
    fan_in_highlight: bool = False
    _listeners: list[Callable[[], None]] = field(default_factory=list)
```

기존 메서드들 다음에 추가:

```python
    def set_connected_pins_only(self, value: bool) -> None:
        self.connected_pins_only = value
        self._notify()

    def set_expand_subpins(self, value: bool) -> None:
        self.expand_subpins = value
        self._notify()

    def set_fan_in_highlight(self, value: bool) -> None:
        self.fan_in_highlight = value
        self._notify()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_view_state.py -q`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/view_state.py tests/core/app/test_view_state.py
git commit -m "feat(app): ViewState view-mode flags"
```

---

## Task 2: NodeItem — 렌더 옵션 (연결 필터 · 서브핀 · 강조)

`NodeItem`을 렌더 옵션을 받도록 개편한다. 옵션 미지정 시 기존(Phase 2c) 동작과 동일 — 최상위 핀 전체, 필터·강조 없음. `_rows`를 **전체 핀 경로**로 키잉한다(백로그 P2b-A1 동명 서브핀 충돌 회피).

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `tests/core/app/test_items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_items.py` 에 추가 (기존 테스트는 옵션 미지정 → 그대로 통과해야 함):

```python
def test_subpins_rendered_when_expanded(qtbot):
    sub = Pin(name="X", cpp_type="double", direction="Input")
    parent = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[sub])
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[parent])
    flat = NodeItem(node, show_subpins=True)
    deep = NodeItem(node, show_subpins=False)
    # 펼침: 헤더 + T + X = 2행 / 미펼침: 헤더 + T = 1행
    assert flat.rect().height() == HEADER_HEIGHT + 2 * ROW_HEIGHT
    assert deep.rect().height() == HEADER_HEIGHT + 1 * ROW_HEIGHT


def test_connected_only_filters_unconnected_pins(qtbot):
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[
        Pin(name="A", cpp_type="exec", direction="Output"),
        Pin(name="B", cpp_type="double", direction="Input"),
    ])
    item = NodeItem(node, connected_paths=frozenset({"N.A"}), connected_only=True)
    # A만 연결됨 → 1행
    assert item.rect().height() == HEADER_HEIGHT + 1 * ROW_HEIGHT
    assert item.has_pin_row("N.A") is True
    assert item.has_pin_row("N.B") is False


def test_highlighted_node_has_distinct_pen(qtbot):
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[])
    plain = NodeItem(node)
    hot = NodeItem(node, highlighted=True)
    assert hot.pen().color() != plain.pen().color()


def test_pin_anchor_uses_full_path_keying(qtbot):
    node = Node(name="N", cls="X", position=(100.0, 50.0), pins=[
        Pin(name="In", cpp_type="exec", direction="Input"),
    ])
    item = NodeItem(node)
    anchor = item.pin_anchor("In", "Input")
    assert anchor.x() == 100.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_items.py -q`
Expected: FAIL — `NodeItem()`에 `show_subpins` 등 인자 없음 → `TypeError`

- [ ] **Step 3: 구현**

`core/app/items.py` — `NodeItem` 클래스를 다음으로 교체 (`LinkItem`·상수는 유지):

```python
class NodeItem(QGraphicsRectItem):
    """노드 1개 — 헤더 + 핀 행. 렌더 옵션으로 필터·서브핀·강조 제어."""

    def __init__(
        self, node: Node, *,
        connected_paths: frozenset[str] = frozenset(),
        connected_only: bool = False,
        show_subpins: bool = False,
        highlighted: bool = False,
    ):
        self.node = node
        rows = self._collect_rows(node, connected_paths, connected_only, show_subpins)
        height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
        super().__init__(QRectF(0, 0, NODE_WIDTH, height))
        x, y = node.position if node.position else (0.0, 0.0)
        self.setPos(x, y)
        if highlighted:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))      # fan-in 강조
        else:
            self.setPen(QPen(QColor(40, 40, 40)))
        self.setBrush(QBrush(QColor(70, 70, 80) if not node.is_generic
                              else QColor(90, 60, 60)))
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

        title = QGraphicsSimpleTextItem(node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)

        self._rows: dict[str, float] = {}                      # 전체 경로 → 행 중심 y
        for i, (pin, path, depth) in enumerate(rows):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[path] = cy
            is_input = (pin.direction or "").lower() != "output"
            mx = 0.0 if is_input else NODE_WIDTH
            dot = QGraphicsEllipseItem(
                mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
            dot.setBrush(QBrush(QColor(200, 200, 120)))
            dot.setPen(QPen(Qt.NoPen))
            label = QGraphicsSimpleTextItem(pin.name, self)
            label.setBrush(QBrush(QColor(210, 210, 210)))
            indent = 8 + depth * 12
            lx = indent if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
            label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)

    @staticmethod
    def _collect_rows(node, connected_paths, connected_only, show_subpins):
        """렌더할 (pin, full_path, depth) 목록."""
        rows: list[tuple[Pin, str, int]] = []

        def walk(pin: Pin, path: str, depth: int) -> None:
            if (not connected_only) or (path in connected_paths):
                rows.append((pin, path, depth))
            if show_subpins:
                for sp in pin.subpins:
                    walk(sp, f"{path}.{sp.name}", depth + 1)

        for pin in node.pins:
            walk(pin, f"{node.name}.{pin.name}", 0)
        return rows

    def has_pin_row(self, full_path: str) -> bool:
        return full_path in self._rows

    def pin_anchor(self, pin_name: str, direction: str) -> QPointF:
        """핀의 씬 좌표 앵커. 핀 이름은 최상위 핀(`Node.Pin`)으로 해석.
        알 수 없거나 숨겨진 핀은 노드 중앙으로 폴백."""
        cy = self._rows.get(f"{self.node.name}.{pin_name}")
        if cy is None:
            return self.mapToScene(QPointF(NODE_WIDTH / 2, self.rect().height() / 2))
        lx = NODE_WIDTH if (direction or "").lower() == "output" else 0.0
        return self.mapToScene(QPointF(lx, cy))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_items.py -q`
Expected: PASS (기존 Phase 2a 테스트 + 신규 4개) — 기존 테스트는 옵션 미지정 기본 동작이 Phase 2c와 동일하므로 통과

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/items.py tests/core/app/test_items.py
git commit -m "feat(app): NodeItem render options — pin filter, subpins, highlight"
```

---

## Task 3: GraphScene — ViewState 기반 단일 렌더 경로

`GraphScene.populate`가 `ViewState`와 `FlowResult`를 받아 뷰 모드를 반영해 노드를 그린다. 노드별 연결 핀 경로는 링크에서, fan-in 강조 대상은 `flow.convergence_points`에서 도출. 재구성 시 선택을 보존한다.

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `tests/core/app/test_scene.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_scene.py` 에 추가:

```python
def test_populate_with_connected_only(qtbot):
    from t3dgraph.core.app.view_state import ViewState
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT
    g = _graph()                                       # A.O → B.I
    vs = ViewState()
    vs.connected_pins_only = True
    scene = GraphScene()
    scene.populate(g, view_state=vs)
    # A의 핀 O는 연결됨 → 1행
    assert scene.node_item("A").rect().height() == HEADER_HEIGHT + 1 * ROW_HEIGHT


def test_populate_preserves_selection(qtbot):
    from t3dgraph.core.app.view_state import ViewState
    scene = GraphScene()
    scene.populate(_graph())
    scene.select_node("B")
    scene.populate(_graph(), view_state=ViewState())   # 재구성
    assert scene.selected_node_name() == "B"


def test_fan_in_highlight_marks_convergence(qtbot):
    from t3dgraph.core.app.view_state import ViewState
    from t3dgraph.core.analysis.flow import analyze_flow
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
    def ep(n, d): return Pin(name=n, cpp_type="x", direction=d, is_execution=True)
    a = Node(name="A", cls="X", position=(0.0, 0.0), pins=[ep("O", "Output")])
    b = Node(name="B", cls="X", position=(0.0, 100.0), pins=[ep("O", "Output")])
    c = Node(name="C", cls="X", position=(200.0, 50.0), pins=[ep("I", "Input")])
    g = GraphModel(nodes=[a, b, c], links=[Link("A.O", "C.I"), Link("B.O", "C.I")])
    vs = ViewState()
    vs.fan_in_highlight = True
    scene = GraphScene()
    scene.populate(g, view_state=vs, flow=analyze_flow(g))
    plain = scene.node_item("A").pen().color()
    hot = scene.node_item("C").pen().color()           # C는 수렴점
    assert hot != plain
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_scene.py -q`
Expected: FAIL — `populate()`에 `view_state` 인자 없음 → `TypeError`

- [ ] **Step 3: 구현**

`core/app/scene.py` — 전체를 다음으로 교체:

```python
"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from ..analysis.flow import FlowResult
from .items import NodeItem, LinkItem
from .view_state import ViewState


def _seg(pin_path: str, index: int) -> str:
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


def _type_suffix(cls: str | None) -> str:
    return (cls or "?").rsplit(".", 1)[-1]


class GraphScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._nodes: dict[str, NodeItem] = {}
        self._links: list[tuple[LinkItem, str, str]] = []

    def node_item(self, name: str) -> NodeItem | None:
        return self._nodes.get(name)

    def populate(self, graph: GraphModel, *,
                 view_state: ViewState | None = None,
                 flow: FlowResult | None = None) -> None:
        vs = view_state or ViewState()
        keep_selected = self.selected_node_name()
        self.clear()
        self._nodes = {}
        self._links = []

        connected = self._connected_paths_by_node(graph)
        convergence = set(flow.convergence_points) if flow is not None else set()

        for node in graph.nodes:
            item = NodeItem(
                node,
                connected_paths=frozenset(connected.get(node.name, set())),
                connected_only=vs.connected_pins_only,
                show_subpins=vs.expand_subpins,
                highlighted=vs.fan_in_highlight and node.name in convergence,
            )
            self.addItem(item)
            self._nodes[node.name] = item
        for link in graph.links:
            self._add_link(link)

        self.apply_hidden_types(vs.hidden_node_types)
        if keep_selected in self._nodes:
            self.select_node(keep_selected)

    @staticmethod
    def _connected_paths_by_node(graph: GraphModel) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for link in graph.links:
            for path in (link.source_path, link.target_path):
                out.setdefault(_seg(path, 0), set()).add(path)
        return out

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
        self.clearSelection()
        item = self._nodes.get(name)
        if item is not None:
            item.setSelected(True)

    def selected_node_name(self) -> str | None:
        for name, item in self._nodes.items():
            try:
                if item.isSelected():
                    return name
            except RuntimeError:
                pass
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
git commit -m "feat(app): GraphScene single render path driven by ViewState"
```

---

## Task 4: 뷰 모드 툴바 — MainWindow 통합

`MainWindow`에 뷰 모드 토글 툴바(체크 가능 액션 3개)를 추가하고, 토글 시 `ViewState` 갱신 + 씬 재구성. `show_graph`는 새 `populate` 시그니처를 쓴다.

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/core/app/test_main_window.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_main_window.py` 에 추가:

```python
def test_view_mode_toolbar_has_three_toggles(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    labels = {a.text() for a in w.view_mode_actions}
    assert labels == {"연결된 핀만", "깊이 펼침", "fan-in 강조"}
    assert all(a.isCheckable() for a in w.view_mode_actions)


def test_toggle_connected_only_rebuilds_scene(qtbot):
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())                       # A.Out→B.In, 각 노드 핀 1개(연결됨)
    w.set_view_mode("연결된 핀만", True)
    assert w.view_state.connected_pins_only is True
    # 핀이 연결돼 있으므로 높이 변화 없음 — 재구성만 검증
    assert w.scene.node_item("A") is not None


def test_toggle_expand_subpins_updates_state(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.set_view_mode("깊이 펼침", True)
    assert w.view_state.expand_subpins is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: FAIL — `MainWindow`에 `view_mode_actions` 없음

- [ ] **Step 3: 구현**

`core/app/main_window.py` — `__init__`의 `self._build_menu()` 호출 다음 줄에 `self._build_view_mode_toolbar()` 추가하고, 새 메서드와 핸들러를 추가. `show_graph`는 `populate` 호출을 새 시그니처로 교체.

`__init__` 의 `self._build_menu()` 다음에:

```python
        self._build_view_mode_toolbar()
```

`_build_menu` 메서드 다음에 추가:

```python
    def _build_view_mode_toolbar(self) -> None:
        from PySide6.QtGui import QAction
        toolbar = self.addToolBar("뷰 모드")
        self.view_mode_actions: list[QAction] = []
        for label, setter in (
            ("연결된 핀만", self.view_state.set_connected_pins_only),
            ("깊이 펼침", self.view_state.set_expand_subpins),
            ("fan-in 강조", self.view_state.set_fan_in_highlight),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.toggled.connect(
                lambda checked, s=setter: self._on_view_mode(s, checked))
            toolbar.addAction(action)
            self.view_mode_actions.append(action)

    def _on_view_mode(self, setter, checked: bool) -> None:
        setter(checked)
        self._rebuild_scene()

    def _rebuild_scene(self) -> None:
        if self.graph is not None:
            self.scene.populate(self.graph, view_state=self.view_state,
                                flow=self._flow)

    def set_view_mode(self, label: str, checked: bool) -> None:
        """테스트·프로그램용 — 라벨로 뷰 모드 액션을 토글."""
        for action in self.view_mode_actions:
            if action.text() == label:
                action.setChecked(checked)
                return
```

`show_graph` 메서드를 다음으로 교체 (분석 결과를 `self._flow`에 보관, 새 `populate` 시그니처 사용):

```python
    def show_graph(self, graph: GraphModel) -> None:
        self.graph = graph
        self._flow = analyze_flow(graph)
        self.scene.populate(graph, view_state=self.view_state, flow=self._flow)
        self.node_filter.set_graph(graph)
        self.inspector.show_node(None, graph)
        self.analysis_panel.show_flow(self._flow)
        self.exec_order_panel.show_order(
            compute_execution_order(graph, self._flow))
        self.view.fit()
        self.statusBar().showMessage(
            f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}", 5000)
```

`__init__`에서 `self.graph` 초기화 줄(`self.graph: GraphModel | None = None`) 다음에 `self._flow` 초기화 추가:

```python
        self._flow = None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window.py
git commit -m "feat(app): view-mode toolbar with scene rebuild"
```

---

## Task 5: 통합 스모크 테스트

실제 Orion 파일로 뷰 모드 토글 전 경로 검증.

**Files:**
- Test: `tests/core/app/test_phase2d_smoke.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/core/app/test_phase2d_smoke.py
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


def test_connected_only_toggle_on_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    window.set_view_mode("연결된 핀만", True)
    assert window.view_state.connected_pins_only is True
    assert len(window.scene._nodes) > 0                # 재구성 후 노드 유지


def test_expand_subpins_toggle_on_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    before = window.scene.node_item(window.graph.nodes[0].name).rect().height()
    window.set_view_mode("깊이 펼침", True)
    after = window.scene.node_item(window.graph.nodes[0].name).rect().height()
    # 서브핀이 있는 RigVM 노드는 펼침 시 높이가 같거나 커진다
    assert after >= before


def test_fan_in_highlight_toggle_no_error(qtbot, orion_dir):
    # 샘플은 수렴점 0건 — 강조 토글이 예외 없이 동작하는지만 검증
    window = _open(qtbot, orion_dir)
    window.set_view_mode("fan-in 강조", True)
    assert window.view_state.fan_in_highlight is True


def test_selection_survives_view_mode_toggle(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    first = window.graph.nodes[0].name
    window.scene.select_node(first)
    window.set_view_mode("깊이 펼침", True)
    assert window.scene.selected_node_name() == first
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/core/app/test_phase2d_smoke.py -q`
Expected: PASS — 미처리 케이스가 드러나면 해당 모듈 수정 + 회귀 테스트 추가 후 재실행

- [ ] **Step 3: 전체 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS (Phase 1~2c 기존 141개 + Phase 2d 신규)

- [ ] **Step 4: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 툴바의 "연결된 핀만"·"깊이 펼침"·"fan-in 강조" 토글 시 캔버스가 즉시 재구성, 선택 노드 유지

- [ ] **Step 5: Commit**

```bash
git add tests/core/app/test_phase2d_smoke.py
git commit -m "test(app): Phase 2d view-mode smoke over real Orion file"
```

---

## Self-Review

**1. Spec coverage (Phase 2d 범위)**
- spec §7.3 연결된 핀만 표시 → Task 2(NodeItem 필터)·3(scene)·4(툴바) ✓
- spec §7.3 깊이 펼침(서브핀) → Task 2·3·4 ✓
- spec §7.3 fan-in 강조 → Task 2(highlighted pen)·3(convergence 도출)·4 ✓
- spec §7.1 뷰 모드 툴바 → Task 4 ✓
- spec §7 뷰어 — Phase 2d 완료 시 §7 전체(레이아웃·패널·인스펙터·분석 도크·뷰 모드) 완성
- 부수: 백로그 P2b-A1(동명 서브핀 키 충돌)을 Task 2에서 `_rows` 전체 경로 키잉으로 **부분 해소** — NodeItem 한정. `InspectorPanel`의 동일 문제는 백로그에 남음(정리 batch).
- **범위 밖**: improver findings 백로그 12건 + 기능 아이디어 4건 — Phase 2d 완료 후 정리 batch.

**2. Placeholder scan** — "TBD/TODO" 없음. 모든 코드 단계에 실제 코드.

**3. Type consistency**
- `ViewState.connected_pins_only`/`expand_subpins`/`fan_in_highlight` + setter — Task 1 정의, Task 3·4 사용 일치
- `NodeItem(node, *, connected_paths, connected_only, show_subpins, highlighted)`/`has_pin_row`/`pin_anchor` — Task 2 정의, Task 3 사용 일치. 옵션 기본값이 Phase 2c 동작을 재현하므로 기존 호출(`NodeItem(node)`)·테스트 호환
- `GraphScene.populate(graph, *, view_state, flow)` — Task 3 정의, Task 4 `show_graph`·`_rebuild_scene` 호출 일치. 기존 `populate(graph)`도 옵션 기본값으로 동작 — Phase 2b/2c 테스트 호환
- `MainWindow.view_mode_actions`/`set_view_mode`/`_flow`/`_rebuild_scene` — Task 4 정의, Task 5 사용 일치
- `pin_anchor`가 최상위 핀 이름을 `f"{node}.{name}"`로 해석 — `scene._add_link`가 `_seg(path,1)`(최상위 핀 세그먼트)을 넘기므로 정합. 링크는 연결된 핀만 가리키고 연결된 핀은 `connected_only`에서도 유지되므로 앵커 조회 성공

---

## 다음 단계 — 뷰어 완성 후

Phase 2d 완료 → **spec §7 뷰어 전체 완성** (산출물 #2 PySide6 앱).

이후 **백로그 정리 batch** — planner가 별도 계획 작성:
- `docs/superpowers/backlog.md`의 improver findings 12건(P1.5/P2a/P2b) + 기능 아이디어 4건
- 착수 시 backlog.md "처리 규칙"대로 각 항목을 **당시 코드 기준으로 재검토** — Phase 진행으로 stale해졌거나 형태가 달라졌을 수 있음 (예: P2b-A1 NodeItem 부분은 Phase 2d에서 이미 해소)
