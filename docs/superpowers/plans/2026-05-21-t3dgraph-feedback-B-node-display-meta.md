# Slice B: 노드 표시명 + 역할 메타 (F1, F3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 노드의 사람-친화적 표시명(F1)과 역할 메타(F3)를 RigVM 메타에서 추출해 인스펙터·검색에 노출한다. 원본 `name`은 모든 식별자·앵커에서 그대로 유지.

**Architecture:** `Node`에 `display_name`/`role_summary`/`role_category` 추가. RigVM interpreter가 `plugins/rigvm/display_name.py` + `plugins/rigvm/role.py` 헬퍼로 채움. items.py 노드 타이틀, inspector_panel 헤더, node_filter_panel 검색이 display_name을 OR 매치.

**Tech Stack:** Python 3.11+, PySide6, pytest.

**Spec ref:** `docs/superpowers/specs/2026-05-21-t3dgraph-user-feedback-batch-design.md` §5.2, §5.3.

**노드 보존 불변식(PRESERVE-ALL):** display_name 없거나 role 없어도 노드는 그대로 표시(원본 name fallback). 검색 결과 0 시에도 노드 hide 금지.

---

## 파일 구조

| 파일 | 책임 | 변경 종류 |
|---|---|---|
| `src/t3dgraph/core/base/graph_model.py` | `Node`에 `display_name`/`role_summary`/`role_category` 필드 | 수정 |
| `src/t3dgraph/plugins/rigvm/display_name.py` | RigVM 객체 → 표시명 결정 | 신규 |
| `src/t3dgraph/plugins/rigvm/role.py` | RigVM 객체 → (signature, category) 결정 | 신규 |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | `_add_node`/`_add_generic`에서 위 두 헬퍼 호출 | 수정 |
| `src/t3dgraph/core/app/items.py` | 노드 타이틀에 display_name 우선 | 수정 |
| `src/t3dgraph/core/app/inspector_panel.py` | 헤더 "name [cls]"에 "역할: …" 한 줄 추가 | 수정 |
| `src/t3dgraph/core/app/node_filter_panel.py` | 검색에 display_name OR 매치 | 수정 |
| `tests/plugins/rigvm/test_display_name.py` | 결정 케이스 단위 | 신규 |
| `tests/plugins/rigvm/test_role.py` | 시그니처/카테고리 케이스 단위 | 신규 |
| `tests/plugins/rigvm/test_interpreter_meta.py` | 통합 — interpret 후 meta 채움 확인 | 신규 |
| `tests/core/app/test_inspector_role_header.py` | 인스펙터 헤더 표시 | 신규 |

---

### Task 1: graph_model — Node 메타 필드 추가

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`

- [ ] **Step 1: Test — Node 인스턴스화에 옵셔널 필드 허용**

`tests/core/base/test_graph_model.py`(존재 시 append, 없으면 신규):

```python
from t3dgraph.core.base.graph_model import Node


def test_node_meta_fields_default_none():
    n = Node(name="X", cls=None)
    assert n.display_name is None
    assert n.role_summary is None
    assert n.role_category is None


def test_node_meta_fields_accept_value():
    n = Node(name="X", cls=None,
             display_name="Begin Execution",
             role_summary="(no args)",
             role_category="Execution")
    assert n.display_name == "Begin Execution"
    assert n.role_summary == "(no args)"
    assert n.role_category == "Execution"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/base/test_graph_model.py::test_node_meta_fields_default_none -v
```
Expected: FAIL (unexpected keyword argument).

- [ ] **Step 3: 변경**

`src/t3dgraph/core/base/graph_model.py`의 `Node` dataclass에 추가:

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
    display_name: str | None = None          # NEW
    role_summary: str | None = None          # NEW
    role_category: str | None = None         # NEW
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/base/test_graph_model.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/base/graph_model.py tests/core/base/test_graph_model.py
git commit -m "feat(graph_model): add display_name/role meta fields (F1, F3 prep)"
```

---

### Task 2: display_name 결정 헬퍼

**Files:**
- Create: `src/t3dgraph/plugins/rigvm/display_name.py`
- Create: `tests/plugins/rigvm/test_display_name.py`

- [ ] **Step 1: Failing tests**

`tests/plugins/rigvm/test_display_name.py`:

```python
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.values import Scalar, QuotedString
from t3dgraph.plugins.rigvm.display_name import display_name_for


def _obj(name, cls, **props):
    return T3DObject(name=name, cls=cls, properties=props, children=[])


def test_unit_node_strips_rigunit_prefix():
    o = _obj("RigUnit_BeginExecution",
             "/Script/RigVMDeveloper.RigVMUnitNode")
    assert display_name_for(o) == "Begin Execution"


def test_unit_node_camelcase_split():
    o = _obj("RigUnit_StepPhysicsSolver",
             "/Script/RigVMDeveloper.RigVMUnitNode")
    assert display_name_for(o) == "Step Physics Solver"


def test_dispatch_uses_resolved_function_prefix():
    o = _obj(
        "RigVMDispatch_GetItemAtIndex_3",
        "/Script/RigVMDeveloper.RigVMDispatchNode",
        ResolvedFunctionName=QuotedString("GetItemAtIndex::Execute(in Array,in Index,out Item)"),
    )
    assert display_name_for(o) == "Get Item At Index"


def test_dispatch_falls_back_to_template_notation():
    o = _obj(
        "RigVMDispatch_Foo_2",
        "/Script/RigVMDeveloper.RigVMDispatchNode",
        TemplateNotation=QuotedString("Foo(in A,in B,out Result)"),
    )
    assert display_name_for(o) == "Foo"


def test_variable_uses_variable_pin_default():
    var_pin = T3DObject(
        name="Variable",
        cls="/Script/RigVMDeveloper.RigVMPin",
        properties={"DefaultValue": QuotedString("IKTarget")},
        children=[],
    )
    o = T3DObject(
        name="RigVMVariableNode_4",
        cls="/Script/RigVMDeveloper.RigVMVariableNode",
        properties={},
        children=[var_pin],
    )
    assert display_name_for(o) == "IKTarget"


def test_unknown_falls_back_to_name():
    o = _obj("SomeWeird_5", "/Script/RigVMDeveloper.RigVMRerouteNode")
    assert display_name_for(o) == "SomeWeird_5"


def test_no_cls_returns_name():
    o = _obj("Anon", None)
    assert display_name_for(o) == "Anon"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/plugins/rigvm/test_display_name.py -v
```
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

`src/t3dgraph/plugins/rigvm/display_name.py`:

```python
"""RigVM 객체 → 사람-친화 표시명 결정. 실패 시 원본 name fallback."""
from __future__ import annotations
import re
from ...core.t3d.objects import T3DObject
from ...core.t3d.values import Value, Scalar, QuotedString


def _text(v: Value | None) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


_CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _camel_split(s: str) -> str:
    return _CAMEL_SPLIT.sub(" ", s)


def _suffix(cls: str | None) -> str:
    if not cls:
        return ""
    return cls.rsplit(".", 1)[-1]


def display_name_for(obj: T3DObject) -> str:
    """노드 객체의 표시명. 원본 name이 항상 fallback."""
    name = obj.name or ""
    if not obj.cls:
        return name
    sfx = _suffix(obj.cls)

    if sfx == "RigVMUnitNode":
        bare = name
        if bare.startswith("RigUnit_"):
            bare = bare[len("RigUnit_"):]
        # trailing _숫자 (인스턴스 식별자) 제거
        bare = re.sub(r"_\d+$", "", bare)
        return _camel_split(bare) or name

    if sfx == "RigVMDispatchNode":
        resolved = _text(obj.properties.get("ResolvedFunctionName"))
        notation = _text(obj.properties.get("TemplateNotation"))
        sig = resolved or notation
        if sig:
            head = sig.split("::")[0].split("(")[0]
            return _camel_split(head) or name
        # fallback — RigVMDispatch_ prefix 제거 + 숫자 suffix 제거
        bare = name
        if bare.startswith("RigVMDispatch_"):
            bare = bare[len("RigVMDispatch_"):]
        bare = re.sub(r"_\d+$", "", bare)
        return _camel_split(bare) or name

    if sfx == "RigVMVariableNode":
        for child in obj.children:
            if child.name == "Variable":
                vt = _text(child.properties.get("DefaultValue"))
                if vt:
                    return vt
        return name

    # CollapseNode / FunctionReferenceNode / FunctionEntry / Return / Reroute …
    # 모두 원본 name 그대로(이미 사용자-부여 라벨이거나 의미 있는 식별자)
    return name
```

- [ ] **Step 4: Run — pass**

```
pytest tests/plugins/rigvm/test_display_name.py -v
```
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/plugins/rigvm/display_name.py tests/plugins/rigvm/test_display_name.py
git commit -m "feat(rigvm): display_name resolver (F1)"
```

---

### Task 3: role(signature/category) 결정 헬퍼

**Files:**
- Create: `src/t3dgraph/plugins/rigvm/role.py`
- Create: `tests/plugins/rigvm/test_role.py`

- [ ] **Step 1: Failing tests**

`tests/plugins/rigvm/test_role.py`:

```python
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.values import QuotedString
from t3dgraph.plugins.rigvm.role import role_for


def _obj(name, cls, **props):
    return T3DObject(name=name, cls=cls, properties=props, children=[])


def test_dispatch_signature_from_resolved():
    o = _obj(
        "RigVMDispatch_GetItemAtIndex_3",
        "/Script/RigVMDeveloper.RigVMDispatchNode",
        ResolvedFunctionName=QuotedString("GetItemAtIndex::Execute(in TArray<float> Array,in int32 Index,out float Item)"),
    )
    summary, category = role_for(o)
    assert summary == "GetItemAtIndex(TArray<float>, int32) → float"
    assert category == "Dispatch"


def test_unit_node_signature_falls_back_to_struct():
    o = _obj(
        "RigUnit_BeginExecution",
        "/Script/RigVMDeveloper.RigVMUnitNode",
        ScriptStruct=QuotedString("/Script/ControlRig.RigUnit_BeginExecution"),
    )
    summary, category = role_for(o)
    assert summary == "RigUnit_BeginExecution"
    assert category == "Unit"


def test_variable_role():
    o = _obj("RigVMVariableNode_4",
             "/Script/RigVMDeveloper.RigVMVariableNode")
    summary, category = role_for(o)
    assert summary is None
    assert category == "Variable"


def test_collapse_role():
    o = _obj("Physics", "/Script/RigVMDeveloper.RigVMCollapseNode")
    summary, category = role_for(o)
    assert summary is None
    assert category == "Subgraph"


def test_unknown_returns_none():
    o = _obj("X", None)
    assert role_for(o) == (None, None)
```

- [ ] **Step 2: Run — fail**

```
pytest tests/plugins/rigvm/test_role.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement**

`src/t3dgraph/plugins/rigvm/role.py`:

```python
"""RigVM 노드 객체 → (시그니처 요약, 카테고리)."""
from __future__ import annotations
import re
from ...core.t3d.objects import T3DObject
from ...core.t3d.values import Value, Scalar, QuotedString


def _text(v: Value | None) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


def _suffix(cls: str | None) -> str:
    return cls.rsplit(".", 1)[-1] if cls else ""


_CATEGORY = {
    "RigVMUnitNode": "Unit",
    "RigVMDispatchNode": "Dispatch",
    "RigVMVariableNode": "Variable",
    "RigVMFunctionEntryNode": "Entry",
    "RigVMFunctionReturnNode": "Return",
    "RigVMCollapseNode": "Subgraph",
    "RigVMFunctionReferenceNode": "Subgraph",
    "RigVMRerouteNode": "Reroute",
}


def _parse_signature(sig: str) -> str:
    """'Name::Execute(in T A,out U B)' → 'Name(T) → U'.

    파싱 실패 시 원문 그대로.
    """
    head, _, tail = sig.partition("(")
    if not tail.endswith(")"):
        return sig
    func_name = head.split("::")[0].strip()
    args_src = tail[:-1]
    inputs: list[str] = []
    outputs: list[str] = []
    if args_src.strip():
        for raw in args_src.split(","):
            tok = raw.strip()
            m = re.match(r"^(in|out)\s+(.+?)(?:\s+\w+)?$", tok)
            if not m:
                continue
            direction, type_part = m.group(1), m.group(2).strip()
            (inputs if direction == "in" else outputs).append(type_part)
    in_part = ", ".join(inputs) if inputs else ""
    out_part = ", ".join(outputs) if outputs else "void"
    return f"{func_name}({in_part}) → {out_part}"


def role_for(obj: T3DObject) -> tuple[str | None, str | None]:
    cls_sfx = _suffix(obj.cls)
    category = _CATEGORY.get(cls_sfx)
    if not category:
        return None, None

    if cls_sfx == "RigVMDispatchNode":
        sig = _text(obj.properties.get("ResolvedFunctionName")) \
            or _text(obj.properties.get("TemplateNotation"))
        if sig:
            return _parse_signature(sig), category
        return None, category

    if cls_sfx == "RigVMUnitNode":
        struct = _text(obj.properties.get("ScriptStruct"))
        if struct:
            # 마지막 컴포넌트만
            return struct.rsplit(".", 1)[-1].rsplit("/", 1)[-1], category
        # ScriptStruct 미가용 시 name fallback
        return obj.name or None, category

    return None, category
```

- [ ] **Step 4: Run — pass**

```
pytest tests/plugins/rigvm/test_role.py -v
```
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/plugins/rigvm/role.py tests/plugins/rigvm/test_role.py
git commit -m "feat(rigvm): role(signature, category) resolver (F3)"
```

---

### Task 4: interpreter — 메타 채움

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py:83-115` (`_add_node`, `_add_generic`)
- Create: `tests/plugins/rigvm/test_interpreter_meta.py`

- [ ] **Step 1: Test**

`tests/plugins/rigvm/test_interpreter_meta.py`:

```python
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.values import QuotedString
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_interpret_fills_display_name_and_role():
    obj = T3DObject(
        name="RigUnit_BeginExecution",
        cls="/Script/RigVMDeveloper.RigVMUnitNode",
        properties={"ScriptStruct": QuotedString("/Script/ControlRig.RigUnit_BeginExecution")},
        children=[],
    )
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1
    n = g.nodes[0]
    assert n.name == "RigUnit_BeginExecution"
    assert n.display_name == "Begin Execution"
    assert n.role_summary == "RigUnit_BeginExecution"
    assert n.role_category == "Unit"


def test_interpret_preserves_node_even_when_meta_missing():
    """PRESERVE-ALL: 메타 결정 실패해도 노드는 그대로."""
    obj = T3DObject(
        name="X",
        cls="/Script/RigVMDeveloper.RigVMUnitNode",
        properties={},
        children=[],
    )
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1
    n = g.nodes[0]
    assert n.name == "X"
    assert n.display_name == "X"        # fallback to name
    # role_summary may be None or X — 둘 다 허용
    assert n.role_category == "Unit"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/plugins/rigvm/test_interpreter_meta.py -v
```
Expected: FAIL (`display_name` is None).

- [ ] **Step 3: Modify interpreter**

`src/t3dgraph/plugins/rigvm/interpreter.py`:

```python
# 상단 import에 추가
from .display_name import display_name_for
from .role import role_for


# _add_node 안에서 Node(...) 생성 시 추가
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
    g.nodes.append(node)
    ...
```

`_add_generic`도 동일하게 추가:

```python
def _add_generic(self, obj: T3DObject, g: GraphModel) -> None:
    g.warnings.append(...)
    summary, category = role_for(obj)
    g.nodes.append(Node(
        name=obj.name or "",
        cls=obj.cls,
        pins=[_build_pin(c) for c in obj.children],
        position=_position(obj),
        raw=dict(obj.properties),
        is_generic=True,
        kind=_classify_kind(obj),
        display_name=display_name_for(obj),
        role_summary=summary,
        role_category=category,
    ))
```

- [ ] **Step 4: Run — pass**

```
pytest tests/plugins/rigvm/test_interpreter_meta.py -v
```
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/plugins/rigvm/interpreter.py tests/plugins/rigvm/test_interpreter_meta.py
git commit -m "feat(rigvm): populate display_name/role on Node (F1, F3)"
```

---

### Task 5: items.py — 노드 타이틀 display_name 우선

**Files:**
- Modify: `src/t3dgraph/core/app/items.py:41-44` (헤더 텍스트 결정)

- [ ] **Step 1: Test**

`tests/core/app/test_items_rows.py` 또는 신규 `tests/core/app/test_node_title.py`:

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.base.graph_model import Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_node_title_uses_display_name_when_set(qapp):
    node = Node(name="RigUnit_BeginExecution", cls=None,
                display_name="Begin Execution")
    item = NodeItem(node)
    # NodeItem children에 SimpleTextItem 첫 번째가 헤더 — 직접 확인
    titles = [c.text() for c in item.childItems()
              if c.__class__.__name__ == "QGraphicsSimpleTextItem"]
    assert titles[0] == "Begin Execution"


def test_node_title_fallback_to_name(qapp):
    node = Node(name="X", cls=None, display_name=None)
    item = NodeItem(node)
    titles = [c.text() for c in item.childItems()
              if c.__class__.__name__ == "QGraphicsSimpleTextItem"]
    assert titles[0] == "X"
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_node_title.py -v
```
Expected: FAIL (display_name 무시되고 name만 표시).

- [ ] **Step 3: Modify items.py**

`NodeItem.__init__` 헤더 부분:

```python
header_text = node.display_name or node.name or "?"
title = QGraphicsSimpleTextItem(header_text, self)
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_node_title.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/items.py tests/core/app/test_node_title.py
git commit -m "feat(items): node title uses display_name (F1)"
```

---

### Task 6: inspector_panel — 헤더에 역할 한 줄

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py:43-53` (`show_node`)
- Create: `tests/core/app/test_inspector_role_header.py`

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.inspector_panel import InspectorPanel
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_inspector_header_includes_role_summary(qapp):
    panel = InspectorPanel()
    g = GraphModel(nodes=[Node(
        name="RigUnit_BeginExecution", cls="...RigVMUnitNode",
        display_name="Begin Execution",
        role_summary="RigUnit_BeginExecution",
        role_category="Unit",
    )])
    panel.show_node(g.nodes[0], g)
    assert "Begin Execution" in panel._title.text()
    assert "Unit" in panel._title.text()
    assert "RigUnit_BeginExecution" in panel._title.text()


def test_inspector_header_skips_role_when_absent(qapp):
    panel = InspectorPanel()
    g = GraphModel(nodes=[Node(name="X", cls=None)])
    panel.show_node(g.nodes[0], g)
    # 노드 표시는 살아 있어야 함 (PRESERVE-ALL)
    assert "X" in panel._title.text()
```

- [ ] **Step 2: Run — fail**

```
pytest tests/core/app/test_inspector_role_header.py -v
```
Expected: FAIL.

- [ ] **Step 3: Modify show_node**

```python
def show_node(self, node: Node | None, graph: GraphModel) -> None:
    self._tree.clear()
    self._items = {}
    if node is None:
        self._title.setText("(노드를 선택하세요)")
        return
    header = node.display_name or node.name or "?"
    cls_part = node.cls or "?"
    role_bits = []
    if node.role_category:
        role_bits.append(node.role_category)
    if node.role_summary:
        role_bits.append(node.role_summary)
    role_suffix = f"   ·   역할: {' · '.join(role_bits)}" if role_bits else ""
    self._title.setText(f"{header}  [{cls_part}]{role_suffix}")
    connected = _connected_pin_paths(graph)
    for pin in node.pins:
        self._add_pin(pin, node.name, pin.name, connected, graph,
                      self._tree.invisibleRootItem())
```

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_inspector_role_header.py -v
```
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/inspector_panel.py tests/core/app/test_inspector_role_header.py
git commit -m "feat(inspector): role line in header (F3)"
```

---

### Task 7: node_filter_panel — 검색 시 display_name OR 매치

**Files:**
- Modify: `src/t3dgraph/core/app/node_filter_panel.py`

기존 panel은 노드 *클래스 접미사* 단위 토글이라, "검색"은 신규 기능. 안전한 변경 폭을 위해 **type 단위 hide는 그대로 두고**, 별도 *이름 검색 박스*를 추가. PRESERVE-ALL이라 검색은 노드를 dim/highlight 할 뿐 hide 안 함.

- [ ] **Step 1: 현 구조 확인**

```
cat src/t3dgraph/core/app/node_filter_panel.py
```

- [ ] **Step 2: Test — 검색어가 display_name에도 매치**

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.node_filter_panel import NodeFilterPanel
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_match_node_by_name(qapp):
    g = GraphModel(nodes=[
        Node(name="RigUnit_BeginExecution", cls=None, display_name="Begin Execution"),
        Node(name="StepPhysicsSolver", cls=None, display_name="Step Physics Solver"),
    ])
    panel = NodeFilterPanel()
    panel.set_graph(g)
    panel.set_search_text("step")
    hits = panel.matched_node_names()
    assert "StepPhysicsSolver" in hits
    assert "RigUnit_BeginExecution" not in hits


def test_match_node_by_display_name(qapp):
    g = GraphModel(nodes=[
        Node(name="RigUnit_BeginExecution", cls=None, display_name="Begin Execution"),
    ])
    panel = NodeFilterPanel()
    panel.set_graph(g)
    panel.set_search_text("begin")
    hits = panel.matched_node_names()
    assert "RigUnit_BeginExecution" in hits


def test_empty_search_returns_all(qapp):
    g = GraphModel(nodes=[
        Node(name="A", cls=None), Node(name="B", cls=None),
    ])
    panel = NodeFilterPanel()
    panel.set_graph(g)
    panel.set_search_text("")
    hits = panel.matched_node_names()
    assert hits == {"A", "B"}    # PRESERVE-ALL: 빈 검색은 전체 매치 = 노드 hide 없음
```

- [ ] **Step 3: Run — fail**

```
pytest tests/core/app/test_node_filter_search.py -v
```
Expected: FAIL.

- [ ] **Step 4: Implement**

기존 NodeFilterPanel에 검색 QLineEdit 추가 + 메서드:

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit, QVBoxLayout

class NodeFilterPanel(QWidget):
    # ... 기존 시그널들 ...
    search_changed = Signal()                       # NEW

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("이름/표시명 검색…")
        self._search.textChanged.connect(lambda _: self.search_changed.emit())
        layout.addWidget(self._search)
        # ... 기존 type-toggle UI ...
        self._graph = None

    def set_graph(self, graph):
        self._graph = graph
        # ... 기존 타입 목록 채우기 ...

    def set_search_text(self, text: str) -> None:
        self._search.setText(text)

    def matched_node_names(self) -> set[str]:
        if self._graph is None:
            return set()
        q = self._search.text().strip().lower()
        if not q:
            return {n.name for n in self._graph.nodes}
        out = set()
        for n in self._graph.nodes:
            if q in (n.name or "").lower():
                out.add(n.name)
            elif n.display_name and q in n.display_name.lower():
                out.add(n.name)
        return out
```

`MainWindow._wire`에 추가 — 검색 변경 시 scene에 dim 적용:

```python
self.node_filter.search_changed.connect(self._on_search_changed)

def _on_search_changed(self) -> None:
    if self.graph is None:
        return
    hits = self.node_filter.matched_node_names()
    self.scene.apply_search_highlight(hits)
```

`GraphScene`에 메서드:

```python
def apply_search_highlight(self, hits: set[str]) -> None:
    """검색어 매치 노드는 그대로, 미매치는 흐리게(투명도). 노드는 hide 금지."""
    full_opacity = 1.0
    dim_opacity = 0.35
    for name, item in self._nodes.items():
        item.setOpacity(full_opacity if name in hits else dim_opacity)
```

- [ ] **Step 5: Run — pass**

```
pytest tests/core/app/test_node_filter_search.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```
git add src/t3dgraph/core/app/node_filter_panel.py src/t3dgraph/core/app/main_window.py \
        src/t3dgraph/core/app/scene.py tests/core/app/test_node_filter_search.py
git commit -m "feat(node_filter): name/display_name search with dim highlight (F1; PRESERVE-ALL)"
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

- [ ] **Step 2: smoke — display_name이 채워지는지 RigVMModel.t3d.txt로 확인**

`tests/smoke_display_name.py`(신규):

```python
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from pathlib import Path

p = Path("Orion_WorkStation_Rig_Analysis/"
         "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
g = default_registry().detect(parse_document(read_t3d_text(p))).interpreter_factory().interpret(parse_document(read_t3d_text(p)))
filled = sum(1 for n in g.nodes if n.display_name and n.display_name != n.name)
print(f"전체 {len(g.nodes)} 중 {filled} 노드가 표시명 별도 부여")
assert filled > 0
```

실행 후 출력 확인.

- [ ] **Step 3: Commit (smoke 추가했으면)**

```
git add tests/smoke_display_name.py
git commit -m "test: smoke for display_name on Orion RigVMModel"
```

---

## 완료 정의

- [ ] 모든 Task 1-8 체크박스 PASS
- [ ] 새/기존 테스트 전체 PASS
- [ ] PRESERVE-ALL — display_name 없는 노드도 캔버스·인스펙터에 그대로
- [ ] 노드 타이틀이 display_name 우선, 인스펙터 헤더에 역할 한 줄
- [ ] 검색 박스로 name/display_name OR 매치, 미매치 노드는 dim만 (hide ✗)
