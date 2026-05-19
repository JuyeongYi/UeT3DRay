# t3dgraph Phase 1.5 — improvement-review 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** sp-improver의 Phase 1 improvement-review findings 중 A·B 6건(기능 개선 3 + 리팩토링 3)을 수정해 레이어 경계·진단성·견고성을 바로잡는다.

**Architecture:** 기존 t3dgraph Phase 1 구조 유지. 핵심 변경은 B1 — 실행 핀 판정을 RigVM 전용 문자열에서 추상 `Pin.is_execution` 플래그로 옮겨 `core/analysis`의 그래프-타입 무관 원칙(spec §4.1)을 회복한다.

**Tech Stack:** Python 3.11+, stdlib only, pytest. (기존 코드베이스 — 신규 의존성 없음.)

**선행 조건:** Phase 1 완료(master, 52 테스트 통과). 리포: `C:/Users/jylee/source/UeT3DRay`.

**근거 findings:** `C:/Users/jylee/source/UeT3DRay/.improvement-review/findings.md`

---

## File Structure (수정 대상)

| 파일 | 변경 | 관련 finding |
| --- | --- | --- |
| `src/t3dgraph/core/base/graph_model.py` | `Pin`에 `is_execution` 필드 추가 | B1 |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | `_build_pin`이 `is_execution` 설정 | B1 |
| `src/t3dgraph/core/analysis/flow.py` | `_exec_pin_index`가 추상 플래그 사용 / `_reachable` deque화 | B1, B3 |
| `src/t3dgraph/core/analysis/execution_order.py` | `flow` 인자 수용 / 반복형 순회 | B2, B3 |
| `src/t3dgraph/cli.py` | 사전계산 flow 전달 / 인코딩 견고화 / external_refs 출력 | B2, A2, A3 |
| `src/t3dgraph/core/t3d/objects.py` | 값 파싱 에러를 `T3DParseError`로 감쌈 | A1 |

범위 밖(백로그): `--lenient` 플래그, C 아이디어 3건(round-trip·에셋 resolver·`--json`). Phase 2(뷰어)와 함께 또는 별도 후속.

---

## Task 1: B1 — 실행 핀을 추상 플래그로 (레이어 경계 회복)

`core/analysis/flow.py`가 RigVM 전용 문자열 `"FRigVMExecuteContext"`를 직접 비교한다(spec §4.1 위반). 인터프리터가 실행 핀을 `Pin.is_execution`으로 표시하고, analysis는 그 추상 플래그만 본다.

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py:28-36`
- Modify: `src/t3dgraph/core/analysis/flow.py:29-41`
- Modify: `tests/core/analysis/test_flow.py`
- Modify: `tests/core/analysis/test_execution_order.py`
- Modify: `tests/plugins/rigvm/test_interpreter.py`
- Modify: `tests/core/base/test_graph_model.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/analysis/test_flow.py` 에 추가 (그래프-타입 무관 검증 — 실행 핀을 `is_execution=True`로 표시하되 `cpp_type`은 RigVM 문자열이 아님):

```python
def test_flow_uses_abstract_is_execution_not_rigvm_string():
    a = Node(name="A", cls="X",
             pins=[Pin(name="O", cpp_type="SomeOtherExecType", direction="Output", is_execution=True)])
    b = Node(name="B", cls="X",
             pins=[Pin(name="I", cpp_type="SomeOtherExecType", direction="Input", is_execution=True)])
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")]))
    assert r.execution_edges == [("A", "B")]


def test_flow_ignores_rigvm_string_when_flag_false():
    # is_execution=False 이면 cpp_type이 RigVM 문자열이어도 실행 엣지 아님
    a = Node(name="A", cls="X",
             pins=[Pin(name="O", cpp_type="FRigVMExecuteContext", direction="Output", is_execution=False)])
    b = Node(name="B", cls="X",
             pins=[Pin(name="I", cpp_type="FRigVMExecuteContext", direction="Input", is_execution=False)])
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")]))
    assert r.execution_edges == []
```

`tests/plugins/rigvm/test_interpreter.py` 에 추가 (인터프리터가 플래그 설정):

```python
def test_interpreter_marks_execution_pins():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    exec_pin = g.node_by_name("A").pins[0]
    assert exec_pin.cpp_type == "FRigVMExecuteContext"
    assert exec_pin.is_execution is True


def test_interpreter_non_execution_pin_flag_false():
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="V"\n'
        '   End Object\n'
        'End Object\n'
        'Begin Object Name="A"\n'
        '   Begin Object Name="V"\n'
        '      CPPType="double"\n'
        '   End Object\n'
        'End Object\n'
    )
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.node_by_name("A").pins[0].is_execution is False
```

`tests/core/base/test_graph_model.py` 에 추가:

```python
def test_pin_is_execution_defaults_false():
    assert Pin(name="X", cpp_type="double", direction="Input").is_execution is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/analysis/test_flow.py tests/plugins/rigvm/test_interpreter.py tests/core/base/test_graph_model.py -q`
Expected: FAIL — `Pin`에 `is_execution` 인자가 없어 `TypeError: __init__() got an unexpected keyword argument 'is_execution'`

- [ ] **Step 3: 구현**

`core/base/graph_model.py` — `Pin` 데이터클래스에 `is_execution` 필드 추가 (`default_value` 다음, `subpins` 앞):

```python
@dataclass
class Pin:
    name: str
    cpp_type: str | None
    direction: str | None
    default_value: str | None = None
    is_execution: bool = False
    subpins: list["Pin"] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
```

`plugins/rigvm/interpreter.py` — `_build_pin` 이 `cpp_type`을 먼저 구해 `is_execution`에 사용:

```python
def _build_pin(obj: T3DObject) -> Pin:
    cpp_type = _text(obj.properties.get("CPPType"))
    return Pin(
        name=obj.name or "",
        cpp_type=cpp_type,
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        is_execution=t.is_execution_cpp_type(cpp_type),
        subpins=[_build_pin(c) for c in obj.children],
        raw=dict(obj.properties),
    )
```

`core/analysis/flow.py` — `_exec_pin_index` 의 `walk`가 추상 플래그 사용 (RigVM 문자열 제거):

```python
def _exec_pin_index(graph: GraphModel) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()

    def walk(node_name: str, pin: Pin) -> None:
        if pin.is_execution:
            out.add((node_name, pin.name))
        for sp in pin.subpins:
            walk(node_name, sp)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p)
    return out
```

기존 테스트 헬퍼도 갱신 — `tests/core/analysis/test_flow.py` 의 `_exec_pin`:

```python
def _exec_pin(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=direction, is_execution=True)
```

`tests/core/analysis/test_execution_order.py` 의 `_ep`:

```python
def _ep(name, d):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=d, is_execution=True)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/analysis tests/plugins/rigvm tests/core/base -q`
Expected: PASS (기존 + 신규 테스트 전부)

추가 확인 — `flow.py`에 RigVM 문자열이 남지 않았는지:
Run: `python -c "import pathlib; assert 'FRigVMExecuteContext' not in pathlib.Path('src/t3dgraph/core/analysis/flow.py').read_text(encoding='utf-8'); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/base/graph_model.py src/t3dgraph/plugins/rigvm/interpreter.py src/t3dgraph/core/analysis/flow.py tests/core/analysis/test_flow.py tests/core/analysis/test_execution_order.py tests/plugins/rigvm/test_interpreter.py tests/core/base/test_graph_model.py
git commit -m "refactor(analysis): use abstract Pin.is_execution instead of RigVM string (B1)"
```

---

## Task 2: B2 — 중복 `analyze_flow` 제거

CLI가 `analyze_flow`를 호출한 뒤 `compute_execution_order`가 내부에서 또 호출한다. `compute_execution_order`가 사전계산된 `FlowResult`를 받게 한다.

**Files:**
- Modify: `src/t3dgraph/core/analysis/execution_order.py:5,14-15`
- Modify: `src/t3dgraph/cli.py:32`
- Modify: `tests/core/analysis/test_execution_order.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/analysis/test_execution_order.py` 에 추가:

```python
def test_compute_with_precomputed_flow_matches():
    from t3dgraph.core.analysis.flow import analyze_flow
    a = _n("A", _ep("O", "Output"))
    b = _n("B", _ep("I", "Input"))
    g = GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")])
    flow = analyze_flow(g)
    assert compute_execution_order(g, flow=flow) == compute_execution_order(g)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/analysis/test_execution_order.py::test_compute_with_precomputed_flow_matches -q`
Expected: FAIL — `TypeError: compute_execution_order() got an unexpected keyword argument 'flow'`

- [ ] **Step 3: 구현**

`core/analysis/execution_order.py` — import에 `FlowResult` 추가, 시그니처에 `flow` 옵션:

```python
from .flow import analyze_flow, FlowResult
```

```python
def compute_execution_order(
    graph: GraphModel, flow: FlowResult | None = None
) -> list[ExecutionStep]:
    if flow is None:
        flow = analyze_flow(graph)
    out_edges: dict[str, list[str]] = {}
    ...  # 이하 기존 본문 동일 (Task 3에서 순회부 교체)
```

`cli.py:32` — 이미 계산한 `flow`를 전달:

```python
    order = compute_execution_order(graph, flow=flow)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/analysis tests/test_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/analysis/execution_order.py src/t3dgraph/cli.py tests/core/analysis/test_execution_order.py
git commit -m "perf(analysis): compute_execution_order accepts precomputed FlowResult (B2)"
```

---

## Task 3: B3 — 순회 견고화 (deque + 반복형)

`flow._reachable`의 `list.pop(0)`는 O(n²)이고, `compute_execution_order`의 재귀 `walk`는 긴 체인에서 `RecursionError` 위험이 있다(실제 RigVMModel 픽스처는 8945줄 규모).

**Files:**
- Modify: `src/t3dgraph/core/analysis/flow.py:1-4,77-86`
- Modify: `src/t3dgraph/core/analysis/execution_order.py:26-41`
- Modify: `tests/core/analysis/test_execution_order.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/analysis/test_execution_order.py` 에 추가 (깊은 선형 체인 — 재귀 구현이면 `RecursionError`):

```python
def test_deep_chain_no_recursion_error():
    nodes = [_n(f"N{i}", _ep("I", "Input"), _ep("O", "Output")) for i in range(5000)]
    links = [Link(f"N{i}.O", f"N{i+1}.I") for i in range(4999)]
    order = compute_execution_order(GraphModel(nodes=nodes, links=links))
    assert len(order) == 5000
    assert order[0].node == "N0"
    assert order[-1].node == "N4999"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/analysis/test_execution_order.py::test_deep_chain_no_recursion_error -q`
Expected: FAIL — `RecursionError: maximum recursion depth exceeded`

- [ ] **Step 3: 구현**

`core/analysis/flow.py` — 맨 위 import에 `deque` 추가:

```python
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin
```

`_reachable` 를 `deque` 기반으로 (파일 하단 함수 전체 교체):

```python
def _reachable(start: str, out_edges: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    queue: deque[str] = deque(out_edges.get(start, []))
    while queue:
        n = queue.popleft()
        if n in seen:
            continue
        seen.add(n)
        queue.extend(out_edges.get(n, []))
    return sorted(seen)
```

`core/analysis/execution_order.py` — 재귀 `walk`를 명시적 스택 반복형으로 교체. `compute_execution_order` 본문의 `steps`/`visited`/`walk`/`for e in entries` 부분(26~41행)을 다음으로 대체:

```python
    steps: list[ExecutionStep] = []
    visited: set[str] = set()
    for entry in entries:
        stack: list[tuple[str, int]] = [(entry, 0)]
        while stack:
            node, depth = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            steps.append(ExecutionStep(node=node, depth=depth))
            succ = out_edges.get(node, [])
            child_depth = depth if len(succ) <= 1 else depth + 1
            for nxt in reversed(succ):          # 역순 push → 원래 순서로 pop
                stack.append((nxt, child_depth))
    return steps
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/analysis -q`
Expected: PASS — 신규 깊은 체인 테스트 + 기존 `test_linear_order`·`test_branch_increases_depth` 등 순서·깊이 테스트 모두 통과

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/analysis/flow.py src/t3dgraph/core/analysis/execution_order.py tests/core/analysis/test_execution_order.py
git commit -m "perf(analysis): deque BFS and iterative traversal, no recursion limit (B3)"
```

---

## Task 4: A1 — 값 파싱 에러에 파일 줄·열 보존

`objects.py`가 `parse_value` 호출 중 `ValueParseError`가 나면 그대로 전파한다. 파일 줄 번호를 잃어 spec §8의 "정확한 위치 보고"가 안 된다. `T3DParseError`로 감싼다.

**Files:**
- Modify: `src/t3dgraph/core/t3d/objects.py:6,62-65`
- Modify: `tests/core/t3d/test_objects.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/t3d/test_objects.py` 에 추가:

```python
def test_bad_value_wrapped_with_file_line():
    import pytest
    from t3dgraph.core.t3d.objects import T3DParseError
    # 2번째 줄의 닫히지 않은 구조체 → values.py가 ValueParseError
    src = 'Begin Object Name="N"\n   Bad=(X=1\nEnd Object\n'
    with pytest.raises(T3DParseError) as ei:
        parse_objects(src)
    assert ei.value.line == 2
    assert ei.value.col > 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_objects.py::test_bad_value_wrapped_with_file_line -q`
Expected: FAIL — `ValueParseError`가 전파되어 `pytest.raises(T3DParseError)` 불만족

- [ ] **Step 3: 구현**

`core/t3d/objects.py` — import에 `ValueParseError` 추가:

```python
from .values import Value, parse_value, ValueParseError
```

`parse_block` 내부의 `elif "=" in ln.text:` 블록(62~65행)을 다음으로 교체:

```python
            elif "=" in ln.text:
                key, _, raw = ln.text.partition("=")
                try:
                    value = parse_value(raw.strip())
                except ValueParseError as e:
                    col = ln.indent + len(key) + 1   # 값이 시작하는 열
                    raise T3DParseError(ln.number, col, f"속성값 파싱 실패: {e}") from e
                obj.properties[key.strip()] = value
                pos += 1
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d -q`
Expected: PASS — 신규 테스트 + 기존 객체 파서 테스트 전부

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/objects.py tests/core/t3d/test_objects.py
git commit -m "fix(t3d): wrap value parse errors with file line/col (A1)"
```

---

## Task 5: A2 — CLI 파일 인코딩 견고화

`cli.py`가 `encoding="utf-8"`을 하드코딩해 BOM·UTF-16 익스포트 파일에서 크래시한다.

**Files:**
- Modify: `src/t3dgraph/cli.py:5,22`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_cli.py` 에 추가:

```python
def _sample(orion_dir):
    return (orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
            ).read_text(encoding="utf-8")


def test_cli_handles_utf8_bom(tmp_path, orion_dir):
    f = tmp_path / "bom.t3d.txt"
    f.write_bytes(b"\xef\xbb\xbf" + _sample(orion_dir).encode("utf-8"))
    assert run([str(f)]) == 0


def test_cli_handles_utf16(tmp_path, orion_dir):
    f = tmp_path / "u16.t3d.txt"
    f.write_bytes(_sample(orion_dir).encode("utf-16"))
    assert run([str(f)]) == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_cli.py::test_cli_handles_utf8_bom tests/test_cli.py::test_cli_handles_utf16 -q`
Expected: FAIL — BOM 파일은 exit 3(객체 미검출), UTF-16은 `UnicodeDecodeError`

- [ ] **Step 3: 구현**

`cli.py` — import에 표준 라이브러리만 그대로. 헬퍼 추가(`run` 함수 위, import 블록 다음):

```python
def _read_text(path: Path) -> str:
    """BOM·UTF-16 익스포트도 처리하는 견고한 텍스트 읽기."""
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")   # utf-8-sig: BOM 있으면 제거, 없으면 utf-8
```

`run` 함수의 22행(`doc = parse_document(path.read_text(encoding="utf-8"))`)을 교체:

```python
    try:
        doc = parse_document(_read_text(path))
    except UnicodeDecodeError as e:
        print(f"파일 인코딩을 해석할 수 없습니다: {path} ({e})", file=sys.stderr)
        return 2
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/cli.py tests/test_cli.py
git commit -m "fix(cli): robust file encoding (BOM/UTF-16) handling (A2)"
```

---

## Task 6: A3 — CLI 요약에 external_refs 추가

인터프리터는 미해결 외부 참조를 `external_refs`로 수집하지만 CLI 요약엔 빠져 있다.

**Files:**
- Modify: `src/t3dgraph/cli.py:37`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_cli.py` 에 추가:

```python
def test_cli_summary_includes_external_refs(orion_dir, capsys):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    assert run([str(f)]) == 0
    assert "external refs:" in capsys.readouterr().out
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_cli.py::test_cli_summary_includes_external_refs -q`
Expected: FAIL — 요약에 `external refs:` 줄 없음

- [ ] **Step 3: 구현**

`cli.py` — `variable refs` 출력 줄(37행) 바로 다음에 한 줄 추가:

```python
    print(f"variable refs: {len(graph.variable_refs)}")
    print(f"external refs: {len(graph.external_refs)}")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/cli.py tests/test_cli.py
git commit -m "fix(cli): include external_refs count in summary (A3)"
```

---

## Task 7: 전체 회귀 검증

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS — Phase 1 기존 52개 + Phase 1.5 신규 테스트(약 9개) 모두 통과, 실패 0

- [ ] **Step 2: CLI 스모크 — 실제 파일**

Run: `python -m t3dgraph.cli tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 요약 출력에 `graph type: rigvm`, `external refs:` 줄 포함, exit 0

(별도 커밋 없음 — 검증 전용 태스크.)

---

## Self-Review

**1. Findings coverage**
- A1 값 파싱 에러 위치 → Task 4 ✓
- A2 CLI 인코딩 → Task 5 ✓
- A3 CLI external_refs → Task 6 ✓
- B1 RigVM 문자열 하드코딩 → Task 1 ✓ (flow.py에 문자열 잔존 0 검증 포함)
- B2 중복 `analyze_flow` → Task 2 ✓
- B3 순회 견고화(deque + 재귀 제거) → Task 3 ✓
- C 아이디어 3건·`--lenient` → 의도적 범위 밖(백로그), 본 계획 불포함 — 사용자 결정(Phase 1.5 우선)

**2. Placeholder scan** — "TBD/TODO" 없음. 모든 코드 단계에 실제 코드. Task 2 Step 3의 `... # 이하 기존 본문 동일`은 플레이스홀더가 아니라 "이 영역은 Task 3에서 교체되며 Task 2에서는 미변경"임을 명시한 것 — Task 3가 해당 본문을 완전한 코드로 교체한다.

**3. Type consistency**
- `Pin.is_execution: bool` — Task 1에서 정의, Task 1의 interpreter·flow·테스트 헬퍼에서 일관 사용
- `compute_execution_order(graph, flow=None)` — Task 2에서 시그니처 변경, Task 3에서 본문 교체, cli.py(Task 2)에서 `flow=flow`로 호출 — 일관
- `FlowResult` — Task 2에서 execution_order.py로 import 추가, Task 3에서 그대로 사용
- 태스크 간 파일 중복: `flow.py`(Task 1,3) / `execution_order.py`(Task 2,3) / `cli.py`(Task 2,5,6) — 순차 실행 전제. 각 태스크의 modify 대상 영역이 겹치지 않음(Task 2는 시그니처+import, Task 3은 본문 순회부) — 순서대로 적용 시 충돌 없음.

---

## 다음 단계

Phase 1.5 완료 후:
- **Phase 2** — PySide6 뷰어 (planner가 별도 계획 작성). spec §4·5.6·7 기반.
- **백로그** — `--lenient` 파싱 플래그, round-trip `.t3d` 익스포트, 에셋 단위 resolver, CLI `--json` 출력. Phase 2와 함께 또는 후속 iteration에서 우선순위 결정.
