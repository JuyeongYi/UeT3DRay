# batch ⑬ g14 — `Pins(N)` 권위 순서 적용 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 인터프리터가 RigVMNode의 `Pins(N)` / `SubPins(N)` 속성을 읽어 node.pins / pin.subpins 순서를 UE 에디터와 동일하게 정렬. **실행 순서 분석·핀 표시·Dispatch ExecuteContext/Completed·Sequence A/B 등 다수 순서 문제 한 번에 해결**.

**Pre-condition:** master 최신.

---

##배경

T3D는 핀을 정의 순서로 직렬화하지만(B, A 같은 임의 순), 같은 노드 properties에 `Pins(0)="path'PinName'"` 형식으로 **권위 순서** 명시:

```
ResolvedFunctionName="RigVMFunction_Sequence::Execute(..., out A, out B)"
Pins(0)="...RigVMPin'ExecuteContext'"
Pins(1)="...RigVMPin'A'"
Pins(2)="...RigVMPin'B'"
```

UE 에디터·실행 엔진은 이 `Pins(N)` 순서로 정렬. 우리도 같은 정렬을 적용하면 실행 순서·시각 모두 정확.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (`_reorder_by_pins_attr` 적용, `_build_pin`이 SubPins 사용) |
| `tests/base/test_pins_n_ordering.py` | 신규 |

---

## Task 1: `Pins(N)` 권위 순서 적용

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Create: `tests/base/test_pins_n_ordering.py`

- [ ] **Step 1: 테스트**

```python
"""g14 — Pins(N) / SubPins(N) 권위 순서 적용."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_pins_n_reorders_node_pins() -> None:
    """Pins(N) 속성이 B,A → A,B 순으로 재정렬."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="Seq"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="ExecuteContext"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Name="Seq"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'ExecuteContext\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '      Pins(2)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    seq = g.node_by_name("Seq")
    pin_names = [p.name for p in seq.pins]
    assert pin_names == ["ExecuteContext", "A", "B"], (
        f"Pins(N) 무시 — pin_names={pin_names}"
    )


def test_pins_n_missing_preserves_original_order() -> None:
    """Pins(N) 속성 없으면 T3D 직렬 순서 유지."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="X"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Y"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    n = g.node_by_name("N")
    # exec 정렬 후 — exec 없으니 원순서
    assert [p.name for p in n.pins] == ["X", "Y"]


def test_pins_n_with_unknown_name_kept_at_end() -> None:
    """Pins(N)에 없는 핀은 권위 핀 뒤에 원순서로."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="C"\n'
        '   End Object\n'
        '   Begin Object Name="N"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    n = g.node_by_name("N")
    # B, A (권위), C (잔여 — 원순서)
    assert [p.name for p in n.pins] == ["B", "A", "C"]


def test_subpins_n_reorders_struct_subpins() -> None:
    """SubPins(N) 속성이 구조체 핀의 자식 순서를 정렬."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Struct"\n'
        '      Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Z"\n'
        '      End Object\n'
        '      Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="X"\n'
        '      End Object\n'
        '      Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Y"\n'
        '      End Object\n'
        '      Begin Object Name="Struct"\n'
        '         SubPins(0)="/Script/RigVMDeveloper.RigVMPin\'X\'"\n'
        '         SubPins(1)="/Script/RigVMDeveloper.RigVMPin\'Y\'"\n'
        '         SubPins(2)="/Script/RigVMDeveloper.RigVMPin\'Z\'"\n'
        '      End Object\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    n = g.node_by_name("N")
    struct_pin = n.pins[0]
    sub_names = [sp.name for sp in struct_pin.subpins]
    assert sub_names == ["X", "Y", "Z"]
```

- [ ] **Step 2: 정렬 헬퍼 + 적용**

`src/t3dgraph/plugins/rigvm/interpreter.py` 상단:

```python
def _extract_pin_name_from_path(path_token: str) -> str | None:
    """Pins(N)/SubPins(N) 값 형식: "...'PinName'" → 'PinName' 추출."""
    import re
    m = re.search(r"'([^']+)'", path_token)
    if m:
        # 마지막 '.' 이후가 핀 이름
        return m.group(1).rsplit(".", 1)[-1]
    return None


def _read_ordered_pin_names(obj: T3DObject, prefix: str) -> list[str] | None:
    """`Pins(N)=...` 또는 `SubPins(N)=...` 속성에서 순서 추출.

    prefix는 "Pins" 또는 "SubPins". 인덱스 순으로 정렬한 핀 이름 리스트 반환.
    속성 없으면 None.
    """
    import re
    pattern = re.compile(rf"^{prefix}\((\d+)\)$")
    indexed: list[tuple[int, str]] = []
    for key, value in obj.properties.items():
        m = pattern.match(key)
        if m is None:
            continue
        text = _text(value)
        if text is None:
            continue
        name = _extract_pin_name_from_path(text)
        if name:
            indexed.append((int(m.group(1)), name))
    if not indexed:
        return None
    indexed.sort(key=lambda iv: iv[0])
    return [name for _, name in indexed]


def _reorder_by_names(pins: list[Pin], names: list[str]) -> list[Pin]:
    """권위 순서(names)대로 pins를 재정렬. names에 없는 핀은 원순서로 뒤에."""
    by_name = {p.name: p for p in pins}
    ordered = [by_name[name] for name in names if name in by_name]
    leftover = [p for p in pins if p.name not in set(names)]
    return ordered + leftover
```

`_build_pin`에 SubPins 적용:

```python
def _build_pin(obj: T3DObject) -> Pin:
    cpp_type = _text(obj.properties.get("CPPType"))
    children_pins = [_build_pin(c) for c in obj.children]
    # SubPins(N) 권위 순서 적용 (없으면 _sort_array_subpins 폴백)
    ordered_names = _read_ordered_pin_names(obj, "SubPins")
    if ordered_names is not None:
        children_pins = _reorder_by_names(children_pins, ordered_names)
    else:
        children_pins = _sort_array_subpins(children_pins)
    return Pin(
        name=obj.name or "",
        cpp_type=cpp_type,
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        is_execution=t.is_execution_cpp_type(cpp_type),
        subpins=children_pins,
        raw=dict(obj.properties),
    )
```

`_add_node`에 Pins 적용 (raw_pins 생성 직후, exec sort 전 또는 후):

```python
raw_pins = [_build_pin(c) for c in obj.children
            if t.is_pin_class(c.cls) or c.cls is None]
# Pins(N) 권위 순서 우선 적용
pin_order = _read_ordered_pin_names(obj, "Pins")
if pin_order is not None:
    raw_pins = _reorder_by_names(raw_pins, pin_order)
# 그 후 exec-first 정렬 (Pins(N) 순서가 이미 적용된 위에)
sorted_pins = _sort_pins_exec_first(raw_pins)
node = Node(..., pins=sorted_pins, ...)
```

- [ ] **Step 3: 실행**

Run: `pytest tests/base/test_pins_n_ordering.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (실행 순서 분석·관련 테스트가 더 정확한 순서 반환).

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

- RigVMFunction_Sequence: 핀 순서 ExecuteContext → A → B
- Dispatch Array Iterator 출력: ExecuteContext(IO) 위, Completed(Output) 아래
- 실행 순서 분석 패널: Sequence의 A → B 순

- [ ] **Step 5: 커밋**

```bash
git add tests/base/test_pins_n_ordering.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "feat(rigvm): apply Pins(N)/SubPins(N) authoritative ordering — UE editor parity"
```

## 완료 후

- 실행 순서 정상화 (중대 문제 해결)
- 핀 표시 순서 UE 에디터와 일치
- Sequence·Dispatch·struct 핀 모두 권위 순서로 보정
