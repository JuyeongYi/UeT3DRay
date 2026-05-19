# t3dgraph 백로그 정리 ②b — 뷰어 리팩토링 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** improver findings 중 뷰어 구조 리팩토링 5건을 수정한다 — 미사용 옵저버 제거, pin_status 문서 정합, 뷰 모드 안정 식별자, 패널 공용 베이스, MVC 규율 회복(모델 오케스트레이션을 Controller로).

**Architecture:** Phase 2 뷰어(`core/app/`)의 구조 정리. 동작은 보존하면서 중복·MVC 이탈을 바로잡는다. Model·분석 레이어 불변.

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt.

**선행 조건:** 백로그 정리 ①·②a 완료. 리포: `C:/Users/jylee/source/UeT3DRay`. (본 계획 코드는 ①·②a 적용 후 상태 기준.)

**근거:** `docs/superpowers/backlog.md` — improver findings P2b-B1·P2b-B3·P2c-B1·P2c-B2·P2d-B1.

**재검토 결과:** 5건 모두 현재 코드에서 유효. P2c-B2(MVC)는 Phase 2d로 더 커졌음(`_rebuild_scene` 등) — 본 계획에서 정리.

---

## File Structure (백로그 정리 ②b)

| 파일 | 변경 | finding |
| --- | --- | --- |
| `src/t3dgraph/core/app/view_state.py` | 수정 | 미사용 옵저버 제거 (P2b-B1) |
| `src/t3dgraph/core/app/pin_status.py` | 수정 | docstring 정합 (P2b-B3) |
| `src/t3dgraph/core/app/main_window.py` | 수정 | 뷰 모드 안정 식별자 + 분석 오케스트레이션 제거 (P2d-B1, P2c-B2) |
| `src/t3dgraph/core/app/navigable_panel.py` | 생성 | 패널 공용 베이스 (P2c-B1) |
| `src/t3dgraph/core/app/inspector_panel.py` | 수정 | 공용 베이스 상속 (P2c-B1) |
| `src/t3dgraph/core/app/analysis_panel.py` | 수정 | 공용 베이스 상속 (P2c-B1) |
| `src/t3dgraph/core/app/execution_order_panel.py` | 수정 | 공용 베이스 상속 (P2c-B1) |
| `src/t3dgraph/core/app/contracts.py` | 수정 | `show_analysis` 계약 추가 (P2c-B2) |
| `src/t3dgraph/core/app/controller.py` | 수정 | 분석 오케스트레이션 (P2c-B2) |

---

## Task 1: P2b-B1 — ViewState 미사용 옵저버 제거

`ViewState`의 `subscribe`/`_notify`/`_listeners`가 어디서도 구독되지 않는다(MainWindow는 직접 시그널 연결만 사용). 죽은 코드를 제거한다.

**Files:**
- Modify: `src/t3dgraph/core/app/view_state.py`
- Modify: `tests/core/app/test_view_state.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_view_state.py` — 옵저버를 검증하던 기존 테스트(`test_select_notifies`·`test_set_type_hidden_toggles_and_notifies`·`test_set_connected_only_notifies` 등 `subscribe`/`seen`/`calls`를 쓰는 테스트)를 옵저버 없는 형태로 교체하고, 옵저버 부재를 명시하는 테스트를 추가:

```python
def test_no_observer_api():
    vs = ViewState()
    assert not hasattr(vs, "subscribe")
    assert not hasattr(vs, "_notify")


def test_select_sets_value():
    vs = ViewState()
    vs.select("NodeA")
    assert vs.selected_node == "NodeA"


def test_set_type_hidden_toggles():
    vs = ViewState()
    vs.set_type_hidden("X", True)
    assert vs.is_type_hidden("X") is True
    vs.set_type_hidden("X", False)
    assert vs.is_type_hidden("X") is False


def test_view_mode_setters():
    vs = ViewState()
    vs.set_connected_pins_only(True)
    vs.set_expand_subpins(True)
    vs.set_fan_in_highlight(True)
    assert (vs.connected_pins_only, vs.expand_subpins, vs.fan_in_highlight) == (True, True, True)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_view_state.py -q`
Expected: FAIL — `test_no_observer_api`가 `subscribe` 존재로 실패

- [ ] **Step 3: 구현**

`core/app/view_state.py` — `_listeners` 필드, `subscribe`/`_notify` 메서드를 삭제하고, 각 setter의 `self._notify()` 호출을 제거. 결과:

```python
"""뷰어 표현 상태 — 선택·필터·뷰 모드. 순수 Python(Qt 없음)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ViewState:
    selected_node: str | None = None
    hidden_node_types: set[str] = field(default_factory=set)
    connected_pins_only: bool = False
    expand_subpins: bool = False
    fan_in_highlight: bool = False

    def select(self, node: str | None) -> None:
        self.selected_node = node

    def set_type_hidden(self, type_name: str, hidden: bool) -> None:
        if hidden:
            self.hidden_node_types.add(type_name)
        else:
            self.hidden_node_types.discard(type_name)

    def is_type_hidden(self, type_name: str) -> bool:
        return type_name in self.hidden_node_types

    def set_connected_pins_only(self, value: bool) -> None:
        self.connected_pins_only = value

    def set_expand_subpins(self, value: bool) -> None:
        self.expand_subpins = value

    def set_fan_in_highlight(self, value: bool) -> None:
        self.fan_in_highlight = value
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_view_state.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/view_state.py tests/core/app/test_view_state.py
git commit -m "refactor(app): remove unused ViewState observer (P2b-B1)"
```

---

## Task 2: P2b-B3 — pin_status docstring 정합

`pin_status` 모듈 docstring이 "교체 가능 전략"이라 하지만 구조는 단일 모듈 함수다. 과장된 표현을 실제에 맞게 정정한다.

**Files:**
- Modify: `src/t3dgraph/core/app/pin_status.py:1`

- [ ] **Step 1: 구현 (문서만 — 동작 변화 없음, 테스트 불필요)**

`core/app/pin_status.py` 의 모듈 docstring(1행)을 다음으로 교체:

```python
"""핀 '변경됨' 휴리스틱 — 타입 zero-value 비교 (spec §7.4).

`is_changed_from_default`는 모듈 수준 함수다. 더 정확한 판정(예: 노드 타입
아키타입 기본값 DB)으로 바꾸려면 이 함수를 대체하거나 호출부에서 다른
구현을 import하면 된다 — 별도의 전략 클래스 계층은 두지 않는다.
"""
```

- [ ] **Step 2: 회귀 확인**

Run: `python -m pytest tests/core/app/test_pin_status.py -q`
Expected: PASS — 동작 무변경, 기존 테스트 그대로 통과

- [ ] **Step 3: Commit**

```bash
git add src/t3dgraph/core/app/pin_status.py
git commit -m "docs(app): accurate pin_status module docstring (P2b-B3)"
```

---

## Task 3: P2d-B1 — 뷰 모드 안정 식별자

`set_view_mode`가 한글 UI 라벨 문자열을 프로그램 키로 쓴다 — 라벨이 바뀌면 API가 깨진다. 안정 식별자(`connected_only`·`expand_subpins`·`fan_in_highlight`)로 분리한다.

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/core/app/test_main_window.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_main_window.py` 에 추가:

```python
def test_set_view_mode_uses_stable_id(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.set_view_mode("connected_only", True)            # 한글 라벨 아닌 안정 ID
    assert w.view_state.connected_pins_only is True
```

기존 `set_view_mode("연결된 핀만", ...)` 등 한글 라벨 호출 테스트는 안정 ID로 갱신한다 (Step 3 참조).

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_main_window.py::test_set_view_mode_uses_stable_id -q`
Expected: FAIL — `set_view_mode("connected_only", ...)`가 라벨 매칭 실패로 무동작

- [ ] **Step 3: 구현**

`core/app/main_window.py` — `_build_view_mode_toolbar` 와 `set_view_mode` 를 안정 ID 기반으로 교체:

```python
    def _build_view_mode_toolbar(self) -> None:
        from PySide6.QtGui import QAction
        toolbar = self.addToolBar("뷰 모드")
        self._view_mode_actions: dict[str, QAction] = {}      # id → action
        specs = (
            ("connected_only", "연결된 핀만", self.view_state.set_connected_pins_only, False),
            ("expand_subpins", "깊이 펼침", self.view_state.set_expand_subpins, False),
            ("fan_in_highlight", "fan-in 강조", self.view_state.set_fan_in_highlight, True),
        )
        for mode_id, label, setter, in_place in specs:
            action = QAction(label, self)
            action.setCheckable(True)
            action.toggled.connect(
                lambda checked, s=setter, ip=in_place: self._on_view_mode(s, checked, ip))
            toolbar.addAction(action)
            self._view_mode_actions[mode_id] = action

    def set_view_mode(self, mode_id: str, checked: bool) -> None:
        """안정 식별자로 뷰 모드 토글 — connected_only / expand_subpins / fan_in_highlight."""
        action = self._view_mode_actions.get(mode_id)
        if action is not None:
            action.setChecked(checked)
```

> 주: 기존 속성 `view_mode_actions`(list)가 `_view_mode_actions`(dict)로 바뀐다. 이를 list로 순회하던 테스트(`test_view_mode_toolbar_has_three_toggles`)는 `w._view_mode_actions.values()`로 갱신한다.

`tests/core/app/test_main_window.py` — 한글 라벨을 쓰던 기존 호출을 안정 ID로 갱신: `set_view_mode("연결된 핀만", ...)` → `set_view_mode("connected_only", ...)`, `"깊이 펼침"` → `"expand_subpins"`, `"fan-in 강조"` → `"fan_in_highlight"`. 그리고 `test_view_mode_toolbar_has_three_toggles`는 `{a.text() for a in w._view_mode_actions.values()}` 로 갱신.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: PASS (갱신된 기존 + 신규)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window.py
git commit -m "refactor(app): stable identifiers for view-mode actions (P2d-B1)"
```

---

## Task 4: P2c-B1 — 패널 공용 베이스

inspector/analysis/execution_order 패널이 `navigate_requested` 시그널을 각자 선언한다. 공용 베이스 `NavigablePanel`로 추출한다.

**Files:**
- Create: `src/t3dgraph/core/app/navigable_panel.py`
- Modify: `src/t3dgraph/core/app/inspector_panel.py`
- Modify: `src/t3dgraph/core/app/analysis_panel.py`
- Modify: `src/t3dgraph/core/app/execution_order_panel.py`
- Test: `tests/core/app/test_navigable_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_navigable_panel.py
from t3dgraph.core.app.navigable_panel import NavigablePanel
from t3dgraph.core.app.inspector_panel import InspectorPanel
from t3dgraph.core.app.analysis_panel import AnalysisPanel
from t3dgraph.core.app.execution_order_panel import ExecutionOrderPanel


def test_panels_share_navigable_base(qtbot):
    for cls in (InspectorPanel, AnalysisPanel, ExecutionOrderPanel):
        panel = cls()
        qtbot.addWidget(panel)
        assert isinstance(panel, NavigablePanel)
        assert hasattr(panel, "navigate_requested")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_navigable_panel.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/navigable_panel.py
"""네비게이션 가능한 도크 패널의 공용 베이스."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class NavigablePanel(QWidget):
    """`navigate_requested(node_name)` 시그널을 공유하는 패널 베이스.

    행 활성화 시 캔버스를 해당 노드로 이동시키려는 패널들이 상속한다.
    """
    navigate_requested = Signal(str)
```

세 패널을 `NavigablePanel` 상속으로 변경:
- `inspector_panel.py` — import에 `from .navigable_panel import NavigablePanel` 추가, `class InspectorPanel(QWidget):` → `class InspectorPanel(NavigablePanel):`, 클래스 본문의 `navigate_requested = Signal(str)` 줄 삭제. `super().__init__()`는 그대로(베이스가 QWidget).
- `analysis_panel.py` — 동일: `class AnalysisPanel(NavigablePanel):`, 본문 `navigate_requested = Signal(str)` 삭제, import 추가.
- `execution_order_panel.py` — 동일: `class ExecutionOrderPanel(NavigablePanel):`, 본문 `navigate_requested = Signal(str)` 삭제, import 추가.

(각 파일에서 `Signal` import가 더 이상 안 쓰이면 정리. `Qt` 등 다른 import는 유지.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app -q`
Expected: PASS — 신규 + 기존 패널·메인윈도우 테스트 (시그널 동작 동일)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/navigable_panel.py src/t3dgraph/core/app/inspector_panel.py src/t3dgraph/core/app/analysis_panel.py src/t3dgraph/core/app/execution_order_panel.py tests/core/app/test_navigable_panel.py
git commit -m "refactor(app): NavigablePanel base for navigate_requested (P2c-B1)"
```

---

## Task 5: P2c-B2 — MVC: 분석 오케스트레이션을 Controller로

`MainWindow.show_graph`(View)가 `analyze_flow`/`compute_execution_order`(모델 연산)를 직접 호출한다. spec §4.1 MVC상 모델 오케스트레이션은 `AppController`의 몫. 분석 호출을 Controller로 옮긴다.

**Files:**
- Modify: `src/t3dgraph/core/app/contracts.py`
- Modify: `src/t3dgraph/core/app/controller.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/core/app/test_main_window.py`, `tests/core/app/test_controller.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_controller.py` 에 추가 (`_FakeView`에 `show_analysis` 추가 — Step 3에서):

```python
def test_controller_feeds_analysis_to_view(orion_dir):
    view = _FakeView()
    ctrl = AppController(view)
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    ctrl.open_file(str(f))
    assert view.shown is not None                       # show_graph 호출됨
    assert view.analysis is not None                    # show_analysis 호출됨
    flow, order = view.analysis
    assert len(order) >= 0 and hasattr(flow, "convergence_points")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_controller.py::test_controller_feeds_analysis_to_view -q`
Expected: FAIL — `AppController`가 분석을 수행·전달하지 않음

- [ ] **Step 3: 구현**

`core/app/contracts.py` — `AbstractGraphView`에 `show_analysis` 추상 메서드 추가:

```python
class AbstractGraphView(ABC):
    @abstractmethod
    def show_graph(self, graph: GraphModel) -> None:
        """주어진 GraphModel을 화면에 렌더링한다."""
        raise NotImplementedError

    @abstractmethod
    def show_analysis(self, flow, order) -> None:
        """분석 결과(FlowResult, 실행 순서)를 분석 도크에 표시한다."""
        raise NotImplementedError
```

`core/app/controller.py` — import 추가, `open_file`이 interpret 후 분석을 수행해 view에 전달:

```python
from ..analysis.flow import analyze_flow
from ..analysis.execution_order import compute_execution_order
```

`open_file`의 마지막 부분(`graph = ...; self.view.show_graph(graph)`)을 다음으로 교체:

```python
        graph = plugin.interpreter_factory().interpret(doc)
        self.view.show_graph(graph)
        flow = analyze_flow(graph)
        order = compute_execution_order(graph, flow)
        self.view.show_analysis(flow, order)
```

`core/app/main_window.py` — `show_graph`에서 분석 호출을 제거하고, `show_analysis`를 신설:

```python
    def show_graph(self, graph: GraphModel) -> None:
        self.graph = graph
        self.scene.populate(graph, view_state=self.view_state, flow=None)
        self.node_filter.set_graph(graph)
        self.inspector.show_node(None, graph)
        self.view.fit()
        self.statusBar().showMessage(
            f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}", 5000)

    def show_analysis(self, flow, order) -> None:
        self._flow = flow
        self.analysis_panel.show_flow(flow)
        self.exec_order_panel.show_order(order)
```

(`main_window.py`에서 `analyze_flow`·`compute_execution_order` import가 더 이상 안 쓰이면 제거.)

`tests/core/app/test_controller.py` — `_FakeView`에 `show_analysis` 구현 추가:

```python
class _FakeView(AbstractGraphView):
    def __init__(self):
        self.shown = None
        self.error = None
        self.analysis = None
    def show_graph(self, graph):
        self.shown = graph
    def show_analysis(self, flow, order):
        self.analysis = (flow, order)
    def show_error(self, message):
        self.error = message
```

`tests/core/app/test_main_window.py` — `show_graph`가 분석 도크를 더 이상 채우지 않으므로, 분석 도크를 검증하던 기존 테스트(`test_show_graph_populates_execution_order` 등)는 `show_graph` 호출 뒤 `w.show_analysis(analyze_flow(g), compute_execution_order(g))`를 함께 호출하도록 갱신하거나, `AppController` 경유로 검증하도록 바꾼다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app -q`
Expected: PASS — 갱신된 기존 + 신규

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/contracts.py src/t3dgraph/core/app/controller.py src/t3dgraph/core/app/main_window.py tests/core/app/test_controller.py tests/core/app/test_main_window.py
git commit -m "refactor(app): move analysis orchestration to AppController (P2c-B2)"
```

---

## Task 6: 전체 회귀 검증

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS — 기존 + 백로그 정리 ①·②a·②b 신규 테스트, 실패 0

- [ ] **Step 2: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 그래프·인스펙터·분석 도크·뷰 모드 모두 정상 (Controller가 분석 오케스트레이션)

(검증 전용 — 별도 커밋 없음.)

---

## Self-Review

**1. Findings coverage (그룹 ②b 범위)**
- P2b-B1 ViewState 미사용 옵저버 → Task 1 ✓
- P2b-B3 pin_status docstring → Task 2 ✓
- P2d-B1 뷰 모드 안정 식별자 → Task 3 ✓
- P2c-B1 패널 공용 베이스 → Task 4 ✓
- P2c-B2 MVC 분석 오케스트레이션 → Task 5 ✓
- → 그룹 ②b로 백로그의 improver 뷰어 findings 전부(②a 6 + ②b 5 + ① 이관·해소분) 처리 완료.
- **범위 밖**: FEAT-5(실행 순서 코드 렌더 고도화) → 그룹 ③.

**2. Placeholder scan** — "TBD/TODO" 없음. 모든 코드 단계에 실제 코드.

**3. Type consistency**
- `ViewState` setter들이 `_notify` 없이 값만 설정 — Task 1, 호출부(MainWindow)는 setter 반환값을 안 쓰므로 호환
- `set_view_mode(mode_id, checked)` + `_view_mode_actions: dict` — Task 3, 테스트 갱신 명시
- `NavigablePanel.navigate_requested` — Task 4, 세 패널이 상속·기존 `navigate_requested` 사용처(MainWindow `_wire`) 호환
- `AbstractGraphView.show_analysis` + `AppController` 호출 + `MainWindow.show_analysis` — Task 5 일관. `_FakeView`도 구현. `MainWindow._flow`는 `show_analysis`에서 설정 — Phase 2d `_rebuild_scene`·②a `apply_fan_in_highlight`가 쓰는 `self._flow`와 정합 (분석은 파일 로드 시 1회 수행되므로 토글 전에 항상 설정됨)

**의존성 주의:** Task 3·5가 모두 `main_window.py`를 수정 — 순차 적용(Task 3 먼저). Task 5의 `show_graph`/`show_analysis` 교체는 Task 3의 툴바 변경과 영역이 겹치지 않음.

---

## 다음 — 그룹 ③

그룹 ②b 완료 시 improver findings 전량 처리 완료. 남은 것:
- **그룹 ③** FEAT-5 — 실행 순서 패널 코드형 렌더링 고도화 (ForEach/Sequence 중첩·`name(){}` 드릴다운). planner가 별도 계획.
- 그 후 백로그 비움 (FEAT-1~4는 사용자 결정으로 범위 외 — backlog.md에 잔존).
