# Slice ι: round-trip `.t3d` 익스포트 (FEAT-2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `T3DDocument`를 텍스트로 직렬화해 round-trip(parse → serialize → parse) 일치를 달성.

**Architecture:** `core/t3d/serializer.py`(신규)에 `serialize_document(doc) -> str` + `serialize_object(obj, indent) -> str` + `serialize_value(v) -> str`. CLI `t3dgraph serialize <file>` 서브커맨드 추가 (stdout 출력).

**Spec ref:** `2026-05-22-t3dgraph-batch-8-heavy-features-design.md` §ι.

---

### Task 1: value 직렬화

**Files:**
- Create: `src/t3dgraph/core/t3d/serializer.py`
- Create: `tests/core/t3d/test_serializer_values.py`

- [ ] **Step 1: Tests**

```python
from t3dgraph.core.t3d.values import (
    Scalar, QuotedString, Struct, ArrayLiteral, parse_value,
)
from t3dgraph.core.t3d.serializer import serialize_value


def test_scalar_round_trip():
    src = "42"
    assert serialize_value(parse_value(src)) == src


def test_quoted_string():
    src = '"hello"'
    assert serialize_value(parse_value(src)) == src


def test_struct():
    src = "(X=1,Y=2,Z=3)"
    assert serialize_value(parse_value(src)) == src


def test_nested_struct():
    src = "(A=(X=1,Y=2),B=10)"
    assert serialize_value(parse_value(src)) == src


def test_array():
    src = "(1,2,3)"
    assert serialize_value(parse_value(src)) == src
```

- [ ] **Step 2: Implement**

```python
"""T3D 값/객체 직렬화 — parse_value의 역."""
from __future__ import annotations
from .values import Value, Scalar, QuotedString, Struct, ArrayLiteral
from .objects import T3DObject
from .document import T3DDocument


def serialize_value(v: Value) -> str:
    if isinstance(v, Scalar):
        return v.text
    if isinstance(v, QuotedString):
        return f'"{v.text}"'
    if isinstance(v, Struct):
        body = ",".join(f"{k}={serialize_value(val)}" for k, val in v.items)
        return f"({body})"
    if isinstance(v, ArrayLiteral):
        return f"({','.join(serialize_value(x) for x in v.items)})"
    raise TypeError(f"unknown value: {type(v).__name__}")
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/t3d/serializer.py tests/core/t3d/test_serializer_values.py
git commit -m "feat(serializer): value round-trip (FEAT-2 prep)"
```

---

### Task 2: object + document 직렬화

**Files:**
- Modify: `src/t3dgraph/core/t3d/serializer.py`
- Create: `tests/core/t3d/test_serializer_round_trip.py`

- [ ] **Step 1: Tests**

```python
from pathlib import Path
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.serializer import serialize_document


def test_round_trip_simple():
    src = (
        'Begin Object Class=/Script/Foo.Bar Name="X"\n'
        '   Prop=1\n'
        '   Begin Object Class=/Script/Foo.Sub Name="Y"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    s = serialize_document(doc)
    doc2 = parse_document(s)
    # 객체 트리 동일성
    assert len(doc.objects) == len(doc2.objects)
    a = doc.objects[0]; b = doc2.objects[0]
    assert a.name == b.name and a.cls == b.cls
    assert len(a.children) == len(b.children)


def test_round_trip_orion_sample():
    p = Path("Orion_WorkStation_Rig_Analysis/"
             "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt")
    doc = parse_document(p.read_text(encoding="utf-8-sig"))
    s = serialize_document(doc)
    doc2 = parse_document(s)
    assert len(doc.objects) == len(doc2.objects)
```

- [ ] **Step 2: Implement**

```python
def serialize_object(obj: T3DObject, indent: int = 0) -> str:
    ind = "   " * indent
    head = f'{ind}Begin Object Class={obj.cls or "?"} Name="{obj.name or ""}"'
    if obj.export_path:
        head += f' ExportPath="{obj.export_path}"'
    head += "\n"
    body_lines = []
    for key, val in obj.properties.items():
        body_lines.append(f'{ind}   {key}={serialize_value(val)}')
    for child in obj.children:
        body_lines.append(serialize_object(child, indent + 1).rstrip("\n"))
    tail = f"{ind}End Object\n"
    return head + "\n".join(body_lines) + ("\n" if body_lines else "") + tail


def serialize_document(doc: T3DDocument) -> str:
    return "".join(serialize_object(o, indent=0) for o in doc.objects)
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/t3d/serializer.py tests/core/t3d/test_serializer_round_trip.py
git commit -m "feat(serializer): document round-trip (FEAT-2)"
```

---

### Task 3: CLI `serialize` 서브커맨드

**Files:**
- Modify: `src/t3dgraph/cli.py`
- Create: `tests/test_cli_serialize.py`

- [ ] **Step 1: Implement + Test**

cli.py에 추가:

```python
p_ser = subs.add_parser("serialize", help="round-trip 직렬화")
p_ser.add_argument("file")
p_ser.add_argument("--lenient", action="store_true")


def _cmd_serialize(args) -> int:
    from .core.t3d.serializer import serialize_document
    from .core.t3d.document import parse_document
    from .core.t3d.encoding import read_t3d_text
    path = Path(args.file)
    if not path.is_file():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2
    try:
        doc = parse_document(read_t3d_text(path))
    except (UnicodeDecodeError, T3DParseError) as e:
        print(f"파싱 실패: {e}", file=sys.stderr)
        return 4 if not args.lenient else 0
    print(serialize_document(doc), end="")
    return 0


# run dispatch에 추가
if args.subcommand == "serialize":
    return _cmd_serialize(args)
```

테스트:
```python
import subprocess, sys
from pathlib import Path


def test_serialize_round_trip(tmp_path):
    src = (
        'Begin Object Class=/Script/Foo.Bar Name="X"\n'
        '   Prop=42\n'
        'End Object\n'
    )
    p = tmp_path / "x.t3d.txt"
    p.write_text(src, encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "serialize", str(p)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0
    assert "Begin Object" in r.stdout
    assert 'Name="X"' in r.stdout
    assert "Prop=42" in r.stdout
```

- [ ] **Step 2: Run·Commit**

```
git add src/t3dgraph/cli.py tests/test_cli_serialize.py
git commit -m "feat(cli): serialize subcommand round-trip (FEAT-2)"
```

---

## 완료 정의

- [ ] Task 1-3 PASS
- [ ] Orion 샘플 1개 이상 round-trip 통과
- [ ] `t3dgraph serialize <file>` 서브커맨드
