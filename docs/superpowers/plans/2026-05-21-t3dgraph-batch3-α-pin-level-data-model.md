# Slice α: 핀 단위 데이터 흐름 모델 (D-A1·A2·A3·B1·B2 + BL1-B1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DataFlowResult.data_edges`가 노드 쌍만 보존하던 정보 손실을 핀 단위로 끌어올린다. `PinRef`·`DataFlowEdge` 도입, adjacency 중복 제거, 핀 경로 헬퍼 `pin_rel_path`를 `core/base/paths.py`로 통합, 패널이 같은 노드 다중 등장도 모두 인덱싱하고 핀 라벨을 렌더.

**Architecture:** 신규 `PinRef`(frozen dataclass)와 `DataFlowEdge`로 핀 정보 보존. `inputs_of/outputs_of`는 `dict[str, list[DataFlowEdge]]`로, 노드 단위 호환 슬롯 `incoming_nodes/outgoing_nodes`를 별도 추가. `core/t3d/paths.py`는 re-export shim으로 두고 신규 import는 `core/base/paths.py`만 사용.

**Tech Stack:** Python 3.11+, PySide6, pytest, pytest-qt.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-batch-3-info-preservation-design.md` §5.1, §5.2.

**PRESERVE-INFO 불변식:** link의 핀 정보를 `data_edges`에 끝까지 보존. 다중 링크는 *드러내야 할 사실*이라 dedupe 후에도 노드 단위로 압축 안 함(엣지 수 = link 수).

---

## 파일 구조

| 파일 | 책임 | 변경 |
|---|---|---|
| `src/t3dgraph/core/base/paths.py` | 핀/클래스 경로 헬퍼 — 새 정규 위치 | 신규 |
| `src/t3dgraph/core/t3d/paths.py` | re-export shim(`from ..base.paths import *`) — batch ④에서 제거 예정 | 수정 |
| `src/t3dgraph/core/base/pin_ref.py` | `PinRef` 모델 | 신규 |
| `src/t3dgraph/core/analysis/data_flow.py` | `DataFlowEdge` + 핀 단위 분석, adjacency dedupe | 수정 |
| `src/t3dgraph/core/app/data_flow_panel.py` | 핀 라벨 렌더 + 다중 인덱싱 + "[위 참조]" | 수정 |
| `src/t3dgraph/core/app/contracts.py` · `main_window.py` | `show_data_flow(result: DataFlowResult)` 타입힌트 | 수정 |
| `tests/core/base/test_paths.py` | 신규 paths 헬퍼 단위 | 신규 |
| `tests/core/base/test_pin_ref.py` | `PinRef` 단위 | 신규 |
| `tests/core/analysis/test_data_flow.py` | 핀 단위 엣지·중복 제거·다중 링크 | 수정 |
| `tests/core/app/test_data_flow_panel.py` | 핀 라벨·다중 인덱싱·[위 참조] | 수정 |

---

### Task 1: `core/base/paths.py` 신규 + `pin_rel_path`

**Files:**
- Create: `src/t3dgraph/core/base/paths.py`
- Create: `tests/core/base/test_paths.py`

- [ ] **Step 1: Failing tests**

`tests/core/base/test_paths.py`:

```python
from t3dgraph.core.base.paths import (
    node_of, pin_segment, pin_rel_path, type_suffix,
)


def test_node_of_basic():
    assert node_of("MyNode.Pin.Sub") == "MyNode"
    assert node_of("Only") == "Only"


def test_pin_segment_indices():
    assert pin_segment("A.B.C", 0) == "A"
    assert pin_segment("A.B.C", 1) == "B"
    assert pin_segment("A.B.C", 5) == ""


def test_pin_rel_path_strips_node_prefix():
    assert pin_rel_path("N", "N.Pin") == "Pin"
    assert pin_rel_path("N", "N.Pin.Sub") == "Pin.Sub"


def test_pin_rel_path_node_only_returns_empty():
    assert pin_rel_path("N", "N") == ""


def test_pin_rel_path_wrong_prefix_returns_empty():
    assert pin_rel_path("N", "M.Pin") == ""


def test_type_suffix_basic():
    assert type_suffix("/Script/X.RigVMUnitNode") == "RigVMUnitNode"
    assert type_suffix(None) == "?"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/base/test_paths.py -v
```
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

`src/t3dgraph/core/base/paths.py`:

```python
"""핀 경로·클래스 경로 파싱 헬퍼 (그래프 모델 개념 — core/base 위치).

batch ③ slice α에서 core/t3d/paths.py로부터 이동. core/t3d/paths.py는
1주기 동안 re-export shim으로 유지된다.
"""
from __future__ import annotations


def node_of(full_path: str) -> str:
    """핀 경로의 노드 세그먼트. 'Node.Pin.Sub' -> 'Node'."""
    return full_path.split(".", 1)[0]


def pin_segment(full_path: str, index: int) -> str:
    """핀 경로의 index번째 점-구분 세그먼트. 범위 밖이면 ''."""
    parts = full_path.split(".")
    return parts[index] if len(parts) > index else ""


def pin_rel_path(node_name: str, full_path: str) -> str:
    """노드 이름을 prefix로 떼어낸 핀 상대 경로.

    노드 자체 경로(`node_name == full_path`)면 ''.
    prefix 불일치면 ''(드러나야 할 사실 — 호출부에서 처리).
    """
    if full_path == node_name:
        return ""
    prefix = f"{node_name}."
    if full_path.startswith(prefix):
        return full_path[len(prefix):]
    return ""


def type_suffix(class_path: str | None) -> str:
    """클래스 경로의 마지막 세그먼트. '/Script/X.Foo' -> 'Foo'. None이면 '?'."""
    return (class_path or "?").rsplit(".", 1)[-1]
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/base/test_paths.py -v
```
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/base/paths.py tests/core/base/test_paths.py
git commit -m "feat(base/paths): pin_rel_path helper + new canonical location (BL1-B1, D-B2)"
```

---

### Task 2: `core/t3d/paths.py` → re-export shim

**Files:**
- Modify: `src/t3dgraph/core/t3d/paths.py`

- [ ] **Step 1: Test — 기존 import 경로가 여전히 동작**

`tests/core/t3d/test_paths_reexport.py`(신규):

```python
def test_legacy_import_still_works():
    from t3dgraph.core.t3d.paths import node_of, pin_segment, type_suffix
    assert node_of("A.B") == "A"
    assert pin_segment("A.B.C", 1) == "B"
    assert type_suffix("/Script/X.Foo") == "Foo"


def test_legacy_and_new_are_same_symbol():
    from t3dgraph.core.t3d.paths import node_of as legacy
    from t3dgraph.core.base.paths import node_of as new
    assert legacy is new
```

- [ ] **Step 2: Run — fail**

`legacy is new` 단정이 실패할 것 (현재 별개 함수).

```
pytest tests/core/t3d/test_paths_reexport.py -v
```

- [ ] **Step 3: 변경**

`src/t3dgraph/core/t3d/paths.py` 전체를:

```python
"""DEPRECATED — core/base/paths로 이동(2026-05-21 batch ③ slice α).

batch ④에서 본 파일은 제거 예정. 신규 import는 모두 core/base/paths를 사용.
"""
from ..base.paths import (
    node_of,
    pin_segment,
    pin_rel_path,
    type_suffix,
)

__all__ = ["node_of", "pin_segment", "pin_rel_path", "type_suffix"]
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/t3d/test_paths_reexport.py -v
pytest tests/ -x        # 전체 회귀
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/t3d/paths.py tests/core/t3d/test_paths_reexport.py
git commit -m "refactor(t3d/paths): re-export shim; canonical home is core/base/paths"
```

---

### Task 3: `PinRef` 모델

**Files:**
- Create: `src/t3dgraph/core/base/pin_ref.py`
- Create: `tests/core/base/test_pin_ref.py`

- [ ] **Step 1: Failing tests**

`tests/core/base/test_pin_ref.py`:

```python
from t3dgraph.core.base.pin_ref import PinRef


def test_parse_node_dot_pin():
    p = PinRef.parse("MyNode.MyPin")
    assert p.node == "MyNode"
    assert p.pin_path == "MyPin"
    assert p.full == "MyNode.MyPin"


def test_parse_deep_path():
    p = PinRef.parse("N.V.X")
    assert p.node == "N"
    assert p.pin_path == "V.X"
    assert p.full == "N.V.X"


def test_parse_node_only():
    p = PinRef.parse("Only")
    assert p.node == "Only"
    assert p.pin_path == ""
    assert p.full == "Only"


def test_frozen_hashable():
    p = PinRef(node="N", pin_path="P")
    s = {p, PinRef(node="N", pin_path="P")}
    assert len(s) == 1     # 같은 값 dedupe
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/base/test_pin_ref.py -v
```

- [ ] **Step 3: Implement**

`src/t3dgraph/core/base/pin_ref.py`:

```python
"""PinRef — 그래프 내 핀의 안정 식별자."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PinRef:
    """핀의 전체 경로. node + 노드 내 상대 경로(점 구분).

    노드 직속이면 pin_path == "" (Link 한쪽이 노드만 가리키는 비정상 케이스 보존용).
    """
    node: str
    pin_path: str            # "Pin" 또는 "Pin.Sub.Sub2" 또는 ""

    @property
    def full(self) -> str:
        return f"{self.node}.{self.pin_path}" if self.pin_path else self.node

    @classmethod
    def parse(cls, full_path: str) -> "PinRef":
        if "." in full_path:
            node, rest = full_path.split(".", 1)
            return cls(node=node, pin_path=rest)
        return cls(node=full_path, pin_path="")
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/base/test_pin_ref.py -v
```
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/base/pin_ref.py tests/core/base/test_pin_ref.py
git commit -m "feat(base/pin_ref): PinRef stable pin identifier (D-A1 prep)"
```

---

### Task 4: `DataFlowEdge` + `analyze_data_flow` 핀 단위

**Files:**
- Modify: `src/t3dgraph/core/analysis/data_flow.py`
- Modify: `tests/core/analysis/test_data_flow.py`

- [ ] **Step 1: 기존 테스트가 새 시그니처에 깨지지 않도록 보존하는 회귀 안전망 — 먼저 새 케이스 추가**

`tests/core/analysis/test_data_flow.py`에 추가:

```python
from t3dgraph.core.analysis.data_flow import (
    analyze_data_flow, DataFlowEdge,
)
from t3dgraph.core.base.pin_ref import PinRef
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def _data_pin(name, direction):
    return Pin(name=name, cpp_type="float", direction=direction, is_execution=False)


def test_data_edges_carry_pin_refs():
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None, pins=[_data_pin("Out", "Output")]),
            Node(name="B", cls=None, pins=[_data_pin("In", "Input")]),
        ],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )
    r = analyze_data_flow(g)
    assert len(r.data_edges) == 1
    e = r.data_edges[0]
    assert isinstance(e, DataFlowEdge)
    assert e.source == PinRef(node="A", pin_path="Out")
    assert e.target == PinRef(node="B", pin_path="In")


def test_multiple_links_same_node_pair_each_preserved():
    """같은 노드 쌍, 다른 핀 — 두 엣지 모두 보존(드러나야 할 사실)."""
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[_data_pin("O1", "Output"), _data_pin("O2", "Output")]),
            Node(name="B", cls=None,
                 pins=[_data_pin("I1", "Input"), _data_pin("I2", "Input")]),
        ],
        links=[
            Link(source_path="A.O1", target_path="B.I1"),
            Link(source_path="A.O2", target_path="B.I2"),
        ],
    )
    r = analyze_data_flow(g)
    assert len(r.data_edges) == 2
    # incoming_nodes 압축본은 dedupe 된 한 항목만 ("드러나야 할 사실"은 엣지 단위로)
    assert r.incoming_nodes["B"] == ["A"]


def test_inputs_of_holds_edges_no_duplication():
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[_data_pin("O1", "Output"), _data_pin("O2", "Output")]),
            Node(name="B", cls=None,
                 pins=[_data_pin("I1", "Input"), _data_pin("I2", "Input")]),
        ],
        links=[
            Link(source_path="A.O1", target_path="B.I1"),
            Link(source_path="A.O2", target_path="B.I2"),
        ],
    )
    r = analyze_data_flow(g)
    # inputs_of는 엣지 단위 — 두 개 별도 (PRESERVE-INFO)
    assert len(r.inputs_of["B"]) == 2
    # 두 엣지 모두 DataFlowEdge 타입
    assert all(isinstance(e, DataFlowEdge) for e in r.inputs_of["B"])
    # incoming_nodes(노드 단위 호환)는 dedupe + sorted
    assert r.incoming_nodes["B"] == ["A"]


def test_sinks_and_sources_node_level_unchanged():
    """노드 단위 sinks/sources는 batch ②와 동일 의미 보존."""
    g = GraphModel(
        nodes=[
            Node(name="Src", cls=None, pins=[_data_pin("O", "Output")]),
            Node(name="Mid", cls=None,
                 pins=[_data_pin("I", "Input"), _data_pin("O", "Output")]),
            Node(name="Snk", cls=None, pins=[_data_pin("I", "Input")]),
        ],
        links=[
            Link(source_path="Src.O", target_path="Mid.I"),
            Link(source_path="Mid.O", target_path="Snk.I"),
        ],
    )
    r = analyze_data_flow(g)
    assert r.sources == ["Src"]
    assert r.sinks == ["Snk"]
```

기존 테스트도 함께 갱신 — `r.inputs_of["C"]` 같은 호출이 `list[str]`을 가정한 경우 `r.incoming_nodes["C"]`로 바꿔야 함.

기존 `test_data_edges_exclude_exec_links`·`test_inputs_outputs_indices`·`test_sinks_and_sources`·`test_isolated_nodes_in_all_nodes`·`test_handles_cycles_without_recursion_blowup` 검토 후 다음 패턴으로 변환:
- `assert ("X", "Y") in r.data_edges` → `assert any(e.source.node == "X" and e.target.node == "Y" for e in r.data_edges)`
- `sorted(r.inputs_of["C"]) == ["A", "B"]` → `sorted(r.incoming_nodes["C"]) == ["A", "B"]`
- `r.outputs_of["A"] == ["C"]` → `r.outgoing_nodes["A"] == ["C"]`

- [ ] **Step 2: Run — fail**

```
pytest tests/core/analysis/test_data_flow.py -v
```
Expected: FAIL (`DataFlowEdge` missing, `incoming_nodes` missing).

- [ ] **Step 3: Implement**

`src/t3dgraph/core/analysis/data_flow.py` 재작성:

```python
"""데이터 흐름 분석 — 핀 단위 정보 보존(PRESERVE-INFO)."""
from __future__ import annotations
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin
from ..base.pin_ref import PinRef
from ..base.paths import node_of, pin_rel_path


@dataclass(frozen=True)
class DataFlowEdge:
    source: PinRef
    target: PinRef

    @property
    def source_node(self) -> str: return self.source.node
    @property
    def target_node(self) -> str: return self.target.node


@dataclass
class DataFlowResult:
    data_edges: list[DataFlowEdge] = field(default_factory=list)
    # 엣지 단위 인덱스 — 핀 정보 보존
    inputs_of: dict[str, list[DataFlowEdge]] = field(default_factory=dict)
    outputs_of: dict[str, list[DataFlowEdge]] = field(default_factory=dict)
    # 노드 단위 호환 — 중복 제거 + 정렬
    incoming_nodes: dict[str, list[str]] = field(default_factory=dict)
    outgoing_nodes: dict[str, list[str]] = field(default_factory=dict)
    sinks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    isolated: list[str] = field(default_factory=list)
    all_nodes: list[str] = field(default_factory=list)


@dataclass
class DepNode:
    node: str
    children: list["DepNode"] = field(default_factory=list)


def _collect_exec_pin_refs(graph: GraphModel) -> set[PinRef]:
    out: set[PinRef] = set()

    def walk(node_name: str, pin: Pin, prefix: str) -> None:
        full = f"{prefix}.{pin.name}"
        rel = pin_rel_path(node_name, full)
        if pin.is_execution:
            out.add(PinRef(node=node_name, pin_path=rel))
        for sp in pin.subpins:
            walk(node_name, sp, full)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    return out


def analyze_data_flow(graph: GraphModel) -> DataFlowResult:
    exec_refs = _collect_exec_pin_refs(graph)
    edges: list[DataFlowEdge] = []

    for link in graph.links:
        src = PinRef.parse(link.source_path)
        tgt = PinRef.parse(link.target_path)
        if src in exec_refs or tgt in exec_refs:
            continue
        edges.append(DataFlowEdge(source=src, target=tgt))

    inputs_of: dict[str, list[DataFlowEdge]] = {}
    outputs_of: dict[str, list[DataFlowEdge]] = {}
    for e in edges:
        outputs_of.setdefault(e.source_node, []).append(e)
        inputs_of.setdefault(e.target_node, []).append(e)

    # 노드 단위 호환 인덱스 — set으로 dedupe 후 정렬
    incoming_nodes: dict[str, list[str]] = {
        tgt: sorted({e.source_node for e in es})
        for tgt, es in inputs_of.items()
    }
    outgoing_nodes: dict[str, list[str]] = {
        src: sorted({e.target_node for e in es})
        for src, es in outputs_of.items()
    }

    all_nodes = [n.name for n in graph.nodes]
    nodes_with_data = set(incoming_nodes) | set(outgoing_nodes)
    sources = sorted(n for n in nodes_with_data
                     if not incoming_nodes.get(n) and outgoing_nodes.get(n))
    sinks = sorted(n for n in nodes_with_data
                   if incoming_nodes.get(n) and not outgoing_nodes.get(n))
    isolated = sorted(n for n in all_nodes if n not in nodes_with_data)

    return DataFlowResult(
        data_edges=edges,
        inputs_of=inputs_of,
        outputs_of=outputs_of,
        incoming_nodes=incoming_nodes,
        outgoing_nodes=outgoing_nodes,
        sinks=sinks,
        sources=sources,
        isolated=isolated,
        all_nodes=all_nodes,
    )


def dependency_tree(
    sink: str,
    incoming_nodes: dict[str, list[str]],
    max_depth: int = 64,
) -> DepNode:
    """sink 기준 의존 트리 — 노드 단위(시각화 단순화).

    호환 — 시그니처가 `incoming_nodes` (str→list[str])로 변경됨.
    이전 `inputs_of` (str→list[DataFlowEdge])를 받는 호출부는 노드 단위로 풀어
    전달하거나, dependency_tree_edges(아래) 사용.
    """
    seen: set[str] = set()

    def build(name: str, depth: int) -> DepNode | None:
        if name in seen or depth >= max_depth:
            return None
        seen.add(name)
        node = DepNode(node=name)
        for src in incoming_nodes.get(name, []):
            child = build(src, depth + 1)
            if child is not None:
                node.children.append(child)
        return node

    return build(sink, 0) or DepNode(node=sink)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/analysis/test_data_flow.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/analysis/data_flow.py tests/core/analysis/test_data_flow.py
git commit -m "feat(data_flow): pin-level DataFlowEdge + dedup'd node-level index (D-A1, D-A3)"
```

---

### Task 5: `DataFlowPanel` 핀 라벨 + 다중 인덱싱

**Files:**
- Modify: `src/t3dgraph/core/app/data_flow_panel.py`
- Modify: `tests/core/app/test_data_flow_panel.py`

- [ ] **Step 1: Failing tests**

`tests/core/app/test_data_flow_panel.py`에 추가:

```python
from t3dgraph.core.analysis.data_flow import (
    DataFlowResult, DataFlowEdge, dependency_tree,
)
from t3dgraph.core.base.pin_ref import PinRef


def _result_fan_in():
    """A → C, B → C, C → D 형태 — C가 두 sink 트리에 안 들어가지만
    한 노드가 여러 의존 트리에 등장하는 케이스를 만들어 D-A2를 검증."""
    edges = [
        DataFlowEdge(PinRef("A", "O"), PinRef("Mid", "I1")),
        DataFlowEdge(PinRef("B", "O"), PinRef("Mid", "I2")),
        DataFlowEdge(PinRef("Mid", "O"), PinRef("S1", "I")),
        DataFlowEdge(PinRef("Mid", "O"), PinRef("S2", "I")),
    ]
    incoming_nodes = {"Mid": ["A", "B"], "S1": ["Mid"], "S2": ["Mid"]}
    outgoing_nodes = {"A": ["Mid"], "B": ["Mid"], "Mid": ["S1", "S2"]}
    return DataFlowResult(
        data_edges=edges,
        inputs_of={"Mid": edges[:2], "S1": [edges[2]], "S2": [edges[3]]},
        outputs_of={"A": [edges[0]], "B": [edges[1]], "Mid": edges[2:]},
        incoming_nodes=incoming_nodes,
        outgoing_nodes=outgoing_nodes,
        sinks=["S1", "S2"],
        sources=["A", "B"],
        isolated=[],
        all_nodes=["A", "B", "Mid", "S1", "S2"],
    )


def test_panel_pin_label_rendered(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    # Mid 노드 라벨에 어디서 들어오는지 핀 정보가 보여야 함
    labels = panel.all_labels()
    assert any("Mid" in l and ("I1" in l or "I2" in l) for l in labels)


def test_panel_indexes_all_occurrences(qapp):
    """D-A2: Mid가 S1·S2 두 트리에 등장 — 두 위치 모두 인덱싱."""
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    items_for_mid = panel.items_for("Mid")
    assert len(items_for_mid) >= 2


def test_panel_marks_subsequent_occurrences_as_back_reference(qapp):
    """두 번째 등장 행은 '[위 참조]' 표식이 라벨에 포함."""
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    items_for_mid = panel.items_for("Mid")
    # 두 번째 항목 라벨에 표식
    second_text = items_for_mid[1].text(0)
    assert "위 참조" in second_text


def test_activate_works_on_any_occurrence(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    received: list[str] = []
    panel.navigate_requested.connect(received.append)
    # 두 번째 occurrence를 활성화해도 시그널은 노드 이름으로 발사
    items_for_mid = panel.items_for("Mid")
    panel._on_activated(items_for_mid[1], 0)
    assert received == ["Mid"]


def test_panel_preserves_all_nodes(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    assert panel.shown_node_names() == {"A", "B", "Mid", "S1", "S2"}
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

`src/t3dgraph/core/app/data_flow_panel.py` 재작성:

```python
"""계산(데이터) 흐름 패널 — sink별 의존 트리 + 핀 라벨 + 다중 인덱싱."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
)
from ..analysis.data_flow import DataFlowResult, dependency_tree, DepNode, DataFlowEdge
from .navigable_panel import NavigablePanel

_NODE_ROLE = Qt.UserRole + 1
_BACK_REF_SUFFIX = "  [위 참조]"


class DataFlowPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._summary = QLabel("(그래프를 열어주세요)")
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["sink/노드 ← 의존 (핀)"])
        layout.addWidget(self._summary)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        # D-A2: 한 노드의 모든 등장 위치 — dict[node, list[item]]
        self._items: dict[str, list[QTreeWidgetItem]] = {}

    def show_result(self, r: DataFlowResult) -> None:
        self._tree.clear()
        self._items = {}
        if not r.all_nodes:
            self._summary.setText("(노드 없음)")
            return
        self._summary.setText(
            f"sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")

        for sink in r.sinks:
            tree = dependency_tree(sink, r.incoming_nodes)
            self._add_tree(tree, self._tree.invisibleRootItem(),
                           inbound=r.inputs_of)

        shown = set(self._items.keys())
        unshown = [n for n in r.all_nodes if n not in shown]
        if unshown:
            group = QTreeWidgetItem(["고립/미연결"])
            self._tree.addTopLevelItem(group)
            for name in unshown:
                child = QTreeWidgetItem([name])
                child.setData(0, _NODE_ROLE, name)
                group.addChild(child)
                self._items.setdefault(name, []).append(child)

    def _add_tree(self, dep: DepNode, parent: QTreeWidgetItem,
                  *, inbound: dict[str, list[DataFlowEdge]]) -> QTreeWidgetItem:
        is_back_ref = dep.node in self._items     # 두 번째 이상 등장 — D-A2
        label = self._label_for(dep.node, inbound)
        if is_back_ref:
            label = label + _BACK_REF_SUFFIX
        item = QTreeWidgetItem([label])
        item.setData(0, _NODE_ROLE, dep.node)
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)
        self._items.setdefault(dep.node, []).append(item)
        if not is_back_ref:
            for c in dep.children:
                self._add_tree(c, item, inbound=inbound)
        return item

    @staticmethod
    def _label_for(node: str, inbound: dict[str, list[DataFlowEdge]]) -> str:
        edges = inbound.get(node, [])
        if not edges:
            return node
        # 들어오는 핀 라벨을 같이 — "Node ← A.O1, B.O" 형태
        srcs = ", ".join(f"{e.source_node}.{e.source.pin_path}" for e in edges
                         if e.source.pin_path)
        return f"{node} ← {srcs}" if srcs else node

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        name = item.data(0, _NODE_ROLE)
        if name:
            self.navigate_requested.emit(name)

    def activate_node(self, name: str) -> None:
        items = self._items.get(name)
        if items:
            self._on_activated(items[0], 0)

    def items_for(self, name: str) -> list[QTreeWidgetItem]:
        return list(self._items.get(name, []))

    def all_labels(self) -> list[str]:
        out: list[str] = []
        for items in self._items.values():
            out.extend(it.text(0) for it in items)
        return out

    def top_level_labels(self) -> list[str]:
        out: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            out.append(self._tree.topLevelItem(i).text(0))
        return out

    def shown_node_names(self) -> set[str]:
        return set(self._items.keys())

    def highlight_node(self, node: str | None) -> None:
        items = self._items.get(node) if node else None
        if items:
            self._tree.setCurrentItem(items[0])
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
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/data_flow_panel.py tests/core/app/test_data_flow_panel.py
git commit -m "feat(data_flow_panel): pin labels + multi-indexing (D-A2)"
```

---

### Task 6: `show_data_flow` 타입힌트

**Files:**
- Modify: `src/t3dgraph/core/app/contracts.py`
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 변경**

`contracts.py`에 `show_data_flow` 추상 메서드 있으면 시그니처:

```python
from ..analysis.data_flow import DataFlowResult

class AbstractGraphView(ABC):
    ...
    def show_data_flow(self, result: DataFlowResult) -> None: ...
```

`main_window.py`:

```python
def show_data_flow(self, result: DataFlowResult) -> None:
    self.data_flow_panel.show_result(result)
```

또한 `controller.py`의 `analyze_data_flow` 호출 시그니처 확인.

- [ ] **Step 2: Run 전체 회귀**

```
pytest tests/ -x
```
Expected: PASS.

- [ ] **Step 3: Commit**

```
git add src/t3dgraph/core/app/contracts.py src/t3dgraph/core/app/main_window.py
git commit -m "refactor(contracts): type-hint show_data_flow(DataFlowResult) (D-B1)"
```

---

### Task 7: 기존 import 갱신 — `core/t3d/paths` → `core/base/paths`

**Files:**
- Modify: 모든 `from t3dgraph.core.t3d.paths import …` 사용처 — `from t3dgraph.core.base.paths import` 로 일괄 변경

- [ ] **Step 1: grep으로 사용처 식별**

```
grep -rln "from t3dgraph.core.t3d.paths" src tests
grep -rln "from \.\..*t3d\.paths" src tests
grep -rln "from \.\.t3d\.paths" src tests
```

- [ ] **Step 2: 일괄 치환**

각 파일에서 `t3d.paths` → `base.paths` (테스트 파일의 re-export 검증 테스트는 *유지*).

- [ ] **Step 3: Run — pass**

```
pytest tests/ -x
```
Expected: PASS.

- [ ] **Step 4: Commit**

```
git add -A
git commit -m "refactor: migrate imports from core/t3d/paths to core/base/paths (BL1-B1)"
```

---

### Task 8: 회귀 + Orion smoke

**Files:**
- Run: `pytest tests/ -v`

- [ ] **Step 1: 전체 회귀**

```
pytest tests/ -v
```
Expected: PASS.

- [ ] **Step 2: smoke — Orion에서 핀 정보가 보존되는지**

`tests/smoke_pin_level_dataflow.py`(신규):

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

# PRESERVE-INFO — 모든 엣지가 핀 정보 가짐
edges_with_pin_info = sum(1 for e in r.data_edges
                          if e.source.pin_path and e.target.pin_path)
print(f"data edges {len(r.data_edges)} · pin info 포함 {edges_with_pin_info}")
assert edges_with_pin_info == len(r.data_edges), \
    "모든 데이터 엣지는 핀 정보를 가져야 함"
print(f"sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")
```

- [ ] **Step 3: Commit (smoke)**

```
git add tests/smoke_pin_level_dataflow.py
git commit -m "test: smoke for pin-level data edges on Orion (PRESERVE-INFO)"
```

---

## 완료 정의

- [ ] Task 1-8 PASS
- [ ] `DataFlowResult.data_edges`가 `list[DataFlowEdge]` — 모든 엣지가 `PinRef` 양끝
- [ ] `incoming_nodes/outgoing_nodes`가 dedupe + sorted; 기존 노드 단위 호출부는 이를 사용
- [ ] `core/base/paths.py`가 정규 위치; `core/t3d/paths.py`는 re-export shim
- [ ] DataFlowPanel이 같은 노드 다중 등장 시 모두 인덱싱 + "[위 참조]" 표식
- [ ] 노드 보존 + 핀 정보 보존 두 불변식 통과
