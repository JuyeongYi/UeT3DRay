# Slice θ-1: Sink 단위 compute trace (FEAT-8) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** sink에서 출발해 의존 ancestor를 DAG depth별로 그룹화한 평탄 트레이스를 산출하고, `DataFlowPanel`에 sink 선택 시 텍스트 박스로 표시.

**Architecture:** `core/analysis/compute_trace.py`(신규) — `compute_trace(sink, incoming_nodes, max_depth)` → `list[TraceLevel]`. `DataFlowPanel`에 보조 `QPlainTextEdit` 추가. sink 항목 클릭(=현재 navigate_requested) 시 별도 시그널로 trace 갱신.

**Spec ref:** `2026-05-22-t3dgraph-batch-7-analysis-vis-design.md` §θ-1.

---

### Task 1: `compute_trace` 분석기

**Files:**
- Create: `src/t3dgraph/core/analysis/compute_trace.py`
- Create: `tests/core/analysis/test_compute_trace.py`

- [ ] **Step 1: Tests**

```python
from t3dgraph.core.analysis.compute_trace import compute_trace, TraceLevel


def test_compute_trace_levels_in_simple_chain():
    incoming = {"S": ["B"], "B": ["A"], "A": []}
    levels = compute_trace("S", incoming)
    assert levels == [
        TraceLevel(depth=0, nodes=["S"]),
        TraceLevel(depth=1, nodes=["B"]),
        TraceLevel(depth=2, nodes=["A"]),
    ]


def test_compute_trace_fan_in_groups_at_same_depth():
    incoming = {"S": ["A", "B"], "A": [], "B": []}
    levels = compute_trace("S", incoming)
    assert levels[0] == TraceLevel(depth=0, nodes=["S"])
    assert sorted(levels[1].nodes) == ["A", "B"]


def test_compute_trace_dedup_across_paths():
    incoming = {"S": ["A", "B"], "A": ["C"], "B": ["C"], "C": []}
    levels = compute_trace("S", incoming)
    # C는 한 번만
    flat = [n for lv in levels for n in lv.nodes]
    assert flat.count("C") == 1


def test_compute_trace_cycle_safe():
    incoming = {"A": ["B"], "B": ["A"]}
    levels = compute_trace("A", incoming, max_depth=5)
    flat = [n for lv in levels for n in lv.nodes]
    assert flat.count("A") == 1
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

```python
"""sink → ancestor 레벨별 평탄 트레이스."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass


@dataclass
class TraceLevel:
    depth: int
    nodes: list[str]


def compute_trace(
    sink: str,
    incoming_nodes: dict[str, list[str]],
    max_depth: int = 64,
) -> list[TraceLevel]:
    """BFS — 같은 depth에 도달한 노드들을 한 레벨로 그룹. dedupe + cycle safe."""
    seen: set[str] = set()
    levels: list[TraceLevel] = []
    frontier: list[str] = [sink]
    depth = 0
    while frontier and depth <= max_depth:
        # 이번 레벨의 노드 — dedupe + sort
        unique = sorted({n for n in frontier if n not in seen})
        if not unique:
            break
        levels.append(TraceLevel(depth=depth, nodes=unique))
        seen.update(unique)
        nxt: list[str] = []
        for n in unique:
            for parent in incoming_nodes.get(n, []):
                if parent not in seen:
                    nxt.append(parent)
        frontier = nxt
        depth += 1
    return levels
```

- [ ] **Step 4: Run·Commit**

```
git add src/t3dgraph/core/analysis/compute_trace.py tests/core/analysis/test_compute_trace.py
git commit -m "feat(analysis): compute_trace BFS-level flatten (FEAT-8)"
```

---

### Task 2: DataFlowPanel에 trace 표시

**Files:**
- Modify: `src/t3dgraph/core/app/data_flow_panel.py`
- Create: `tests/core/app/test_data_flow_trace.py`

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.data_flow_panel import DataFlowPanel
from t3dgraph.core.analysis.data_flow import DataFlowResult, DataFlowEdge
from t3dgraph.core.base.pin_ref import PinRef


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_panel_shows_trace_on_sink_activate(qapp):
    edges = [
        DataFlowEdge(PinRef("A", "O"), PinRef("S", "I")),
    ]
    r = DataFlowResult(
        data_edges=edges,
        inputs_of={"S": edges},
        outputs_of={"A": edges},
        incoming_nodes={"S": ["A"]},
        outgoing_nodes={"A": ["S"]},
        sinks=["S"], sources=["A"], isolated=[],
        all_nodes=["A", "S"],
    )
    panel = DataFlowPanel()
    panel.show_result(r)
    # sink 항목 활성화
    items = panel.items_for("S")
    panel._on_activated(items[0], 0)
    trace_text = panel.trace_text()
    assert "S" in trace_text
    assert "A" in trace_text
    assert "level" in trace_text.lower() or "depth" in trace_text.lower() or "단계" in trace_text
```

- [ ] **Step 2: Implement**

`data_flow_panel.py`에 텍스트 박스 + trace 갱신 로직:

```python
from PySide6.QtWidgets import QPlainTextEdit, QSplitter
from PySide6.QtCore import Qt
from ..analysis.compute_trace import compute_trace, TraceLevel


# DataFlowPanel.__init__ 안 — tree 옆에 텍스트 박스
self._trace = QPlainTextEdit()
self._trace.setReadOnly(True)
self._trace.setPlaceholderText("(sink 선택 시 의존 트레이스)")
splitter = QSplitter(Qt.Vertical)
splitter.addWidget(self._tree)
splitter.addWidget(self._trace)
layout.addWidget(splitter)

# show_result 마지막에 트레이스 초기화
self._trace.setPlainText("")
self._incoming_cache = r.incoming_nodes

# _on_activated 보강
def _on_activated(self, item, _col):
    name = item.data(0, _NODE_ROLE)
    if not name:
        return
    self.navigate_requested.emit(name)
    self._update_trace(name)


def _update_trace(self, node: str) -> None:
    if not hasattr(self, "_incoming_cache") or self._incoming_cache is None:
        return
    levels = compute_trace(node, self._incoming_cache)
    lines = [f"sink: {node}"]
    for lv in levels:
        if lv.depth == 0:
            continue
        lines.append(f"  level {lv.depth}: {', '.join(lv.nodes)}")
    self._trace.setPlainText("\n".join(lines))


def trace_text(self) -> str:
    return self._trace.toPlainText()
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/data_flow_panel.py tests/core/app/test_data_flow_trace.py
git commit -m "feat(data_flow_panel): compute trace text on sink activate (FEAT-8)"
```

---

### Task 3: 회귀

```
pytest tests/ -v
```

---

## 완료 정의

- [ ] Task 1-3 PASS
- [ ] `compute_trace(sink, incoming, max_depth)` BFS·dedupe·cycle-safe
- [ ] DataFlowPanel sink 활성화 시 trace 텍스트 갱신
