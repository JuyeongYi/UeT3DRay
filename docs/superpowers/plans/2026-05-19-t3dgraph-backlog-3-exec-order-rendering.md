# t3dgraph 백로그 정리 ③ — FEAT-5 실행 순서 코드형 렌더링 고도화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실행 순서 패널을 코드처럼 보이게 고도화한다 — 루프(ForEach)·시퀀스(Sequence)·함수/콜랩스 노드를 구별해 `ForEach N:`·`Sequence N:`·`N() { … }` 형태로 렌더링한다.

**Architecture:** spec §7.2의 실행 순서 코드 뷰 강화. 노드의 구조적 역할을 추상 `Node.kind`로 노출(RigVM 인터프리터가 분류 — 레이어 무관 분석은 그대로 소비), `ExecutionStep`이 이를 운반, 패널이 코드형으로 렌더.

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt.

**선행 조건:** 백로그 정리 ①·②a·②b 완료. 리포: `C:/Users/jylee/source/UeT3DRay`.

**근거:** `docs/superpowers/backlog.md` FEAT-5 — improver Phase 2c C1.

**범위 한정:** 본 계획은 **렌더링 고도화**까지다. 함수/콜랩스 노드는 `N() { … }`로 *표시*해 펼침 가능함을 알리되, 콜랩스 ContainedGraph로의 실제 **드릴다운 네비게이션은 범위 밖**(별도 후속 — `name(){}` 클릭 시 서브그래프 진입). 이유: 드릴다운은 멀티 그래프 로딩·뒤로가기 등 별도 설계가 필요하며, 코드형 렌더링만으로도 spec §7.2 "코드처럼"의 핵심 가치를 제공.

---

## File Structure (백로그 정리 ③)

| 파일 | 변경 | 내용 |
| --- | --- | --- |
| `src/t3dgraph/core/base/graph_model.py` | 수정 | `Node.kind` 필드 추가 |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 | 노드 구조 역할 분류 |
| `src/t3dgraph/core/analysis/execution_order.py` | 수정 | `ExecutionStep`이 `kind` 운반 |
| `src/t3dgraph/core/app/execution_order_panel.py` | 수정 | 코드형 렌더링 |

---

## Task 1: `Node.kind` — 노드 구조 역할 분류

추상 `Node`에 `kind` 필드를 추가하고, RigVM 인터프리터가 loop/sequence/function/node로 분류한다. 분석·뷰는 추상 `kind`만 본다(레이어 무관 유지).

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Modify: `tests/core/base/test_graph_model.py`
- Modify: `tests/plugins/rigvm/test_interpreter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/base/test_graph_model.py` 에 추가:

```python
def test_node_kind_defaults_to_node():
    assert Node(name="N", cls="X").kind == "node"
```

`tests/plugins/rigvm/test_interpreter.py` 에 추가:

```python
def test_interpreter_classifies_loop_node():
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMDispatchNode Name="For_Each"\n'
        'End Object\n'
        'Begin Object Name="For_Each"\n'
        '   TemplateNotation="DISPATCH_RigVMDispatch_ArrayIterator(in Array,out Element)"\n'
        'End Object\n'
    )
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.node_by_name("For_Each").kind == "loop"


def test_interpreter_classifies_function_node():
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMCollapseNode Name="Physics"\n'
        'End Object\n'
        'Begin Object Name="Physics"\n'
        '   ContainedGraph="/Script/RigVMDeveloper.RigVMGraph\'CollapseNode_ContainedGraph\'"\n'
        'End Object\n'
    )
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.node_by_name("Physics").kind == "function"


def test_interpreter_plain_unit_node_kind_node():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    assert g.node_by_name("A").kind == "node"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/base/test_graph_model.py tests/plugins/rigvm/test_interpreter.py -q`
Expected: FAIL — `Node`에 `kind` 없음 / 인터프리터가 분류 안 함

- [ ] **Step 3: 구현**

`core/base/graph_model.py` — `Node` 데이터클래스에 `kind` 필드 추가(`is_generic` 다음):

```python
@dataclass
class Node:
    name: str
    cls: str | None
    pins: list[Pin] = field(default_factory=list)
    position: tuple[float, float] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    is_generic: bool = False
    kind: str = "node"          # node | loop | sequence | function
```

`plugins/rigvm/interpreter.py` — 분류 헬퍼를 추가하고 `_add_node`·`_add_generic`에서 설정:

```python
def _classify_kind(obj: T3DObject) -> str:
    """노드의 구조적 역할 — loop / sequence / function / node."""
    suffix = (obj.cls or "").rsplit(".", 1)[-1]
    if suffix in ("RigVMCollapseNode", "RigVMFunctionReferenceNode"):
        return "function"
    if "ContainedGraph" in obj.properties:
        return "function"
    notation = _text(obj.properties.get("TemplateNotation")) or ""
    resolved = _text(obj.properties.get("ResolvedFunctionName")) or ""
    if "ArrayIterator" in notation:
        return "loop"
    if "Sequence" in resolved or "Sequence" in (obj.name or ""):
        return "sequence"
    return "node"
```

`_add_node` 의 `Node(...)` 생성에 `kind=_classify_kind(obj)` 추가:

```python
    def _add_node(self, obj: T3DObject, g: GraphModel) -> None:
        node = Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children if t.is_pin_class(c.cls) or c.cls is None],
            position=_position(obj),
            raw=dict(obj.properties),
            kind=_classify_kind(obj),
        )
        g.nodes.append(node)
        if obj.cls and obj.cls.rsplit(".", 1)[-1] == "RigVMVariableNode":
            self._add_variable_ref(node, g)
```

`_add_generic` 의 `Node(...)` 에도 `kind=_classify_kind(obj)` 추가 (제네릭 노드도 ContainedGraph 등으로 분류될 수 있음).

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/base tests/plugins/rigvm -q`
Expected: PASS — 기존 + 신규

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/base/graph_model.py src/t3dgraph/plugins/rigvm/interpreter.py tests/core/base/test_graph_model.py tests/plugins/rigvm/test_interpreter.py
git commit -m "feat: classify node structural kind (loop/sequence/function) (FEAT-5)"
```

---

## Task 2: `ExecutionStep`이 `kind` 운반

실행 순서 분석이 각 스텝에 노드의 `kind`를 실어 패널에 전달한다.

**Files:**
- Modify: `src/t3dgraph/core/analysis/execution_order.py`
- Modify: `tests/core/analysis/test_execution_order.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/analysis/test_execution_order.py` 에 추가:

```python
def test_execution_step_carries_node_kind():
    a = Node(name="A", cls="X", kind="loop", pins=[_ep("O", "Output")])
    b = Node(name="B", cls="X", kind="node", pins=[_ep("I", "Input")])
    g = GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")])
    order = compute_execution_order(g)
    by_node = {s.node: s.kind for s in order}
    assert by_node == {"A": "loop", "B": "node"}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/analysis/test_execution_order.py::test_execution_step_carries_node_kind -q`
Expected: FAIL — `ExecutionStep`에 `kind` 없음 (`AttributeError`)

- [ ] **Step 3: 구현**

`core/analysis/execution_order.py` — `ExecutionStep`에 `kind` 추가, `compute_execution_order`가 노드 kind를 운반:

```python
@dataclass
class ExecutionStep:
    node: str
    depth: int
    kind: str = "node"
```

`compute_execution_order` 함수 본문 시작부에 노드 kind 맵을 만들고, `ExecutionStep` 생성 시 사용:

```python
    if flow is None:
        flow = analyze_flow(graph)
    node_kind = {n.name: n.kind for n in graph.nodes}
    out_edges: dict[str, list[str]] = {}
    ...
```

`walk` 내부의 `steps.append(ExecutionStep(node=node, depth=depth))` 를:

```python
            steps.append(ExecutionStep(
                node=node, depth=depth, kind=node_kind.get(node, "node")))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/analysis/test_execution_order.py -q`
Expected: PASS — 기존(`==` 비교 테스트 포함) + 신규. `ExecutionStep`이 dataclass라 `kind` 기본값으로 기존 동등 비교 호환.

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/analysis/execution_order.py tests/core/analysis/test_execution_order.py
git commit -m "feat(analysis): ExecutionStep carries node kind (FEAT-5)"
```

---

## Task 3: 실행 순서 패널 코드형 렌더링

`ExecutionOrderPanel`이 `step.kind`에 따라 코드처럼 렌더 — `ForEach N:`·`Sequence N:`·`N() { … }`·`N`.

**Files:**
- Modify: `src/t3dgraph/core/app/execution_order_panel.py`
- Modify: `tests/core/app/test_execution_order_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_execution_order_panel.py` 에 추가:

```python
def test_kind_specific_rendering(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order([
        ExecutionStep("Loop", 0, "loop"),
        ExecutionStep("Body", 1, "node"),
        ExecutionStep("Seq", 0, "sequence"),
        ExecutionStep("Fn", 0, "function"),
    ])
    assert panel.row_text(0) == "ForEach Loop:"
    assert panel.row_text(1) == "    Body"
    assert panel.row_text(2) == "Sequence Seq:"
    assert panel.row_text(3) == "Fn() { … }"


def test_navigation_still_uses_node_name(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order([ExecutionStep("Loop", 0, "loop")])
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_row(0)
    assert sig.args == ["Loop"]                 # 렌더 텍스트가 아닌 노드명
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_execution_order_panel.py::test_kind_specific_rendering -q`
Expected: FAIL — 현재는 `_INDENT*depth + step.node` 평면 렌더

- [ ] **Step 3: 구현**

`core/app/execution_order_panel.py` — 행 텍스트 포맷 헬퍼를 추가하고 `show_order`가 사용:

```python
def _format_step(step) -> str:
    indent = _INDENT * step.depth
    if step.kind == "loop":
        return f"{indent}ForEach {step.node}:"
    if step.kind == "sequence":
        return f"{indent}Sequence {step.node}:"
    if step.kind == "function":
        return f"{indent}{step.node}() {{ … }}"
    return f"{indent}{step.node}"
```

`show_order` 의 `item = QListWidgetItem(_INDENT * step.depth + step.node)` 를:

```python
            item = QListWidgetItem(_format_step(step))
```

(노드명은 `_NODE_ROLE` 데이터로 그대로 저장되므로 네비게이션은 렌더 텍스트와 무관하게 유지된다.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_execution_order_panel.py -q`
Expected: PASS — 기존(`row_text`로 평면 텍스트 확인하던 테스트는 kind 기본값 "node"라 `_INDENT*depth+node`와 동일 — 호환) + 신규

> 주: 기존 `test_depth_rendered_as_indent` 등은 `ExecutionStep("A", 0)`(kind 미지정 → "node")을 쓰므로 `_format_step`이 `indent + node`를 반환 — 기존 기대값과 동일.

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/execution_order_panel.py tests/core/app/test_execution_order_panel.py
git commit -m "feat(app): code-like execution order rendering by node kind (FEAT-5)"
```

---

## Task 4: 통합 검증 — 실제 Orion 파일

**Files:**
- Modify: `tests/core/app/test_phase2c_smoke.py` (또는 신규 `tests/core/app/test_feat5_smoke.py`)

- [ ] **Step 1: 테스트 작성**

`tests/core/app/test_feat5_smoke.py` 생성:

```python
# tests/core/app/test_feat5_smoke.py
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController

RIGVMMODEL = "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"


def test_execution_order_renders_constructs(qtbot, orion_dir):
    window = MainWindow()
    qtbot.addWidget(window)
    controller = AppController(window)
    window.set_open_handler(controller.open_file)
    window.open_path(str(orion_dir / RIGVMMODEL))

    texts = [window.exec_order_panel.row_text(i)
             for i in range(window.exec_order_panel.step_count())]
    # RigVMModel은 Physics 콜랩스 노드를 포함 → 'function' 렌더(N() { … })가 1개 이상
    assert any(t.rstrip().endswith("{ … }") for t in texts)
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/core/app/test_feat5_smoke.py -q`
Expected: PASS — 미처리 케이스가 드러나면 분류 헬퍼(`_classify_kind`)를 보정하고 회귀 테스트 추가 후 재실행

- [ ] **Step 3: 전체 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS — 기존 + 백로그 정리 ①·②a·②b·③ 신규 테스트, 실패 0

- [ ] **Step 4: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: "실행 순서" 탭에 `ForEach …:`·`Sequence …:`·`… () { … }` 코드형 표기

- [ ] **Step 5: Commit**

```bash
git add tests/core/app/test_feat5_smoke.py
git commit -m "test(app): FEAT-5 execution order rendering smoke over real file"
```

---

## Self-Review

**1. 범위 coverage**
- FEAT-5 코드형 렌더링(ForEach/Sequence/function 구별) → Task 1·2·3 ✓
- 실제 파일 검증 → Task 4 ✓
- **범위 밖(명시)**: `name(){}` 콜랩스 드릴다운 네비게이션 — 별도 후속(멀티 그래프 로딩 설계 필요). 본 계획은 코드형 *표시*까지.
- 레이어: 구조 분류는 RigVM 인터프리터(plugin), 분석·뷰는 추상 `Node.kind`/`ExecutionStep.kind`만 소비 — spec §4.1 그래프-타입 무관 원칙 유지.

**2. Placeholder scan** — "TBD/TODO" 없음. `{ … }`·`…`는 UI에 표시되는 실제 문자(말줄임표), 플레이스홀더 아님.

**3. Type consistency**
- `Node.kind: str = "node"` — Task 1 정의, 인터프리터가 설정, `compute_execution_order`가 읽음 일치
- `ExecutionStep.kind: str = "node"` — Task 2 정의, 기본값으로 기존 `ExecutionStep(node, depth)` 호출·동등비교 호환
- `_format_step(step)` — Task 3, `step.kind`/`step.depth`/`step.node` 사용 일치. 네비게이션은 `_NODE_ROLE`(노드명)로 분리돼 렌더 텍스트 변경과 무관
- `_classify_kind`가 `obj.properties`(dict[str,Value])와 `_text` 사용 — `interpreter.py` 기존 패턴과 일치

---

## 완료 후

백로그 정리 ③ 완료 시 — **improver findings 전량 + FEAT-5 처리 완료**.

`docs/superpowers/backlog.md` 잔여:
- `BL1-B1`·`BL1-B2` (정리 batch ① 리뷰 findings) — 차기 정리 batch 또는 ②a/②b 리뷰 findings와 묶어 처리.
- `FEAT-1~4` (`--lenient`·round-trip·resolver·`--json`) — 사용자 결정으로 범위 외, backlog.md에 보존.

이후 improver가 정리 batch ②a/②b/③을 리뷰하면 새 findings가 나올 수 있고, planner가 backlog 규칙대로 누적·후속 batch로 처리한다 (ouroboros 지속).
