# Slice δ: AnalysisBundle (D-B3 + P2c-B2 잔여) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 분석 3종(flow, execution_order, data_flow)을 `AnalysisBundle`로 묶어 controller·view·MainWindow가 단일 출처에서 분석을 얻고 단일 view 메서드로 전달.

**Architecture:** `core/analysis/bundle.py`(신규)에 `AnalysisBundle` dataclass + `run(graph)`. `contracts.AbstractGraphView.show_analyses(bundle)` 추상 추가. MainWindow.`_render_current`와 controller.`open_file` 폴백이 같은 `bundle.run` 호출.

**Tech Stack:** Python 3.11+, PySide6, pytest.

**Spec ref:** `docs/superpowers/specs/2026-05-22-t3dgraph-batch-4-analysis-bundle-cleanup-design.md` §2 slice δ.

---

## 파일 구조

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/analysis/bundle.py` | 신규 — `AnalysisBundle` + `run` |
| `src/t3dgraph/core/analysis/__init__.py` | export 추가 |
| `src/t3dgraph/core/app/contracts.py` | `show_analyses(bundle)` 추상 추가; `show_analysis`/`show_data_flow`는 유지(deprecated docstring) |
| `src/t3dgraph/core/app/controller.py` | `bundle.run` 단일 호출, `view.show_analyses(bundle)` 우선 |
| `src/t3dgraph/core/app/main_window.py` | `_render_current`가 `bundle.run` 사용; `show_analyses` 구현(기존 `show_analysis`/`show_data_flow`로 위임) |
| `tests/core/analysis/test_bundle.py` | 신규 |
| `tests/core/app/test_controller_bundle.py` | 신규 |

---

### Task 1: `AnalysisBundle` + `run`

**Files:**
- Create: `src/t3dgraph/core/analysis/bundle.py`
- Modify: `src/t3dgraph/core/analysis/__init__.py`
- Create: `tests/core/analysis/test_bundle.py`

- [ ] **Step 1: Test**

`tests/core/analysis/test_bundle.py`:

```python
from t3dgraph.core.analysis.bundle import AnalysisBundle, run
from t3dgraph.core.analysis.flow import FlowResult
from t3dgraph.core.analysis.data_flow import DataFlowResult
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_run_returns_bundle_with_three_results():
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[Pin(name="O", cpp_type="float", direction="Output")]),
            Node(name="B", cls=None,
                 pins=[Pin(name="I", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.O", target_path="B.I")],
    )
    b = run(g)
    assert isinstance(b, AnalysisBundle)
    assert isinstance(b.flow, FlowResult)
    assert isinstance(b.data_flow, DataFlowResult)
    assert b.execution_order == []   # exec edge 없음


def test_bundle_carries_consistent_graph_analysis():
    """모든 분석이 같은 graph 인스턴스에 대한 결과여야 함."""
    g = GraphModel(nodes=[Node(name="X", cls=None)])
    b = run(g)
    assert b.data_flow.all_nodes == ["X"]
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/analysis/test_bundle.py -v
```

- [ ] **Step 3: Implement**

`src/t3dgraph/core/analysis/bundle.py`:

```python
"""분석 번들 — 그래프에 대한 모든 분석 결과를 한 객체로 묶는다."""
from __future__ import annotations
from dataclasses import dataclass
from ..base.graph_model import GraphModel
from .flow import FlowResult, analyze_flow
from .execution_order import ExecutionStep, compute_execution_order
from .data_flow import DataFlowResult, analyze_data_flow


@dataclass
class AnalysisBundle:
    flow: FlowResult
    execution_order: list[ExecutionStep]
    data_flow: DataFlowResult


def run(graph: GraphModel) -> AnalysisBundle:
    f = analyze_flow(graph)
    return AnalysisBundle(
        flow=f,
        execution_order=compute_execution_order(graph, f),
        data_flow=analyze_data_flow(graph),
    )
```

`__init__.py`에 export 추가:

```python
from .bundle import AnalysisBundle, run as run_analyses
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/analysis/bundle.py src/t3dgraph/core/analysis/__init__.py tests/core/analysis/test_bundle.py
git commit -m "feat(analysis): AnalysisBundle wrapping flow+order+data_flow (D-B3 prep)"
```

---

### Task 2: `AbstractGraphView.show_analyses` 계약

**Files:**
- Modify: `src/t3dgraph/core/app/contracts.py`

- [ ] **Step 1: 변경**

```python
from ..analysis.bundle import AnalysisBundle


class AbstractGraphView(ABC):
    @abstractmethod
    def show_graph(self, graph: GraphModel) -> None: ...

    @abstractmethod
    def show_analyses(self, bundle: AnalysisBundle) -> None:
        """모든 분석 결과(flow·execution_order·data_flow)를 한 번에 표시."""
        raise NotImplementedError

    # 기존 메서드는 한 cycle 유지 — 구체 구현이 위임 가능.
    @abstractmethod
    def show_analysis(self, flow, order) -> None: ...

    @abstractmethod
    def show_data_flow(self, result) -> None: ...
```

- [ ] **Step 2: 회귀 확인**

```
pytest tests/ -x
```

- [ ] **Step 3: Commit**

```
git add src/t3dgraph/core/app/contracts.py
git commit -m "refactor(contracts): add show_analyses(bundle) abstract (D-B3)"
```

---

### Task 3: `MainWindow.show_analyses` 구현

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: Test**

`tests/core/app/test_main_window_show_analyses.py`:

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.analysis.bundle import run as run_analyses
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_show_analyses_populates_all_panels(qapp):
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[Pin(name="O", cpp_type="float", direction="Output")]),
            Node(name="B", cls=None,
                 pins=[Pin(name="I", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.O", target_path="B.I")],
    )
    win = MainWindow()
    win.open_graph(g, label="t")
    # 패널이 채워졌는지 — data_flow_panel이 모든 노드 가지고 있는지
    assert {"A", "B"}.issubset(win.data_flow_panel.shown_node_names())
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: 변경**

`main_window.py`에 `show_analyses` 추가 + `_render_current` 단순화:

```python
def show_analyses(self, bundle) -> None:
    self.show_analysis(bundle.flow, bundle.execution_order)
    self.show_data_flow(bundle.data_flow)

def _render_current(self) -> None:
    current = self.graph_stack.current()
    if current is None:
        return
    self.graph = current
    from ..analysis.bundle import run as run_analyses
    bundle = run_analyses(current)
    self.scene.populate(current, view_state=self.view_state, flow=bundle.flow)
    self.node_filter.set_graph(current)
    self.inspector.show_node(None, current)
    self.view.fit()
    self.breadcrumb.set_segments(self.graph_stack.segments())
    self.statusBar().showMessage(
        f"노드 {len(current.nodes)} · 링크 {len(current.links)}", 5000)
    self.show_analyses(bundle)
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window_show_analyses.py
git commit -m "feat(main_window): show_analyses + _render_current uses bundle.run (D-B3, P2c-B2)"
```

---

### Task 4: `AppController.open_file` 단순화

**Files:**
- Modify: `src/t3dgraph/core/app/controller.py`
- Create: `tests/core/app/test_controller_bundle.py`

- [ ] **Step 1: 변경**

```python
from ..analysis.bundle import run as run_analyses


class AppController(AbstractGraphController):
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
            return
        # 레거시 view 폴백 — bundle.run로 단일 출처
        self.view.show_graph(graph)
        self.view.show_analyses(run_analyses(graph))
```

- [ ] **Step 2: Test**

`tests/core/app/test_controller_bundle.py`:

```python
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.controller import AppController
from t3dgraph.core.app.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_open_file_routes_to_open_graph_when_available(qapp, tmp_path):
    # 실데이터 대신 합성 t3d 한 줄
    sample = tmp_path / "x.t3d.txt"
    sample.write_text(
        "Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name=\"X\"\n"
        "End Object\n",
        encoding="utf-8",
    )
    win = MainWindow()
    ctl = AppController(win)
    ctl.open_file(str(sample))
    assert win.graph is not None
    assert any(n.name == "X" for n in win.graph.nodes)
```

- [ ] **Step 3: Run — pass**

```
pytest tests/core/app/test_controller_bundle.py -v
pytest tests/ -x
```

- [ ] **Step 4: Commit**

```
git add src/t3dgraph/core/app/controller.py tests/core/app/test_controller_bundle.py
git commit -m "refactor(controller): single source via run_analyses (D-B3, P2c-B2 fixed)"
```

---

### Task 5: 회귀 + Orion smoke

- [ ] **Step 1**: `pytest tests/ -v` → PASS

- [ ] **Step 2**: Orion 합성 smoke — `tests/smoke_bundle_orion.py`:

```python
from pathlib import Path
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from t3dgraph.core.analysis.bundle import run as run_analyses

p = Path("Orion_WorkStation_Rig_Analysis/"
         "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
g = default_registry().detect(parse_document(read_t3d_text(p))).interpreter_factory().interpret(parse_document(read_t3d_text(p)))
b = run_analyses(g)
print(f"flow exec edges {len(b.flow.execution_edges)} · steps {len(b.execution_order)} · data edges {len(b.data_flow.data_edges)}")
assert b.data_flow.all_nodes
```

- [ ] **Step 3: Commit smoke**

---

## 완료 정의

- [ ] Task 1-5 PASS
- [ ] `bundle.run(graph)`이 분석 3종 단일 출처
- [ ] MainWindow와 AppController 모두 `bundle.run`만 호출 (분석 함수 직접 호출 ✗)
- [ ] `show_analyses(bundle)` 계약 + 구체 구현
- [ ] 기존 `show_analysis`/`show_data_flow`는 한 cycle 유지 (다음 cycle에 deprecation 진행)
