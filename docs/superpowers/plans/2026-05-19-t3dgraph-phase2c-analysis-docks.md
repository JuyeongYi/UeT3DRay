# t3dgraph Phase 2c — 분석 도크 (수렴점 · 실행 순서) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 2b 뷰어의 하단 placeholder 도크를 실제 분석 도크로 교체한다 — fan-in 수렴점 목록 탭과 실행 순서 코드 뷰 탭, 캔버스와 양방향 연동.

**Architecture:** spec §7.2(분석 도크)·§7.4(양방향 연동). Phase 1/1.5의 분석 API(`analyze_flow`·`compute_execution_order`)를 그대로 소비하는 패널 위젯을 `core/app/`에 추가하고, `MainWindow`가 그래프 로드 시 분석을 1회 수행해 패널에 공급한다. Model·분석 레이어 불변.

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt.

**선행 조건:** Phase 2b 완료(master, 125 테스트 통과). 리포: `C:/Users/jylee/source/UeT3DRay`.

**Spec:** `docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md`

**범위 밖 (Phase 2d):** 뷰 모드 — 연결된 핀만 표시, 깊이 펼침, fan-in 강조. 분석 패널은 데이터를 보여줄 뿐 캔버스 렌더링은 바꾸지 않는다.

**참고:** 제공된 Orion 샘플 11개는 실행 흐름이 전부 선형 — fan-in 수렴점 0건. 수렴점 패널은 "수렴점 없음" 상태를 정상 처리해야 하며, 합성 픽스처로 수렴점 표시를 테스트한다.

---

## File Structure (Phase 2c)

| 파일 | 변경 | 책임 |
| --- | --- | --- |
| `src/t3dgraph/core/app/analysis_panel.py` | 생성 | `AnalysisPanel` — fan-in 수렴점 목록 |
| `src/t3dgraph/core/app/execution_order_panel.py` | 생성 | `ExecutionOrderPanel` — 실행 순서 코드 뷰 |
| `src/t3dgraph/core/app/main_window.py` | 수정 | placeholder 하단 도크 → 탭 분석 도크, 분석 수행·양방향 연동 |
| `tests/core/app/...` | 생성 | 각 패널 테스트 + 통합 스모크 |

---

## Task 1: 수렴점 패널 — `core/app/analysis_panel.py`

`AnalysisPanel(QWidget)` — `FlowResult`를 받아 fan-in 수렴점을 `QTreeWidget`에 표시. 수렴점마다 유입 노드·공통 다운스트림을 하위 행으로. 수렴점 행 활성화 시 `navigate_requested(node)`. 수렴점 0건이면 안내 문구.

**Files:**
- Create: `src/t3dgraph/core/app/analysis_panel.py`
- Test: `tests/core/app/test_analysis_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_analysis_panel.py
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.flow import analyze_flow
from t3dgraph.core.app.analysis_panel import AnalysisPanel


def _ep(name, d):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=d, is_execution=True)


def _fan_in_graph():
    a = Node(name="A", cls="X", pins=[_ep("O", "Output")])
    b = Node(name="B", cls="X", pins=[_ep("O", "Output")])
    c = Node(name="C", cls="X", pins=[_ep("I", "Input"), _ep("O", "Output")])
    d = Node(name="D", cls="X", pins=[_ep("I", "Input")])
    links = [Link("A.O", "C.I"), Link("B.O", "C.I"), Link("C.O", "D.I")]
    return GraphModel(nodes=[a, b, c, d], links=links)


def test_no_convergence_shows_message(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    a = Node(name="A", cls="X", pins=[_ep("O", "Output")])
    b = Node(name="B", cls="X", pins=[_ep("I", "Input")])
    panel.show_flow(analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")])))
    assert panel.convergence_count() == 0
    assert "없음" in panel.summary_text()


def test_convergence_listed(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show_flow(analyze_flow(_fan_in_graph()))
    assert panel.convergence_count() == 1
    assert panel.has_convergence("C")


def test_activate_convergence_emits_navigate(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show_flow(analyze_flow(_fan_in_graph()))
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_convergence("C")
    assert sig.args == ["C"]


def test_highlight_node_selects_row(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show_flow(analyze_flow(_fan_in_graph()))
    panel.highlight_node("C")
    assert panel.highlighted_node() == "C"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_analysis_panel.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/analysis_panel.py
"""분석 도크 — fan-in 수렴점 목록."""
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from ..analysis.flow import FlowResult

_NODE_ROLE = Qt.UserRole + 1


class AnalysisPanel(QWidget):
    navigate_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._summary = QLabel("(그래프를 열어주세요)")
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["수렴점 / 상세"])
        layout.addWidget(self._summary)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        self._rows: dict[str, QTreeWidgetItem] = {}

    def show_flow(self, flow: FlowResult) -> None:
        self._tree.clear()
        self._rows = {}
        cps = flow.convergence_points
        if not cps:
            self._summary.setText("실행 수렴점(fan-in) 없음 — 선형 실행 흐름")
            return
        self._summary.setText(f"실행 수렴점 {len(cps)}개")
        for node in cps:
            conv = flow.convergence(node)
            top = QTreeWidgetItem([node])
            top.setData(0, _NODE_ROLE, node)
            top.addChild(QTreeWidgetItem([f"유입 경로: {', '.join(conv.incoming_nodes)}"]))
            down = ", ".join(conv.common_downstream) or "(없음)"
            top.addChild(QTreeWidgetItem([f"공통 다운스트림: {down}"]))
            self._tree.addTopLevelItem(top)
            self._rows[node] = top

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        node = item.data(0, _NODE_ROLE)
        if node:
            self.navigate_requested.emit(node)

    # --- 조회·연동 ---
    def summary_text(self) -> str:
        return self._summary.text()

    def convergence_count(self) -> int:
        return len(self._rows)

    def has_convergence(self, node: str) -> bool:
        return node in self._rows

    def activate_convergence(self, node: str) -> None:
        item = self._rows.get(node)
        if item is not None:
            self._on_activated(item, 0)

    def highlight_node(self, node: str | None) -> None:
        item = self._rows.get(node) if node else None
        if item is not None:
            self._tree.setCurrentItem(item)
        else:
            self._tree.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._tree.currentItem()
        return item.data(0, _NODE_ROLE) if item is not None else None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_analysis_panel.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/analysis_panel.py tests/core/app/test_analysis_panel.py
git commit -m "feat(app): AnalysisPanel — fan-in convergence list"
```

---

## Task 2: 실행 순서 패널 — `core/app/execution_order_panel.py`

`ExecutionOrderPanel(QWidget)` — `list[ExecutionStep]`을 받아 깊이 들여쓰기로 코드처럼 표시(`QListWidget`). 행 활성화 시 `navigate_requested(node)`.

**Files:**
- Create: `src/t3dgraph/core/app/execution_order_panel.py`
- Test: `tests/core/app/test_execution_order_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_execution_order_panel.py
from t3dgraph.core.analysis.execution_order import ExecutionStep
from t3dgraph.core.app.execution_order_panel import ExecutionOrderPanel


def _steps():
    return [ExecutionStep("A", 0), ExecutionStep("B", 1), ExecutionStep("C", 1)]


def test_show_order_lists_steps(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    assert panel.step_count() == 3


def test_depth_rendered_as_indent(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    assert panel.row_text(0) == "A"
    assert panel.row_text(1).startswith("    ") and panel.row_text(1).strip() == "B"


def test_activate_row_emits_navigate(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_row(2)
    assert sig.args == ["C"]


def test_highlight_node_selects_row(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    panel.highlight_node("B")
    assert panel.highlighted_node() == "B"


def test_empty_order(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order([])
    assert panel.step_count() == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_execution_order_panel.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/execution_order_panel.py
"""분석 도크 — 실행 순서 코드 뷰."""
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from ..analysis.execution_order import ExecutionStep

_NODE_ROLE = Qt.UserRole + 1
_INDENT = "    "


class ExecutionOrderPanel(QWidget):
    navigate_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setFont(QFont("Consolas"))
        layout.addWidget(self._list)
        self._list.itemActivated.connect(self._on_activated)
        self._rows: dict[str, QListWidgetItem] = {}

    def show_order(self, steps: list[ExecutionStep]) -> None:
        self._list.clear()
        self._rows = {}
        for step in steps:
            item = QListWidgetItem(_INDENT * step.depth + step.node)
            item.setData(_NODE_ROLE, step.node)
            self._list.addItem(item)
            self._rows[step.node] = item

    def _on_activated(self, item: QListWidgetItem) -> None:
        node = item.data(_NODE_ROLE)
        if node:
            self.navigate_requested.emit(node)

    # --- 조회·연동 ---
    def step_count(self) -> int:
        return self._list.count()

    def row_text(self, row: int) -> str:
        return self._list.item(row).text()

    def activate_row(self, row: int) -> None:
        self._on_activated(self._list.item(row))

    def highlight_node(self, node: str | None) -> None:
        item = self._rows.get(node) if node else None
        if item is not None:
            self._list.setCurrentItem(item)
        else:
            self._list.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._list.currentItem()
        return item.data(_NODE_ROLE) if item is not None else None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_execution_order_panel.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/execution_order_panel.py tests/core/app/test_execution_order_panel.py
git commit -m "feat(app): ExecutionOrderPanel — code-like execution order view"
```

---

## Task 3: MainWindow 통합 — 탭 분석 도크 + 양방향 연동

하단 placeholder 도크를 `QTabWidget`(수렴점 / 실행 순서)으로 교체. `show_graph`에서 `analyze_flow`·`compute_execution_order`를 1회 수행해 두 패널에 공급. 패널 `navigate_requested` → 캔버스 이동. 캔버스 노드 선택 → 두 패널에서 해당 행 강조(양방향).

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py` (전체 교체)
- Test: `tests/core/app/test_main_window.py` (기존 파일에 추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_main_window.py` 에 추가:

```python
def test_bottom_dock_has_analysis_tabs(qtbot):
    from PySide6.QtWidgets import QTabWidget
    w = MainWindow()
    qtbot.addWidget(w)
    tabs = w.dock_bottom.widget()
    assert isinstance(tabs, QTabWidget)
    titles = {tabs.tabText(i) for i in range(tabs.count())}
    assert titles == {"수렴점", "실행 순서"}


def test_show_graph_populates_execution_order(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())                    # Phase 2b 테스트 헬퍼: A.Out→B.In
    assert w.exec_order_panel.step_count() == 2     # A, B


def test_analysis_panel_navigate_moves_canvas(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.exec_order_panel.activate_row(1)              # B 행
    assert w.scene.selected_node_name() == "B"


def test_canvas_selection_highlights_exec_panel(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.scene.select_node("A")
    assert w.exec_order_panel.highlighted_node() == "A"
```

(`_wired_graph()`는 Phase 2b Task 6에서 정의된 헬퍼 — `A.Out → B.In` 실행 링크 포함. 실행 핀이므로 `compute_execution_order`가 A·B 2스텝을 낸다. `Pin`의 `is_execution`은 Phase 2b 헬퍼가 `exec` cpp_type만 줄 경우 False일 수 있으니, 본 테스트용으로 헬퍼를 보강한다 — 아래 Step 3 참조.)

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: FAIL — `dock_bottom.widget()`가 `QTabWidget`이 아님(QLabel placeholder)

- [ ] **Step 3: 구현**

먼저 `tests/core/app/test_main_window.py`의 `_wired_graph()` 헬퍼에서 실행 핀이 `is_execution=True`가 되도록 보강한다 (기존 헬퍼의 `Pin(...)` 호출에 `is_execution=True` 추가):

```python
def _wired_graph():
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
    a = Node(name="A", cls="/X.RigVMUnitNode", position=(0.0, 0.0),
             pins=[Pin("Out", "FRigVMExecuteContext", "Output", is_execution=True)])
    b = Node(name="B", cls="/X.RigVMDispatchNode", position=(400.0, 0.0),
             pins=[Pin("In", "FRigVMExecuteContext", "Input", is_execution=True)])
    return GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")])
```

`core/app/main_window.py` — 전체를 다음으로 교체:

```python
"""메인 윈도우 — 메뉴·도크·중앙 그래프 캔버스."""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QDockWidget, QFileDialog, QTabWidget
from ..base.graph_model import GraphModel
from ..analysis.flow import analyze_flow
from ..analysis.execution_order import compute_execution_order
from .contracts import AbstractGraphView
from .scene import GraphScene
from .graph_view import GraphView
from .view_state import ViewState
from .inspector_panel import InspectorPanel
from .node_filter_panel import NodeFilterPanel
from .analysis_panel import AnalysisPanel
from .execution_order_panel import ExecutionOrderPanel


class MainWindow(QMainWindow):
    """'분석 중심' 레이아웃."""

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

        self.node_filter = NodeFilterPanel()
        self.inspector = InspectorPanel()
        self.analysis_panel = AnalysisPanel()
        self.exec_order_panel = ExecutionOrderPanel()

        bottom_tabs = QTabWidget()
        bottom_tabs.addTab(self.analysis_panel, "수렴점")
        bottom_tabs.addTab(self.exec_order_panel, "실행 순서")

        self.dock_left = self._dock("노드 타입 필터", self.node_filter)
        self.dock_right = self._dock("속성 인스펙터", self.inspector)
        self.dock_bottom = self._dock("분석", bottom_tabs)
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
        self.analysis_panel.navigate_requested.connect(self._navigate_to)
        self.exec_order_panel.navigate_requested.connect(self._navigate_to)

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

    def _on_scene_selection(self) -> None:
        name = self.scene.selected_node_name()
        self.view_state.select(name)
        if self.graph is not None:
            node = self.graph.node_by_name(name) if name else None
            self.inspector.show_node(node, self.graph)
        self.analysis_panel.highlight_node(name)
        self.exec_order_panel.highlight_node(name)

    def _on_type_toggled(self, type_name: str, hidden: bool) -> None:
        self.view_state.set_type_hidden(type_name, hidden)
        self.scene.apply_hidden_types(self.view_state.hidden_node_types)

    def _navigate_to(self, node_name: str) -> None:
        self.scene.select_node(node_name)
        item = self.scene.node_item(node_name)
        if item is not None:
            self.view.centerOn(item)

    def show_graph(self, graph: GraphModel) -> None:
        self.graph = graph
        self.scene.populate(graph)
        self.node_filter.set_graph(graph)
        self.inspector.show_node(None, graph)
        flow = analyze_flow(graph)
        self.analysis_panel.show_flow(flow)
        self.exec_order_panel.show_order(compute_execution_order(graph, flow))
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
git commit -m "feat(app): wire analysis dock (convergence/execution-order) into MainWindow"
```

---

## Task 4: 통합 스모크 테스트

실제 Orion 파일로 분석 도크 전 경로 검증.

**Files:**
- Test: `tests/core/app/test_phase2c_smoke.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/core/app/test_phase2c_smoke.py
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


def test_execution_order_populated_from_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    assert window.exec_order_panel.step_count() > 0


def test_convergence_panel_reports_no_fan_in(qtbot, orion_dir):
    # spec 2.3 / Phase 1: 제공 샘플은 실행 흐름이 전부 선형 → 수렴점 0
    window = _open(qtbot, orion_dir)
    assert window.analysis_panel.convergence_count() == 0
    assert "없음" in window.analysis_panel.summary_text()


def test_exec_order_navigation_selects_node(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    window.exec_order_panel.activate_row(0)         # 첫 실행 스텝
    assert window.scene.selected_node_name() is not None
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/core/app/test_phase2c_smoke.py -q`
Expected: PASS — 미처리 케이스가 드러나면 해당 모듈 수정 + 회귀 테스트 추가 후 재실행

- [ ] **Step 3: 전체 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS (Phase 1~2b 기존 125개 + Phase 2c 신규)

- [ ] **Step 4: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 하단 도크에 "수렴점"·"실행 순서" 탭. 실행 순서 탭에 들여쓴 노드 목록, 행 더블클릭 시 캔버스가 해당 노드로 이동

- [ ] **Step 5: Commit**

```bash
git add tests/core/app/test_phase2c_smoke.py
git commit -m "test(app): Phase 2c analysis dock smoke over real Orion file"
```

---

## Self-Review

**1. Spec coverage (Phase 2c 범위)**
- spec §7.2 분석 도크 — 수렴점 목록 탭 → Task 1·3 ✓
- spec §7.2 분석 도크 — 실행 순서 코드 뷰 탭 → Task 2·3 ✓
- spec §7.4 양방향 연동 — 패널 행 → 캔버스 이동, 캔버스 선택 → 패널 행 강조 → Task 3 ✓
- spec §2.3 fan-in 부재 — Task 1이 "수렴점 없음" 상태 처리, Task 1이 합성 fan-in 픽스처로 수렴점 표시 검증, Task 4가 실제 파일에서 0건 확인 ✓
- **범위 밖(Phase 2d, 의도적)**: 뷰 모드(연결된 핀만·깊이 펼침·fan-in 강조) — 분석 패널은 데이터 표시만, 캔버스 렌더링 불변
- **백로그 유지**: improver Phase 1.5/2a findings 7건 + 기능 아이디어 4건 (`docs/superpowers/backlog.md`)

**2. Placeholder scan** — "TBD/TODO" 없음. 모든 코드 단계에 실제 코드.

**3. Type consistency**
- `AnalysisPanel.show_flow`/`navigate_requested`/`convergence_count`/`has_convergence`/`activate_convergence`/`highlight_node`/`highlighted_node`/`summary_text` — Task 1 정의, Task 3·4 사용 일치
- `ExecutionOrderPanel.show_order`/`navigate_requested`/`step_count`/`row_text`/`activate_row`/`highlight_node`/`highlighted_node` — Task 2 정의, Task 3·4 사용 일치
- `analyze_flow(graph) -> FlowResult`, `FlowResult.convergence_points`/`.convergence(node)`, `Convergence.incoming_nodes`/`common_downstream` — Phase 1 분석 API, Task 1에서 사용 일치
- `compute_execution_order(graph, flow)` / `ExecutionStep.node`/`.depth` — Phase 1 분석 API, Task 2·3에서 사용 일치
- `MainWindow.analysis_panel`/`exec_order_panel`/`scene`/`graph` 속성 — Task 3 정의, Task 4 사용 일치
- Task 3가 `_wired_graph()` 헬퍼를 보강(`is_execution=True`) — `compute_execution_order`가 실행 엣지를 인식하는 데 필요. Phase 1.5 B1 이후 분석은 `is_execution` 플래그에 의존하므로 정합.

---

## 다음 단계 — Phase 2d

Phase 2c 완료 후 planner가 별도 계획 작성:
- 뷰 모드 — 연결된 핀만 표시, 깊이(서브핀) 펼침, fan-in 수렴점 강조 (NodeItem 렌더링 변경 + ViewState 확장 + 뷰 모드 툴바)
- 필요 시 `plugins/rigvm/view.py` (NodeColor 등 RigVM 고유 렌더)
- → Phase 2d 완료 시 spec §7 뷰어 전체 완성

그 다음 — **백로그 정리 batch** (`docs/superpowers/backlog.md`의 improver findings + 기능 아이디어, 착수 시 당시 코드 기준 재검토).
