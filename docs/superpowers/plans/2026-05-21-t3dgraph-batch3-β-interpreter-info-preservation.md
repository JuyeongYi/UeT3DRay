# Slice β: 인터프리터 정보 보존 (C-A1 + C-A2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RigVMGraphInterpreter가 노드의 두 번째 이상 ContainedGraph 자식을 silent drop 하던 동작(C-A1)을 끄고 `Node.extra_subgraphs`에 보존 + warning. `_interpret_objects` 재귀에 깊이 cap을 두어 cyclic ContainedGraph 입력에도 stack overflow 대신 warning을 남기고 중단(C-A2).

**Architecture:** `Node.extra_subgraphs: list[GraphModel]` 슬롯 추가. `_add_node`가 graph_children을 전부 모아 첫 개는 `subgraph`, 나머지는 `extra_subgraphs`. `_interpret_objects`는 `depth` 파라미터를 받고 `max_depth=64` 초과 시 빈 `GraphModel`+warning 반환.

**Tech Stack:** Python 3.11+, pytest.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-batch-3-info-preservation-design.md` §5.3.

**의존:** 없음. slice α와 같은 `graph_model.py`를 수정하지만 α 머지 후 진입 권장(conflict 회피).

**PRESERVE-INFO 불변식:** 두 번째 자식 graph도 모델에 보존. 재귀 cap 발동도 silent return ✗ → warning + 빈 GraphModel.

---

## 파일 구조

| 파일 | 책임 | 변경 |
|---|---|---|
| `src/t3dgraph/core/base/graph_model.py` | `Node.extra_subgraphs` 필드 | 수정 |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 다중 자식 보존 + 깊이 cap | 수정 |
| `tests/core/base/test_graph_model.py` | `extra_subgraphs` 단위 | 수정 |
| `tests/plugins/rigvm/test_interpreter_multi_subgraph.py` | 다중 자식 동작 | 신규 |
| `tests/plugins/rigvm/test_interpreter_depth_cap.py` | 깊이 cap 동작 | 신규 |

---

### Task 1: `Node.extra_subgraphs` 필드

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`
- Modify: `tests/core/base/test_graph_model.py`

- [ ] **Step 1: Test**

`tests/core/base/test_graph_model.py`에 추가:

```python
from t3dgraph.core.base.graph_model import GraphModel, Node


def test_node_extra_subgraphs_default_empty():
    n = Node(name="X", cls=None)
    assert n.extra_subgraphs == []


def test_node_extra_subgraphs_accepts_models():
    inner1 = GraphModel(label="g1")
    inner2 = GraphModel(label="g2")
    n = Node(name="X", cls=None, subgraph=inner1, extra_subgraphs=[inner2])
    assert n.subgraph is inner1
    assert n.extra_subgraphs == [inner2]
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/base/test_graph_model.py -k "extra_subgraphs" -v
```
Expected: FAIL.

- [ ] **Step 3: 변경**

`graph_model.py` `Node` dataclass:

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
    display_name: str | None = None
    role_summary: str | None = None
    role_category: str | None = None
    subgraph: "GraphModel | None" = None
    extra_subgraphs: list["GraphModel"] = field(default_factory=list)   # NEW (C)
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/base/graph_model.py tests/core/base/test_graph_model.py
git commit -m "feat(graph_model): Node.extra_subgraphs for multi-ContainedGraph (C-A1 prep)"
```

---

### Task 2: 인터프리터 — 다중 자식 보존

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py` (`_add_node`)
- Create: `tests/plugins/rigvm/test_interpreter_multi_subgraph.py`

- [ ] **Step 1: Failing tests**

```python
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _unit(name):
    return T3DObject(name=name,
                     cls="/Script/RigVMDeveloper.RigVMUnitNode",
                     properties={}, children=[])


def _graph_child(name, inner_nodes):
    return T3DObject(name=name,
                     cls="/Script/RigVMDeveloper.RigVMGraph",
                     properties={}, children=inner_nodes)


def test_single_subgraph_unchanged():
    """기존 동작 회귀 — 한 자식이면 subgraph에 그대로."""
    collapse = T3DObject(
        name="Solo",
        cls="/Script/RigVMDeveloper.RigVMCollapseNode",
        properties={},
        children=[_graph_child("Solo_ContainedGraph", [_unit("Inner")])],
    )
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[collapse]))
    parent = g.nodes[0]
    assert parent.subgraph is not None
    assert parent.extra_subgraphs == []


def test_two_subgraph_children_both_preserved():
    """C-A1: 두 자식 graph — 첫 개는 subgraph, 두 번째는 extra_subgraphs."""
    collapse = T3DObject(
        name="P",
        cls="/Script/RigVMDeveloper.RigVMCollapseNode",
        properties={},
        children=[
            _graph_child("P_ContainedGraph", [_unit("A")]),
            _graph_child("P_ContainedGraph_2", [_unit("B")]),
        ],
    )
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[collapse]))
    parent = g.nodes[0]
    assert parent.subgraph is not None
    assert [n.name for n in parent.subgraph.nodes] == ["A"]
    assert len(parent.extra_subgraphs) == 1
    assert [n.name for n in parent.extra_subgraphs[0].nodes] == ["B"]


def test_two_subgraph_warning_emitted():
    """PRESERVE-INFO: 다중 자식 발견은 warning으로 가시화."""
    collapse = T3DObject(
        name="P",
        cls="/Script/RigVMDeveloper.RigVMCollapseNode",
        properties={},
        children=[
            _graph_child("c1", [_unit("X")]),
            _graph_child("c2", [_unit("Y")]),
        ],
    )
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[collapse]))
    assert any("RigVMGraph 자식" in w and "P" in w for w in g.warnings)


def test_three_subgraph_children_all_preserved():
    collapse = T3DObject(
        name="P",
        cls="/Script/RigVMDeveloper.RigVMCollapseNode",
        properties={},
        children=[_graph_child(f"c{i}", [_unit(f"N{i}")]) for i in range(3)],
    )
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[collapse]))
    parent = g.nodes[0]
    assert parent.subgraph is not None
    assert len(parent.extra_subgraphs) == 2
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Modify `_add_node`**

```python
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
    graph_children = [c for c in obj.children if t.is_graph_class(c.cls)]
    for i, child in enumerate(graph_children):
        sub = self._interpret_objects(
            child.children,
            label=f"{node.name}/{child.name or 'graph'}",
            parent_node=node.name,
        )
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
    if obj.cls and obj.cls.rsplit(".", 1)[-1] == "RigVMVariableNode":
        self._add_variable_ref(node, g)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/plugins/rigvm/test_interpreter_multi_subgraph.py -v
```

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/plugins/rigvm/interpreter.py tests/plugins/rigvm/test_interpreter_multi_subgraph.py
git commit -m "feat(rigvm): preserve multi-ContainedGraph children in Node.extra_subgraphs (C-A1)"
```

---

### Task 3: `_interpret_objects` 깊이 cap

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Create: `tests/plugins/rigvm/test_interpreter_depth_cap.py`

- [ ] **Step 1: Failing tests**

```python
import sys
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _unit(name):
    return T3DObject(name=name,
                     cls="/Script/RigVMDeveloper.RigVMUnitNode",
                     properties={}, children=[])


def _nest(depth: int) -> T3DObject:
    """깊이 depth 만큼 collapse→graph→collapse 중첩 — 합성."""
    inner = _unit("Leaf")
    obj = inner
    for i in range(depth):
        graph = T3DObject(
            name=f"g{i}",
            cls="/Script/RigVMDeveloper.RigVMGraph",
            properties={},
            children=[obj],
        )
        obj = T3DObject(
            name=f"c{i}",
            cls="/Script/RigVMDeveloper.RigVMCollapseNode",
            properties={},
            children=[graph],
        )
    return obj


def test_normal_depth_no_warning():
    obj = _nest(5)
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    assert all("깊이" not in w for w in g.warnings)


def test_excessive_depth_caps_with_warning():
    # max_depth=64. 100단 입력 시 cap 발동.
    obj = _nest(100)
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    # 최상위 노드는 살아 있음
    assert len(g.nodes) == 1
    # 어딘가 깊이 초과 경고
    assert any("깊이" in w for w in g.warnings)


def test_custom_max_depth():
    obj = _nest(10)
    interp = RigVMGraphInterpreter()
    # max_depth=3으로 강제 → 깊이 4부터 cap
    g = interp._interpret_objects(
        [obj], label=None, parent_node=None, depth=0, max_depth=3
    )
    assert any("깊이" in w for w in g.warnings)
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Modify `_interpret_objects`**

```python
def _interpret_objects(
    self,
    objects: list[T3DObject],
    *,
    label: str | None,
    parent_node: str | None,
    depth: int = 0,
    max_depth: int = 64,
) -> GraphModel:
    if depth >= max_depth:
        g = GraphModel(label=label, parent_node=parent_node)
        g.warnings.append(
            f"interpret 깊이 {depth} ≥ {max_depth} — 추가 추출 중단 "
            f"(label={label or '?'})"
        )
        return g

    g = GraphModel(label=label, parent_node=parent_node)
    for obj in objects:
        if t.is_link_class(obj.cls):
            self._add_link(obj, g)
        elif t.is_node_class(obj.cls):
            self._add_node(obj, g, _depth=depth, _max_depth=max_depth)
        elif obj.cls is None:
            continue
        elif t.is_graph_class(obj.cls):
            g.warnings.append(
                f"최상위에 RigVMGraph 객체 '{obj.name or '?'}' 발견 — "
                f"자식 {len(obj.children)}개가 추출되지 않음"
            )
            continue
        else:
            self._add_generic(obj, g)
    known = {n.name for n in g.nodes}
    for link in g.links:
        for path in (link.source_path, link.target_path):
            node = node_of(path)
            if node not in known and path not in g.external_refs:
                g.external_refs.append(path)
    return g


def _add_node(self, obj: T3DObject, g: GraphModel,
              *, _depth: int = 0, _max_depth: int = 64) -> None:
    # ... 노드 생성 (위와 동일) ...
    graph_children = [c for c in obj.children if t.is_graph_class(c.cls)]
    for i, child in enumerate(graph_children):
        sub = self._interpret_objects(
            child.children,
            label=f"{node.name}/{child.name or 'graph'}",
            parent_node=node.name,
            depth=_depth + 1,
            max_depth=_max_depth,
        )
        if i == 0:
            node.subgraph = sub
        else:
            node.extra_subgraphs.append(sub)
    if len(graph_children) > 1:
        g.warnings.append(...)
    g.nodes.append(node)
    ...
```

`_add_generic`도 동일 패턴(필요시).

- [ ] **Step 4: Run — pass**

```
pytest tests/plugins/rigvm/test_interpreter_depth_cap.py -v
```

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/plugins/rigvm/interpreter.py tests/plugins/rigvm/test_interpreter_depth_cap.py
git commit -m "feat(rigvm): max_depth=64 cap on recursive interpret (C-A2)"
```

---

### Task 4: 회귀 + Orion smoke

**Files:**
- Run: `pytest tests/ -v`

- [ ] **Step 1: 전체 회귀**

```
pytest tests/ -v
```

기존 단일 ContainedGraph smoke 테스트가 통과해야 함 — `Node.extra_subgraphs == []` 가정.

- [ ] **Step 2: smoke — Orion 데이터에서 다중 자식 가진 노드 있는지 확인**

`tests/smoke_extra_subgraphs_orion.py`(신규):

```python
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from pathlib import Path

p = Path("Orion_WorkStation_Rig_Analysis/"
         "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
g = default_registry().detect(parse_document(read_t3d_text(p))).interpreter_factory().interpret(parse_document(read_t3d_text(p)))

multi = [n for n in g.nodes if n.extra_subgraphs]
single = [n for n in g.nodes if n.subgraph is not None and not n.extra_subgraphs]
print(f"단일 subgraph 노드: {len(single)}")
print(f"다중 subgraph 노드(extra_subgraphs 있음): {len(multi)}")
print(f"warnings: {len(g.warnings)}")
# 실제 데이터에 다중 자식이 없을 수도 있음 — assertion 안 함, 정보 출력만
```

실행: `python tests/smoke_extra_subgraphs_orion.py`

- [ ] **Step 3: Commit (smoke)**

```
git add tests/smoke_extra_subgraphs_orion.py
git commit -m "test: smoke for extra_subgraphs count on Orion"
```

---

## 완료 정의

- [ ] Task 1-4 PASS
- [ ] 두 자식 graph 있는 노드에서 둘 다 모델에 보존 (subgraph + extra_subgraphs)
- [ ] 다중 자식 발견 시 `g.warnings`에 가시화
- [ ] 깊이 cap 발동 시 stack overflow 대신 warning + 빈 GraphModel 반환
- [ ] 기존 단일 subgraph 테스트 회귀 없음
