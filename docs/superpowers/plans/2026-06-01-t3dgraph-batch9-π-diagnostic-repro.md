# batch ⑨ π (pi) — 진단 인프라 + 재현 테스트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `GraphModel.diagnostics: InterpreterDiagnostics`를 도입해 인터프리터가 추출/누락 결정을 모두 기록하게 만들고, `tests/repro/`에 F14·F17·F20 재현 테스트를 박는다. ρ·σ 슬라이스가 이 데이터·테스트 위에서 fix를 진행한다.

**Architecture:** `InterpreterDiagnostics`는 dataclass로 `GraphModel`에 attached. 인터프리터가 한 번의 `interpret()` 동안 모든 객체에 대해 추출/누락 결정을 누적. `tests/repro/` 디렉터리는 Orion 샘플 의존이라 환경 변수(`T3DGRAPH_ORION_SAMPLE`)로 경로 주입, 미설정 시 skip.

**Tech Stack:** Python 3.11, pytest, pytest-qt(F14 재현 한정), 신규 외부 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` §4·§5·§6

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/base/graph_model.py` | 수정 (`DroppedObject`·`InterpreterDiagnostics` dataclass + `GraphModel.diagnostics` 필드) |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (진단 객체 생성·전파·누적) |
| `tests/repro/__init__.py` | 신규 (패키지 마커) |
| `tests/repro/conftest.py` | 신규 (`orion_sample` fixture + skip 가드) |
| `tests/repro/test_f20_node_preservation.py` | 신규 |
| `tests/repro/test_f14_connected_only_dot_count.py` | 신규 |
| `tests/repro/test_f17_array_order.py` | 신규 |
| `tests/base/test_interpreter_diagnostics.py` | 신규 (단위 테스트 — Orion 의존 없음) |

---

## Task 1: `InterpreterDiagnostics` 자료구조 — TDD

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`
- Create: `tests/base/test_interpreter_diagnostics.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/base/test_interpreter_diagnostics.py`:

```python
"""DroppedObject·InterpreterDiagnostics 자료구조 단위."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import (
    DroppedObject, InterpreterDiagnostics, GraphModel,
)


def test_dropped_object_fields() -> None:
    d = DroppedObject(name="N1", cls="/Script/X.Foo",
                      reason="unknown class", parent_obj=None)
    assert d.name == "N1"
    assert d.cls == "/Script/X.Foo"
    assert d.reason == "unknown class"
    assert d.parent_obj is None


def test_diagnostics_defaults_empty() -> None:
    diag = InterpreterDiagnostics()
    assert diag.objects_dropped == []
    assert diag.extracted_per_class == {}
    assert diag.max_depth_seen == 0
    assert diag.contained_graph_count == 0
    assert diag.external_refs_unresolved == []


def test_graph_model_diagnostics_default_none() -> None:
    g = GraphModel()
    assert g.diagnostics is None


def test_graph_model_diagnostics_attach() -> None:
    g = GraphModel()
    diag = InterpreterDiagnostics()
    diag.objects_dropped.append(DroppedObject("N1", "X", "unknown", None))
    diag.extracted_per_class["RigVMUnitNode"] = 5
    g.diagnostics = diag
    assert g.diagnostics is not None
    assert g.diagnostics.extracted_per_class["RigVMUnitNode"] == 5
    assert len(g.diagnostics.objects_dropped) == 1
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_interpreter_diagnostics.py -v`
Expected: FAIL — `ImportError: cannot import name 'DroppedObject'`.

- [ ] **Step 3: `graph_model.py` 확장**

`src/t3dgraph/core/base/graph_model.py` 상단(`Pin` dataclass 위)에 추가:

```python
@dataclass
class DroppedObject:
    """인터프리터가 처리하지 못해 그래프에 들어가지 못한 객체."""
    name: str
    cls: str | None
    reason: str            # "unknown class" | "depth cap" | "graph at top" | "no resolver"
    parent_obj: str | None # 부모 객체명 (재귀 손실 추적). top-level이면 None


@dataclass
class InterpreterDiagnostics:
    """인터프리터 한 사이클의 정량 진단."""
    objects_dropped: list[DroppedObject] = field(default_factory=list)
    extracted_per_class: dict[str, int] = field(default_factory=dict)
    max_depth_seen: int = 0
    contained_graph_count: int = 0
    external_refs_unresolved: list[str] = field(default_factory=list)
```

`GraphModel` 데이터클래스 필드 추가 (`warnings` 다음 줄에):

```python
diagnostics: InterpreterDiagnostics | None = None
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/base/test_interpreter_diagnostics.py -v`
Expected: 4 passed

- [ ] **Step 5: 회귀 확인**

Run: `pytest tests -v`
Expected: 기존 테스트 전부 통과 (`diagnostics` 디폴트 None, 호출부 영향 0).

- [ ] **Step 6: 커밋**

```bash
git add tests/base/test_interpreter_diagnostics.py src/t3dgraph/core/base/graph_model.py
git commit -m "feat(base): InterpreterDiagnostics + DroppedObject + GraphModel.diagnostics (F20 prep)"
```

---

## Task 2: 인터프리터 진단 객체 생성·전파

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`

- [ ] **Step 1: 단위 테스트 추가 — 진단 객체 항상 attach**

`tests/base/test_interpreter_diagnostics.py` 추가:

```python
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_interpret_always_attaches_diagnostics() -> None:
    doc = T3DDocument(objects=[])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    assert isinstance(g.diagnostics.extracted_per_class, dict)
    assert g.diagnostics.max_depth_seen == 0


def test_unknown_class_recorded_as_dropped() -> None:
    obj = T3DObject(cls="/Script/X.Foo", name="N1", properties={}, children=[])
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    dropped_classes = [d.cls for d in g.diagnostics.objects_dropped]
    # _add_generic는 노드를 생성하지만 진단에도 "unknown class"로 기록
    assert "/Script/X.Foo" in dropped_classes
    reasons = [d.reason for d in g.diagnostics.objects_dropped]
    assert "unknown class" in reasons


def test_extracted_per_class_counts_node_suffixes() -> None:
    # RigVMUnitNode 두 개
    u1 = T3DObject(cls="/Script/RigVMDeveloper.RigVMUnitNode", name="U1",
                   properties={}, children=[])
    u2 = T3DObject(cls="/Script/RigVMDeveloper.RigVMUnitNode", name="U2",
                   properties={}, children=[])
    doc = T3DDocument(objects=[u1, u2])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    assert g.diagnostics.extracted_per_class.get("RigVMUnitNode") == 2
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_interpreter_diagnostics.py -v`
Expected: FAIL — 새 테스트 3개 실패 (`g.diagnostics is None`).

- [ ] **Step 3: 인터프리터 시그니처 + 진단 전파**

`src/t3dgraph/plugins/rigvm/interpreter.py` 상단 import 갱신:

```python
from ...core.base.graph_model import (
    GraphModel, Node, Pin, Link, VariableRef,
    InterpreterDiagnostics, DroppedObject,
)
```

`interpret()` 메서드를 다음으로 교체:

```python
def interpret(self, doc: T3DDocument) -> GraphModel:
    diag = InterpreterDiagnostics()
    g = self._interpret_objects(
        doc.objects, label=None, parent_node=None, diagnostics=diag)
    g.diagnostics = diag
    return g
```

`_interpret_objects` 시그니처에 `diagnostics: InterpreterDiagnostics` 인자 추가, 본문 내부 분기 모두 진단 갱신:

```python
def _interpret_objects(
    self,
    objects: list[T3DObject],
    *,
    label: str | None,
    parent_node: str | None,
    diagnostics: InterpreterDiagnostics,
    depth: int = 0,
    max_depth: int = 64,
) -> GraphModel:
    g = GraphModel(label=label, parent_node=parent_node)
    diagnostics.max_depth_seen = max(diagnostics.max_depth_seen, depth)
    if depth >= max_depth:
        g.warnings.append(
            f"interpret 깊이 {depth} >= {max_depth} — 추가 추출 중단 (label={label or '?'})"
        )
        for obj in objects:
            diagnostics.objects_dropped.append(DroppedObject(
                name=obj.name or "?", cls=obj.cls,
                reason="depth cap", parent_obj=parent_node))
        return g
    for obj in objects:
        if t.is_link_class(obj.cls):
            self._add_link(obj, g)
        elif t.is_node_class(obj.cls):
            self._add_node(obj, g, diagnostics=diagnostics,
                           depth=depth, max_depth=max_depth)
        elif obj.cls is None:
            continue
        elif t.is_graph_class(obj.cls):
            g.warnings.append(
                f"최상위에 RigVMGraph 객체 '{obj.name or '?'}' 발견 — "
                f"자식 {len(obj.children)}개가 추출되지 않음"
            )
            diagnostics.objects_dropped.append(DroppedObject(
                name=obj.name or "?", cls=obj.cls,
                reason="graph at top", parent_obj=parent_node))
            continue
        else:
            diagnostics.objects_dropped.append(DroppedObject(
                name=obj.name or "?", cls=obj.cls,
                reason="unknown class", parent_obj=parent_node))
            self._add_generic(obj, g)
    known = {n.name for n in g.nodes}
    for link in g.links:
        for path in (link.source_path, link.target_path):
            node = node_of(path)
            if node not in known and path not in g.external_refs:
                g.external_refs.append(path)
    return g
```

`_add_node` 시그니처에 `diagnostics` 인자 추가 + extracted_per_class 카운트 + ContainedGraph 카운트 + 재귀 호출 시 전파:

```python
def _add_node(self, obj: T3DObject, g: GraphModel, *,
              diagnostics: InterpreterDiagnostics,
              depth: int = 0, max_depth: int = 64) -> None:
    summary, category = role_for(obj)
    node = Node(
        name=obj.name or "",
        cls=obj.cls,
        pins=[_build_pin(c) for c in obj.children
              if t.is_pin_class(c.cls) or c.cls is None],
        position=_position(obj),
        raw=dict(obj.properties),
        kind=_classify_kind(obj),
        display_name=display_name_for(obj),
        role_summary=summary,
        role_category=category,
    )
    graph_children = [c for c in obj.children if t.is_graph_class(c.cls)]
    diagnostics.contained_graph_count += len(graph_children)
    for i, child in enumerate(graph_children):
        sub = self._interpret_objects(
            child.children,
            label=f"{node.name}/{child.name or 'graph'}",
            parent_node=node.name,
            diagnostics=diagnostics,
            depth=depth + 1,
            max_depth=max_depth,
        )
        g.warnings.extend(w for w in sub.warnings if "깊이" in w)
        if i == 0:
            node.subgraph = sub
        else:
            node.extra_subgraphs.append(sub)
    if len(graph_children) > 1:
        g.warnings.append(
            f"노드 '{node.name}'에 RigVMGraph 자식 {len(graph_children)}개 — "
            f"첫 개는 subgraph, 나머지 {len(graph_children) - 1}개는 extra_subgraphs"
        )
    g.nodes.append(node)
    suffix = (obj.cls or "").rsplit(".", 1)[-1]
    diagnostics.extracted_per_class[suffix] = (
        diagnostics.extracted_per_class.get(suffix, 0) + 1
    )
    if obj.cls and obj.cls.rsplit(".", 1)[-1] == "RigVMVariableNode":
        self._add_variable_ref(node, g)
```

`_add_generic` 변경 없음 (이미 warning 발생, 진단은 호출부에서 처리).

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/base/test_interpreter_diagnostics.py -v`
Expected: 7 passed

- [ ] **Step 5: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과. 인터프리터 시그니처 외부에서는 무변경 — `_interpret_objects`/`_add_node`는 외부 미공개라 호출부 영향 없음. `interpret()`만 노출되며 시그니처 동일.

- [ ] **Step 6: 커밋**

```bash
git add src/t3dgraph/plugins/rigvm/interpreter.py tests/base/test_interpreter_diagnostics.py
git commit -m "feat(rigvm): InterpreterDiagnostics propagation in interpret() (F20 prep)"
```

---

## Task 3: `tests/repro/` 패키지 + conftest

**Files:**
- Create: `tests/repro/__init__.py`
- Create: `tests/repro/conftest.py`

- [ ] **Step 1: 패키지 마커**

`tests/repro/__init__.py`:

```python
"""F14·F17·F20 재현 테스트 — Orion 샘플 의존."""
```

- [ ] **Step 2: conftest.py 작성**

`tests/repro/conftest.py`:

```python
"""tests/repro fixtures — Orion 샘플 경로 주입·skip 가드."""
from __future__ import annotations
import os
from pathlib import Path

import pytest

from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.tokenizer import tokenize
from t3dgraph.core.t3d.objects import parse_t3d


# Orion 샘플 경로는 환경변수 T3DGRAPH_ORION_SAMPLE 또는 기본 위치.
# 미설정·미존재 시 본 디렉터리 모든 테스트 skip.
def _orion_path() -> Path | None:
    env = os.environ.get("T3DGRAPH_ORION_SAMPLE")
    if env:
        p = Path(env)
        return p if p.exists() else None
    # 기본: 레포 루트의 Orion_WorkStation_Rig_Analysis/.../sample.t3d.txt
    repo_root = Path(__file__).resolve().parents[2]
    candidates = list((repo_root / "Orion_WorkStation_Rig_Analysis").rglob("*.t3d.txt"))
    return candidates[0] if candidates else None


@pytest.fixture(scope="session")
def orion_sample_path() -> Path:
    p = _orion_path()
    if p is None:
        pytest.skip("Orion 샘플 미발견 (T3DGRAPH_ORION_SAMPLE 환경변수 또는 "
                    "Orion_WorkStation_Rig_Analysis/ 디렉터리 필요)")
    return p


@pytest.fixture(scope="session")
def orion_doc(orion_sample_path: Path) -> T3DDocument:
    text = orion_sample_path.read_text(encoding="utf-8", errors="replace")
    tokens = tokenize(text)
    return parse_t3d(tokens)
```

- [ ] **Step 3: 실행 — fixture 동작 확인**

`tests/repro/test_smoke.py`를 임시로 만들어 fixture 동작 확인:

```python
def test_orion_fixture_loads(orion_doc) -> None:
    assert orion_doc is not None
    assert len(orion_doc.objects) > 0
```

Run: `pytest tests/repro -v`
Expected: PASS (Orion 샘플이 레포에 있으면) 또는 SKIP (없으면). 둘 다 OK — fixture 동작 검증.

- [ ] **Step 4: smoke 테스트 제거**

```bash
rm tests/repro/test_smoke.py
```

(스모크는 영구 fixture 추가하지 않음 — 다음 task의 실제 repro 테스트가 fixture 사용.)

- [ ] **Step 5: 커밋**

```bash
git add tests/repro/__init__.py tests/repro/conftest.py
git commit -m "test(repro): tests/repro package + orion_sample fixture"
```

---

## Task 4: F20 재현 — 노드 보존 어서션

**Files:**
- Create: `tests/repro/test_f20_node_preservation.py`

- [ ] **Step 1: 테스트 작성**

`tests/repro/test_f20_node_preservation.py`:

```python
"""F20 재현 — 인터프리터가 모든 노드 후보를 추출 또는 dropped로 기록.

ρ 슬라이스가 본 파일의 어서션을 통과시켜야 한다.
"""
from __future__ import annotations

import pytest

from t3dgraph.core.base.graph_model import GraphModel
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


_NODE_EXCLUDED_SUFFIXES = ("RigVMPin", "RigVMLink", "RigVMGraph")


def _count_node_candidates(objects: list[T3DObject]) -> int:
    """T3D 객체 트리(중첩 포함)에서 노드 후보 수."""
    n = 0
    for o in objects:
        cls = o.cls or ""
        if cls.startswith("/Script/RigVM") and not any(
                cls.endswith(s) for s in _NODE_EXCLUDED_SUFFIXES):
            n += 1
        n += _count_node_candidates(o.children)
    return n


def _count_extracted_nodes(g: GraphModel) -> int:
    """GraphModel 트리(subgraph·extra_subgraphs 포함)에서 추출된 노드 수."""
    total = len(g.nodes)
    for node in g.nodes:
        if node.subgraph is not None:
            total += _count_extracted_nodes(node.subgraph)
        for extra in node.extra_subgraphs:
            total += _count_extracted_nodes(extra)
    return total


def test_orion_sample_node_preservation(orion_doc: T3DDocument) -> None:
    """모든 노드 후보가 추출 또는 dropped 목록에 들어간다 — 잠적 0."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    expected = _count_node_candidates(orion_doc.objects)
    extracted = _count_extracted_nodes(graph)
    dropped = len(graph.diagnostics.objects_dropped)
    assert extracted + dropped >= expected, (
        f"노드 잠적: expected={expected}, extracted={extracted}, dropped={dropped}, "
        f"dropped_classes={ {d.cls for d in graph.diagnostics.objects_dropped} }"
    )


def test_extracted_per_class_snapshot(orion_doc: T3DDocument) -> None:
    """핵심 클래스는 0이 아니어야 함 — extractor 동작 sanity."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    # Orion 샘플엔 RigVMUnitNode·RigVMDispatchNode가 반드시 있다고 가정.
    # 실제 분포는 π 머지 후 데이터로 ρ 슬라이스가 본 스냅숏을 갱신한다.
    units = graph.diagnostics.extracted_per_class.get("RigVMUnitNode", 0)
    dispatch = graph.diagnostics.extracted_per_class.get("RigVMDispatchNode", 0)
    assert units + dispatch > 0, (
        f"노드 추출 0 — extractor 동작 의심. 분포: "
        f"{graph.diagnostics.extracted_per_class}"
    )


@pytest.mark.xfail(reason="π는 unknown class drop 허용 — ρ 머지 시 제거")
def test_no_unknown_classes_after_fix(orion_doc: T3DDocument) -> None:
    """ρ 머지 충족 조건 — unknown class dropped 0."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    unknown = [d for d in graph.diagnostics.objects_dropped
               if d.reason == "unknown class"]
    assert unknown == [], (
        f"미알 클래스 {len(unknown)}개 — NODE_CLASS_SUFFIXES 확장 필요: "
        f"{ {d.cls for d in unknown} }"
    )


@pytest.mark.xfail(reason="π는 external_ref 미해결 허용 — ρ 머지 시 제거")
def test_no_unresolved_external_refs_after_fix(orion_doc: T3DDocument) -> None:
    """ρ 머지 충족 조건 — AssetResolver가 모든 external_ref 해결."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    assert graph.diagnostics.external_refs_unresolved == [], (
        f"미해결 external_refs: {graph.diagnostics.external_refs_unresolved}"
    )
```

- [ ] **Step 2: 실행 — 어서션 통과·xfail 확인**

Run: `pytest tests/repro/test_f20_node_preservation.py -v`

Expected (Orion 샘플 있을 때):
- `test_orion_sample_node_preservation` — PASS (모든 객체가 extracted 또는 dropped). 만약 FAIL이면 인터프리터 진단 갱신 누락 — Task 2 재검토.
- `test_extracted_per_class_snapshot` — PASS
- `test_no_unknown_classes_after_fix` — XFAIL (예상). ρ 머지 시 XPASS → @pytest.mark.xfail 제거.
- `test_no_unresolved_external_refs_after_fix` — XFAIL.

Expected (Orion 샘플 없을 때): SKIP (전체).

- [ ] **Step 3: 데이터 수집 — π 머지 전 dropped 분포 출력 (수동)**

ρ 슬라이스 plan 작성에 쓸 데이터 수집. 다음 명령으로 dropped class 분포를 화면에 출력:

```bash
T3DGRAPH_ORION_SAMPLE=Orion_WorkStation_Rig_Analysis/<sample>.t3d.txt \
  uv run python -c "
from pathlib import Path
import os
from t3dgraph.core.t3d.tokenizer import tokenize
from t3dgraph.core.t3d.objects import parse_t3d
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter

p = Path(os.environ['T3DGRAPH_ORION_SAMPLE'])
doc = parse_t3d(tokenize(p.read_text(encoding='utf-8', errors='replace')))
g = RigVMGraphInterpreter().interpret(doc)
print('=== extracted_per_class ===')
for k, v in sorted(g.diagnostics.extracted_per_class.items()):
    print(f'  {k}: {v}')
print('=== dropped (top 10 by class) ===')
from collections import Counter
c = Counter(d.cls for d in g.diagnostics.objects_dropped)
for cls, n in c.most_common(10):
    print(f'  {cls}: {n}')
print('=== external_refs_unresolved (top 10) ===')
for r in g.diagnostics.external_refs_unresolved[:10]:
    print(f'  {r}')
print(f'max_depth_seen: {g.diagnostics.max_depth_seen}')
print(f'contained_graph_count: {g.diagnostics.contained_graph_count}')
"
```

출력을 ρ 슬라이스 plan 작성 시 인용. 본 task 완료 조건엔 수동 검증 — 출력이 보이면 OK.

- [ ] **Step 4: 커밋**

```bash
git add tests/repro/test_f20_node_preservation.py
git commit -m "test(repro): F20 node preservation reproducer + ρ-gating xfails"
```

---

## Task 5: F14 재현 — 연결된 핀만 토글 시 dot 증가 없음

**Files:**
- Create: `tests/repro/test_f14_connected_only_dot_count.py`

- [ ] **Step 1: 테스트 작성**

`tests/repro/test_f14_connected_only_dot_count.py`:

```python
"""F14 재현 — connected_only 토글 시 dot 개수 증가 금지.

σ 슬라이스가 본 어서션을 통과시켜야 한다.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QGraphicsEllipseItem

from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.view_state import ViewState
from t3dgraph.core.app.pin_colors import PinColorTable
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _count_dots(node_item) -> int:
    """NodeItem 자식 중 QGraphicsEllipseItem(핀 dot) 개수."""
    return sum(
        1 for c in node_item.childItems() if isinstance(c, QGraphicsEllipseItem)
    )


def _total_dots(scene: GraphScene) -> int:
    return sum(_count_dots(n) for n in scene._nodes.values())


@pytest.fixture
def pin_colors(tmp_path, monkeypatch) -> PinColorTable:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    return PinColorTable.load()


def test_connected_only_toggle_does_not_double_dots(
        qtbot, orion_doc: T3DDocument, pin_colors: PinColorTable) -> None:
    """connected_only 토글 후 dot 개수가 증가하지 않는다."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    # 너무 큰 그래프면 첫 루트의 첫 서브그래프(또는 그래프 자체) 1개만 검사
    scene = GraphScene()
    vs = ViewState()
    scene.populate(graph, view_state=vs, pin_colors=pin_colors)
    dots_off = _total_dots(scene)
    assert dots_off > 0  # extractor sanity

    vs.connected_pins_only = True
    scene.populate(graph, view_state=vs, pin_colors=pin_colors)
    dots_on = _total_dots(scene)

    assert dots_on <= dots_off, (
        f"F14 회귀: connected_only=True에서 dot 증가 — off={dots_off}, on={dots_on}"
    )


def test_connected_only_reduces_or_keeps_dots(
        qtbot, orion_doc: T3DDocument, pin_colors: PinColorTable) -> None:
    """추가 보강 — 연결된 핀이 전체보다 적거나 같다는 단조성."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    scene = GraphScene()
    vs_off = ViewState()
    vs_on = ViewState()
    vs_on.connected_pins_only = True
    scene.populate(graph, view_state=vs_off, pin_colors=pin_colors)
    off = _total_dots(scene)
    scene.populate(graph, view_state=vs_on, pin_colors=pin_colors)
    on = _total_dots(scene)
    assert on <= off, f"단조성 위배: off={off}, on={on}"
```

- [ ] **Step 2: 실행 — 현재 상태 확인**

Run: `pytest tests/repro/test_f14_connected_only_dot_count.py -v`

Expected: FAIL (F14가 실제로 회귀 중이라면) 또는 PASS (오해였다면).

본 시점에서 FAIL이 되어야 σ 슬라이스의 fix 대상이 명확해진다. PASS면 F14가 정적 분석상 보이지 않은 다른 곳에 있다는 신호 — σ 진입 시 재현 시나리오 갱신.

- [ ] **Step 3: 커밋 (PASS/FAIL 무관)**

```bash
git add tests/repro/test_f14_connected_only_dot_count.py
git commit -m "test(repro): F14 connected_only dot count monotonicity"
```

---

## Task 6: F17 재현 — 배열 subpin 순서

**Files:**
- Create: `tests/repro/test_f17_array_order.py`

- [ ] **Step 1: 테스트 작성 — 합성 T3D 기반**

`tests/repro/test_f17_array_order.py`:

```python
"""F17 재현 — 배열 subpin 순서가 T3D 원본 객체 순서와 일치.

σ 슬라이스가 본 어서션을 통과시켜야 한다.
"""
from __future__ import annotations

from t3dgraph.core.t3d.tokenizer import tokenize
from t3dgraph.core.t3d.objects import parse_t3d
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _build_array_doc_text(item_names: list[str]) -> str:
    """RigVMPin 배열을 자식으로 가진 노드 1개짜리 T3D 텍스트 생성."""
    items_block = "\n".join(
        f'Begin Object Name="{name}" Class=/Script/RigVMDeveloper.RigVMPin\nEnd Object'
        for name in item_names
    )
    return f"""Begin Object Name="N1" Class=/Script/RigVMDeveloper.RigVMUnitNode
   Begin Object Name="Items" Class=/Script/RigVMDeveloper.RigVMPin
{items_block}
   End Object
End Object
"""


def test_array_subpin_order_preserved_synth() -> None:
    """합성 T3D — subpin 순서 == 원본 순서."""
    names = ["0", "1", "2", "3"]
    text = _build_array_doc_text(names)
    doc = parse_t3d(tokenize(text))
    graph = RigVMGraphInterpreter().interpret(doc)
    assert len(graph.nodes) == 1
    items_pin = next(p for p in graph.nodes[0].pins if p.name == "Items")
    actual = [sp.name for sp in items_pin.subpins]
    assert actual == names, (
        f"배열 subpin 순서 역전 — expected={names}, actual={actual}"
    )


def test_array_subpin_order_preserved_orion(orion_doc) -> None:
    """Orion 샘플 — 배열 핀이 있는 경우 모두 단조 검사.

    각 노드의 각 핀에서, subpin name이 숫자로만 구성된 배열형 핀이라면
    int(name) 순서로 정렬되어 있어야 한다. T3D는 0, 1, 2... 순서로 작성.
    """
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    violations: list[tuple[str, str, list[str]]] = []

    def walk(g) -> None:
        for node in g.nodes:
            for pin in node.pins:
                _check_pin(node.name, pin)
            if node.subgraph is not None:
                walk(node.subgraph)
            for extra in node.extra_subgraphs:
                walk(extra)

    def _check_pin(node_name: str, pin) -> None:
        names = [sp.name for sp in pin.subpins]
        # 모든 sub 이름이 digit이면 배열형
        if names and all(n.isdigit() for n in names):
            indices = [int(n) for n in names]
            if indices != sorted(indices):
                violations.append((node_name, pin.name, names))
        for sp in pin.subpins:
            _check_pin(node_name, sp)

    walk(graph)
    assert not violations, (
        f"F17 회귀 — 배열 subpin 순서 역전 {len(violations)}건 "
        f"(첫 5건): {violations[:5]}"
    )
```

- [ ] **Step 2: 실행**

Run: `pytest tests/repro/test_f17_array_order.py -v`

Expected:
- `test_array_subpin_order_preserved_synth` — 합성 케이스는 PASS (파서는 순서 보존)
- `test_array_subpin_order_preserved_orion` — FAIL이 예상 (사용자 보고). PASS면 reverse가 시각 레이어 어딘가에 있어 모델 단계엔 안 보임.

- [ ] **Step 3: 커밋**

```bash
git add tests/repro/test_f17_array_order.py
git commit -m "test(repro): F17 array subpin order — synth + Orion monotonicity"
```

---

## Task 7: 회귀 풀스위트 + 데이터 수집 출력

**Files:** (변경 없음 — 검증 단계)

- [ ] **Step 1: 풀스위트 실행**

Run: `pytest tests -v`

Expected:
- 기존 테스트 전부 통과
- `tests/base/test_interpreter_diagnostics.py` — 통과
- `tests/repro/test_f14_*` — PASS 또는 FAIL (회귀 여부 데이터)
- `tests/repro/test_f17_*` — synth PASS, Orion 케이스 PASS 또는 FAIL
- `tests/repro/test_f20_*` — preservation/snapshot PASS, xfail 2건은 XFAIL

- [ ] **Step 2: ρ 슬라이스를 위한 데이터 출력 (수동)**

Task 4 Step 3의 명령을 다시 실행해 dropped 분포·external_refs·max_depth를 수집. 출력을 PR description에 첨부 — ρ plan 작성자가 참조한다.

- [ ] **Step 3: 머지·후속 트리거**

PR 머지 후:
- improver 자동 리뷰 사이클 진입
- ρ 슬라이스 plan 작성 트리거 (`docs/superpowers/plans/2026-XX-XX-t3dgraph-batch9-ρ-f20-fix.md`) — Task 4 데이터 기반
- σ 슬라이스 plan 작성 트리거 (`docs/superpowers/plans/2026-XX-XX-t3dgraph-batch9-σ-f14-f17-fix.md`) — Task 5·6 결과 기반

---

## Self-Review 체크리스트

- Spec §4.2 `DroppedObject`·`InterpreterDiagnostics` — Task 1 ✅
- Spec §4.2 `GraphModel.diagnostics` 필드 — Task 1 ✅
- Spec §4.3 인터프리터 항상 진단 attach — Task 2 (`test_interpret_always_attaches_diagnostics`) ✅
- Spec §4.3 unknown class 기록 — Task 2 (`test_unknown_class_recorded_as_dropped`) ✅
- Spec §4.3 extracted_per_class 카운트 — Task 2 (`test_extracted_per_class_counts_node_suffixes`) ✅
- Spec §4.3 ContainedGraph 카운트 — Task 2 (`_add_node`에서 `diagnostics.contained_graph_count += len(graph_children)`) ✅
- Spec §4.5 노드 후보 카운트 헬퍼 — Task 4 `_count_node_candidates` ✅
- Spec §4.5 추출 노드 재귀 카운트 — Task 4 `_count_extracted_nodes` ✅
- Spec §4.5 ρ-gating xfail — Task 4 `test_no_unknown_classes_after_fix`·`test_no_unresolved_external_refs_after_fix` ✅
- Spec §5.2 F17 재현 — Task 6 (synth + Orion) ✅
- Spec §6.2 F14 재현 — Task 5 ✅
- PRESERVE-ALL 정량 가드 — Task 4 `test_orion_sample_node_preservation` ✅

---

## 완료 후

머지 후:
- improver 자동 리뷰 → backlog
- ρ 슬라이스 plan 작성 (π 데이터 인용)
- σ 슬라이스 plan 작성 (Task 5·6 PASS/FAIL 결과 인용)
- τ·φ는 본 슬라이스와 독립 — 병렬 진행 중
