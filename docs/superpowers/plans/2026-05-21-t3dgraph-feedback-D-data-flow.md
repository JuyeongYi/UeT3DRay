# Slice D: 데이터 흐름 분석 + 패널 (F2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실행 핀 흐름과 별개로 *데이터 핀 흐름*을 분석·시각화한다. 사용자가 "계산 결과값이 더 중요한 경우가 많다"고 한 피드백 대응. 기존 ExecutionOrderPanel은 그대로 유지하고, 하단 도크에 "계산 흐름" 탭을 추가.

**Architecture:** `core/analysis/data_flow.py`에 `analyze_data_flow(graph) -> DataFlowResult`. 새 패널 `DataFlowPanel`은 sinks(출력 없는 노드)부터 역방향 위상 정렬로 "결과 → 입력" 트리 표시. controller가 흐름을 계산해 view에 전달.

**Tech Stack:** Python 3.11+, PySide6, pytest.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-user-feedback-batch-design.md` §5.6.

**노드 보존 불변식(PRESERVE-ALL):** 데이터 흐름 분석 결과에 일부 노드(완전 고립된 상수 등)가 sink/source 어느 분류에도 안 들어가도 패널에 *고립 그룹*으로 표시. 누락 ✗.

---

## 파일 구조

| 파일 | 책임 | 변경 종류 |
|---|---|---|
| `src/t3dgraph/core/analysis/data_flow.py` | `analyze_data_flow` + `DataFlowResult` | 신규 |
| `src/t3dgraph/core/app/data_flow_panel.py` | 패널 위젯 — 트리 형태 결과 표시 + 네비게이션 | 신규 |
| `src/t3dgraph/core/app/main_window.py` | 하단 도크 탭에 "계산 흐름" 추가 + show_data_flow 메서드 | 수정 |
| `src/t3dgraph/core/app/controller.py` | `analyze_data_flow` 호출 + view에 전달 | 수정 |
| `src/t3dgraph/core/app/contracts.py` | `AbstractGraphView` 계약에 `show_data_flow` 추가(있다면) | 수정 |
| `tests/core/analysis/test_data_flow.py` | 분석 단위 | 신규 |
| `tests/core/app/test_data_flow_panel.py` | 패널 통합 (pytest-qt) | 신규 |

---

### Task 1: data_flow 분석기 — 기본 케이스

**Files:**
- Create: `src/t3dgraph/core/analysis/data_flow.py`
- Create: `tests/core/analysis/test_data_flow.py`

- [ ] **Step 1: Failing tests — 기본 데이터 엣지**

`tests/core/analysis/test_data_flow.py`:

```python
from t3dgraph.core.analysis.data_flow import analyze_data_flow, DataFlowResult
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def _node(name, *pins):
    return Node(name=name, cls=None, pins=list(pins))


def _data_pin(name, direction):
    return Pin(name=name, cpp_type="float", direction=direction, is_execution=False)


def _exec_pin(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def test_data_edges_exclude_exec_links():
    g = GraphModel(
        nodes=[
            _node("Src", _data_pin("Out", "Output")),
            _node("Dst", _data_pin("In", "Input")),
            _node("ExecA", _exec_pin("EOut", "Output")),
            _node("ExecB", _exec_pin("EIn", "Input")),
        ],
        links=[
            Link(source_path="Src.Out", target_path="Dst.In"),       # 데이터
            Link(source_path="ExecA.EOut", target_path="ExecB.EIn"),  # exec
        ],
    )
    r = analyze_data_flow(g)
    assert ("Src", "Dst") in r.data_edges
    assert ("ExecA", "ExecB") not in r.data_edges


def test_inputs_outputs_indices():
    g = GraphModel(
        nodes=[
            _node("A", _data_pin("O", "Output")),
            _node("B", _data_pin("O", "Output")),
            _node("C", _data_pin("I1", "Input"), _data_pin("I2", "Input")),
        ],
        links=[
            Link(source_path="A.O", target_path="C.I1"),
            Link(source_path="B.O", target_path="C.I2"),
        ],
    )
    r = analyze_data_flow(g)
    assert sorted(r.inputs_of["C"]) == ["A", "B"]
    assert r.outputs_of["A"] == ["C"]
    assert r.outputs_of["B"] == ["C"]


def test_sinks_and_sources():
    g = GraphModel(
        nodes=[
            _node("Const", _data_pin("Out", "Output")),
            _node("Compute", _data_pin("In", "Input"), _data_pin("Out", "Output")),
            _node("Sink", _data_pin("In", "Input")),
        ],
        links=[
            Link(source_path="Const.Out", target_path="Compute.In"),
            Link(source_path="Compute.Out", target_path="Sink.In"),
        ],
    )
    r = analyze_data_flow(g)
    assert r.sources == ["Const"]
    assert r.sinks == ["Sink"]


def test_isolated_nodes_in_all_nodes():
    """PRESERVE-ALL: 고립 노드도 결과에 모두 등장(고립 그룹용)."""
    g = GraphModel(
        nodes=[_node("X", _data_pin("In", "Input")), _node("Y", _data_pin("Out", "Output"))],
        links=[],
    )
    r = analyze_data_flow(g)
    assert set(r.all_nodes) == {"X", "Y"}
    assert r.isolated == ["X", "Y"]


def test_handles_cycles_without_recursion_blowup():
    g = GraphModel(
        nodes=[
            _node("A", _data_pin("I", "Input"), _data_pin("O", "Output")),
            _node("B", _data_pin("I", "Input"), _data_pin("O", "Output")),
        ],
        links=[
            Link(source_path="A.O", target_path="B.I"),
            Link(source_path="B.O", target_path="A.I"),
        ],
    )
    r = analyze_data_flow(g)
    # 순환이라 sink/source 둘 다 없을 수 있음 — 폭주만 막으면 됨
    assert ("A", "B") in r.data_edges
    assert ("B", "A") in r.data_edges
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/analysis/test_data_flow.py -v
```
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

`src/t3dgraph/core/analysis/data_flow.py`:

```python
"""데이터 흐름 분석 — exec 핀이 아닌 핀들 사이의 링크."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin
from ..t3d.paths import node_of, pin_segment


@dataclass
class DataFlowResult:
    data_edges: list[tuple[str, str]] = field(default_factory=list)
    inputs_of: dict[str, list[str]] = field(default_factory=dict)
    outputs_of: dict[str, list[str]] = field(default_factory=dict)
    sinks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    isolated: list[str] = field(default_factory=list)
    all_nodes: list[str] = field(default_factory=list)


def _exec_pin_paths(graph: GraphModel) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()

    def walk(node_name: str, pin: Pin, prefix: str) -> None:
        full = f"{prefix}.{pin.name}"
        if pin.is_execution:
            out.add((node_name, full[len(node_name) + 1:]))
        for sp in pin.subpins:
            walk(node_name, sp, full)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    return out


def analyze_data_flow(graph: GraphModel) -> DataFlowResult:
    exec_paths = _exec_pin_paths(graph)
    edges: list[tuple[str, str]] = []
    for link in graph.links:
        s_node = node_of(link.source_path)
        t_node = node_of(link.target_path)
        s_pin_path = link.source_path[len(s_node) + 1:] if "." in link.source_path else ""
        t_pin_path = link.target_path[len(t_node) + 1:] if "." in link.target_path else ""
        if (s_node, s_pin_path) in exec_paths or (t_node, t_pin_path) in exec_paths:
            continue
        edges.append((s_node, t_node))

    inputs_of: dict[str, list[str]] = {}
    outputs_of: dict[str, list[str]] = {}
    for s, t in edges:
        outputs_of.setdefault(s, []).append(t)
        inputs_of.setdefault(t, []).append(s)

    all_nodes = [n.name for n in graph.nodes]
    nodes_with_data = {x for pair in edges for x in pair}
    sources = sorted(n for n in nodes_with_data
                     if not inputs_of.get(n) and outputs_of.get(n))
    sinks = sorted(n for n in nodes_with_data
                   if inputs_of.get(n) and not outputs_of.get(n))
    isolated = sorted(n for n in all_nodes if n not in nodes_with_data)

    return DataFlowResult(
        data_edges=edges,
        inputs_of=inputs_of,
        outputs_of=outputs_of,
        sinks=sinks,
        sources=sources,
        isolated=isolated,
        all_nodes=all_nodes,
    )
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/analysis/test_data_flow.py -v
```
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/analysis/data_flow.py tests/core/analysis/test_data_flow.py
git commit -m "feat(analysis): data flow analyzer (F2)"
```

---

### Task 2: backward dependency tree — sink 기준 역추적

**Files:**
- Modify: `src/t3dgraph/core/analysis/data_flow.py`
- Modify: `tests/core/analysis/test_data_flow.py`

패널이 sink 기준으로 트리를 그리려면 분석 결과에 "sink → 의존 트리(중복 노드 cap)" 형태가 필요. 별도 함수로 노출.

- [ ] **Step 1: Test**

`tests/core/analysis/test_data_flow.py`에 추가:

```python
from t3dgraph.core.analysis.data_flow import dependency_tree


def test_dependency_tree_basic():
    inputs_of = {
        "Sink": ["Mul"],
        "Mul": ["A", "B"],
        "A": [],
        "B": [],
    }
    tree = dependency_tree("Sink", inputs_of)
    assert tree.node == "Sink"
    children = [c.node for c in tree.children]
    assert children == ["Mul"]
    leaf_kids = [c.node for c in tree.children[0].children]
    assert sorted(leaf_kids) == ["A", "B"]


def test_dependency_tree_cycle_protection():
    inputs_of = {
        "A": ["B"],
        "B": ["A"],   # 순환
    }
    tree = dependency_tree("A", inputs_of, max_depth=10)
    # 자기 자신은 자식으로 두 번 등장 안 함 — 첫 등장에서 잘림
    def walk(n, seen):
        seen.append(n.node)
        for c in n.children:
            walk(c, seen)
    seen = []
    walk(tree, seen)
    assert seen.count("A") == 1
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/analysis/test_data_flow.py -v
```
Expected: FAIL (`dependency_tree` missing).

- [ ] **Step 3: Implement**

`src/t3dgraph/core/analysis/data_flow.py`에 추가:

```python
@dataclass
class DepNode:
    node: str
    children: list["DepNode"] = field(default_factory=list)


def dependency_tree(
    sink: str,
    inputs_of: dict[str, list[str]],
    max_depth: int = 64,
) -> DepNode:
    """sink에서 출발해 입력 노드들을 자식으로 펼친 트리.

    노드 중복 cap: 한 번 본 노드는 children에 두지 않음(순환·DAG fan-in 보호).
    """
    seen: set[str] = set()

    def build(name: str, depth: int) -> DepNode:
        node = DepNode(node=name)
        if depth >= max_depth or name in seen:
            return node
        seen.add(name)
        for src in inputs_of.get(name, []):
            node.children.append(build(src, depth + 1))
        return node

    return build(sink, 0)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/analysis/test_data_flow.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/analysis/data_flow.py tests/core/analysis/test_data_flow.py
git commit -m "feat(data_flow): dependency_tree from sink (F2)"
```

---

### Task 3: DataFlowPanel — UI 위젯

**Files:**
- Create: `src/t3dgraph/core/app/data_flow_panel.py`
- Create: `tests/core/app/test_data_flow_panel.py`

- [ ] **Step 1: Test (pytest-qt)**

`tests/core/app/test_data_flow_panel.py`:

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.analysis.data_flow import DataFlowResult, DepNode
from t3dgraph.core.app.data_flow_panel import DataFlowPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _result_with_two_sinks():
    return DataFlowResult(
        data_edges=[("A", "S1"), ("B", "S1"), ("C", "S2")],
        inputs_of={"S1": ["A", "B"], "S2": ["C"]},
        outputs_of={"A": ["S1"], "B": ["S1"], "C": ["S2"]},
        sinks=["S1", "S2"],
        sources=["A", "B", "C"],
        isolated=["X"],                      # PRESERVE-ALL — 고립 노드
        all_nodes=["A", "B", "C", "S1", "S2", "X"],
    )


def test_panel_shows_each_sink_and_isolated_group(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    labels = panel.top_level_labels()
    assert any("S1" in l for l in labels)
    assert any("S2" in l for l in labels)
    assert any("고립" in l or "isolated" in l.lower() for l in labels)


def test_panel_emits_navigate_on_double_click(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    received = []
    panel.navigate_requested.connect(received.append)
    panel.activate_node("A")
    assert "A" in received


def test_panel_preserves_all_nodes(qapp):
    """PRESERVE-ALL: 패널이 표시하는 노드 = 그래프의 모든 노드."""
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    shown = panel.shown_node_names()
    assert shown == {"A", "B", "C", "S1", "S2", "X"}
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_data_flow_panel.py -v
```
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

`src/t3dgraph/core/app/data_flow_panel.py`:

```python
"""계산(데이터) 흐름 패널 — sink별 의존 트리 + 고립 노드 그룹."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
)
from ..analysis.data_flow import DataFlowResult, dependency_tree, DepNode
from .navigable_panel import NavigablePanel

_NODE_ROLE = Qt.UserRole + 1
_INDENT = "    "


class DataFlowPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._summary = QLabel("(그래프를 열어주세요)")
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["sink/노드 ← 의존"])
        layout.addWidget(self._summary)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        self._items: dict[str, QTreeWidgetItem] = {}

    def show_result(self, r: DataFlowResult) -> None:
        self._tree.clear()
        self._items = {}
        if not r.all_nodes:
            self._summary.setText("(노드 없음)")
            return
        self._summary.setText(
            f"sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")

        for sink in r.sinks:
            tree = dependency_tree(sink, r.inputs_of)
            top = self._add_tree(tree, self._tree.invisibleRootItem())
            top.setExpanded(True)

        # 표시되지 않은(sink 트리에 안 들어간) 노드들 → '고립' 그룹 (PRESERVE-ALL)
        shown = set(self._items.keys())
        unshown = [n for n in r.all_nodes if n not in shown]
        if unshown:
            group = QTreeWidgetItem(["고립/미연결"])
            self._tree.addTopLevelItem(group)
            for name in unshown:
                child = QTreeWidgetItem([name])
                child.setData(0, _NODE_ROLE, name)
                group.addChild(child)
                self._items[name] = child

    def _add_tree(self, dep: DepNode, parent: QTreeWidgetItem) -> QTreeWidgetItem:
        item = QTreeWidgetItem([dep.node])
        item.setData(0, _NODE_ROLE, dep.node)
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)
        self._items.setdefault(dep.node, item)
        for c in dep.children:
            self._add_tree(c, item)
        return item

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        name = item.data(0, _NODE_ROLE)
        if name:
            self.navigate_requested.emit(name)

    def activate_node(self, name: str) -> None:
        item = self._items.get(name)
        if item is not None:
            self._on_activated(item, 0)

    def top_level_labels(self) -> list[str]:
        out: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            out.append(self._tree.topLevelItem(i).text(0))
        return out

    def shown_node_names(self) -> set[str]:
        return set(self._items.keys())

    def highlight_node(self, node: str | None) -> None:
        item = self._items.get(node) if node else None
        if item is not None:
            self._tree.setCurrentItem(item)
        else:
            self._tree.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._tree.currentItem()
        return item.data(0, _NODE_ROLE) if item is not None else None
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_data_flow_panel.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/data_flow_panel.py tests/core/app/test_data_flow_panel.py
git commit -m "feat(app): DataFlowPanel widget (F2)"
```

---

### Task 4: MainWindow + Controller — 패널 통합

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `src/t3dgraph/core/app/controller.py`
- Modify: `src/t3dgraph/core/app/contracts.py` (계약에 `show_data_flow` 있다면)

- [ ] **Step 1: 변경 — MainWindow**

`main_window.py`:

```python
# import 추가
from .data_flow_panel import DataFlowPanel

# __init__ 안 — 기존 ExecutionOrderPanel 옆에
self.data_flow_panel = DataFlowPanel()

bottom_tabs = QTabWidget()
bottom_tabs.addTab(self.analysis_panel, "수렴점")
bottom_tabs.addTab(self.exec_order_panel, "실행 순서")
bottom_tabs.addTab(self.data_flow_panel, "계산 흐름")          # NEW

# _wire 안 — navigate
self.data_flow_panel.navigate_requested.connect(self._navigate_to)

# _on_scene_selection 안 — 선택 동기화
self.data_flow_panel.highlight_node(name)

# 새 메서드
def show_data_flow(self, result) -> None:
    self.data_flow_panel.show_result(result)
```

- [ ] **Step 2: 변경 — controller**

`controller.py:open_file`의 분석 호출부:

```python
from ..analysis.data_flow import analyze_data_flow
# ...
flow = analyze_flow(graph)
order = compute_execution_order(graph, flow)
data_flow = analyze_data_flow(graph)
self.view.show_analysis(flow, order)
self.view.show_data_flow(data_flow)
```

- [ ] **Step 3: contracts**

`src/t3dgraph/core/app/contracts.py`에 `AbstractGraphView` 추상 메서드 시그니처 있으면 `show_data_flow` 추가. 없으면 skip(duck-typed).

- [ ] **Step 4: 통합 테스트**

`tests/core/app/test_data_flow_integration.py`(신규):

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_open_pipeline_populates_data_flow_panel(qapp, tmp_path):
    # 단순 합성 그래프 직접 주입 — 파일 로드 우회
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[Pin(name="Out", cpp_type="float", direction="Output")]),
            Node(name="B", cls=None,
                 pins=[Pin(name="In", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )
    win = MainWindow()
    win.show_graph(g)
    from t3dgraph.core.analysis.data_flow import analyze_data_flow
    win.show_data_flow(analyze_data_flow(g))
    # 모든 노드 보존
    assert win.data_flow_panel.shown_node_names() >= {"A", "B"}
```

- [ ] **Step 5: Run — pass**

```
pytest tests/core/app/test_data_flow_integration.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add src/t3dgraph/core/app/main_window.py \
        src/t3dgraph/core/app/controller.py \
        src/t3dgraph/core/app/contracts.py \
        tests/core/app/test_data_flow_integration.py
git commit -m "feat(app): wire data flow analysis into pipeline (F2)"
```

---

### Task 5: 회귀 + Orion smoke

**Files:**
- Run: `pytest tests/ -v`

- [ ] **Step 1: 전체 회귀**

```
pytest tests/ -v
```
Expected: PASS.

- [ ] **Step 2: Orion RigVMModel.t3d.txt smoke — 데이터 흐름 결과 비어있지 않은지**

`tests/smoke_data_flow_orion.py`(신규):

```python
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from t3dgraph.core.analysis.data_flow import analyze_data_flow
from pathlib import Path

p = Path("Orion_WorkStation_Rig_Analysis/"
         "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
g = default_registry().detect(parse_document(read_t3d_text(p))).interpreter_factory().interpret(parse_document(read_t3d_text(p)))
r = analyze_data_flow(g)
print(f"data edges {len(r.data_edges)} · sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")
# PRESERVE-ALL — all_nodes 가 그래프 노드 수와 일치
assert set(r.all_nodes) == {n.name for n in g.nodes}
```

실행: `python tests/smoke_data_flow_orion.py`

- [ ] **Step 3: Commit (smoke 추가했으면)**

```
git add tests/smoke_data_flow_orion.py
git commit -m "test: smoke for data flow on Orion RigVMModel (PRESERVE-ALL)"
```

---

## 완료 정의

- [ ] 모든 Task 1-5 체크박스 PASS
- [ ] `analyze_data_flow`가 exec 링크를 제외한 데이터 엣지만 반환
- [ ] PRESERVE-ALL — `r.all_nodes`가 graph.nodes 와 일치, 고립 노드는 패널에 *고립* 그룹으로 표시
- [ ] 하단 도크에 새 탭 "계산 흐름" 존재
- [ ] 패널 더블클릭 → 캔버스 네비게이션
- [ ] 기존 "실행 순서"·"수렴점" 패널 동작 영향 없음
