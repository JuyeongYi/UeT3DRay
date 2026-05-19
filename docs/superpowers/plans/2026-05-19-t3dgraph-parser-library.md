# t3dgraph 파서·분석 라이브러리 (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UE T3D 텍스트(`.t3d`)를 무손실로 파싱하고 RigVM 그래프로 해석한 뒤 실행 흐름을 분석하는, Qt 의존성 없는 Python 라이브러리 + CLI를 만든다.

**Architecture:** 레이어드 + 플러그인 우선. `core/t3d`(그래프 무관 구조 파서) → `core/base`(추상 계약) → `plugins/rigvm`(구체 해석) → `core/analysis`(그래프 무관 분석). 전 구간 순수 Python(stdlib만). 이 Phase가 곧 산출물 #1 라이브러리.

**Tech Stack:** Python 3.11+, stdlib only(`tomllib`·`dataclasses`·`argparse`), pytest. PySide6는 Phase 2.

**Spec:** `docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md`

---

## File Structure (Phase 1)

| 파일 | 책임 |
| --- | --- |
| `pyproject.toml` | 패키지 메타·src-layout·pytest 설정 |
| `src/t3dgraph/core/t3d/tokenizer.py` | `.t3d` 텍스트 → 토큰 스트림 |
| `src/t3dgraph/core/t3d/values.py` | 재귀 하강 값 파서 (스칼라·구조체·중첩·배열·참조) |
| `src/t3dgraph/core/t3d/objects.py` | `Begin/End Object` → 객체 트리 |
| `src/t3dgraph/core/t3d/document.py` | `T3DDocument` + 2단계(선언/정의) 병합 |
| `src/t3dgraph/core/base/graph_model.py` | 추상 `GraphModel/Node/Pin/Link` |
| `src/t3dgraph/core/base/interpreter.py` | `AbstractGraphInterpreter` |
| `src/t3dgraph/core/base/plugin.py` | `GraphTypePlugin` 계약 |
| `src/t3dgraph/core/registry.py` | 플러그인 등록·클래스→인터프리터 디스패치 |
| `src/t3dgraph/plugins/rigvm/types.py` | RigVM 전용 노드/핀 분류 |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | `RigVMGraphInterpreter` |
| `src/t3dgraph/plugins/rigvm/__init__.py` | 플러그인 self-register |
| `src/t3dgraph/core/analysis/flow.py` | 실행 그래프·fan-in 수렴점 |
| `src/t3dgraph/core/analysis/execution_order.py` | 구조화 실행 순서 |
| `src/t3dgraph/cli.py` | 파싱·분석 CLI |
| `config/graph_types.toml` | 그래프 타입 매핑 |
| `tests/...` | 각 모듈 단위 테스트 + 통합 테스트 |

테스트 픽스처: 실제 데이터 `C:\Users\jylee\source\UeT3DRay\Orion_WorkStation_Rig_Analysis\*.t3d.txt` 11개를 `tests/fixtures/orion/`로 복사해 사용한다.

---

## Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `pyproject.toml`
- Create: `src/t3dgraph/__init__.py`, `src/t3dgraph/core/__init__.py`, `src/t3dgraph/core/t3d/__init__.py`, `src/t3dgraph/core/base/__init__.py`, `src/t3dgraph/core/analysis/__init__.py`, `src/t3dgraph/plugins/__init__.py`, `src/t3dgraph/plugins/rigvm/__init__.py` (빈 파일, 내용은 Task 11)
- Create: `tests/__init__.py`, `tests/conftest.py`
- Create: `config/graph_types.toml` (Task 11에서 채움 — 지금은 빈 헤더)

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "t3dgraph"
version = "0.1.0"
description = "UE T3D graph parser, interpreter and analysis library"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
t3dgraph = "t3dgraph.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: 패키지 디렉터리와 `__init__.py` 생성**

위 Files 목록의 모든 `__init__.py`를 빈 파일로 생성. `config/graph_types.toml`은 한 줄 주석만:

```toml
# graph type → interpreter 매핑. Task 11에서 채움.
```

- [ ] **Step 3: `tests/conftest.py` — 픽스처 경로 헬퍼**

```python
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ORION = FIXTURES / "orion"


@pytest.fixture
def orion_dir() -> Path:
    """11개 실제 .t3d.txt 파일이 있는 디렉터리."""
    return ORION
```

- [ ] **Step 4: Orion 픽스처 복사 + 검증 실행**

Run:
```bash
mkdir -p tests/fixtures/orion
cp "C:/Users/jylee/source/UeT3DRay/Orion_WorkStation_Rig_Analysis/"*.t3d.txt tests/fixtures/orion/
python -m pytest -q
```
Expected: `no tests ran` (테스트 0개, 에러 없음). `ls tests/fixtures/orion` 시 11개 파일.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src tests config
git commit -m "chore: scaffold t3dgraph package and pytest setup"
```

---

## Task 2: T3D 토크나이저 — `core/t3d/tokenizer.py`

T3D를 토큰 단위로 분해한다. 토큰: `BEGIN`, `END`, `OBJECT`, `IDENT`(키/식별자), `EQUALS`, `STRING`(따옴표), `LPAREN`/`RPAREN`, `COMMA`, `VALUE`(따옴표 없는 원시 값 조각), `NEWLINE`, `EOF`. 단순화를 위해 토크나이저는 **줄 단위**로 동작한다: 각 줄을 `(indent, raw_line)` 로 내보내고, 값 레벨의 세부 토큰화는 `values.py`가 담당한다.

**Files:**
- Create: `src/t3dgraph/core/t3d/tokenizer.py`
- Test: `tests/core/t3d/test_tokenizer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/t3d/test_tokenizer.py
from t3dgraph.core.t3d.tokenizer import tokenize_lines, Line


def test_blank_and_indent():
    src = "Begin Object Class=A Name=\"X\"\n   Direction=Output\nEnd Object\n"
    lines = tokenize_lines(src)
    assert [l.indent for l in lines] == [0, 3, 0]
    assert lines[0].text == 'Begin Object Class=A Name="X"'
    assert lines[1].text == "Direction=Output"
    assert lines[2].text == "End Object"


def test_line_numbers_are_1_based():
    lines = tokenize_lines("a\nb\n")
    assert [l.number for l in lines] == [1, 2]


def test_trailing_blank_lines_skipped():
    lines = tokenize_lines("a\n\n  \n")
    assert [l.text for l in lines] == ["a"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_tokenizer.py -q`
Expected: FAIL — `ModuleNotFoundError: t3dgraph.core.t3d.tokenizer`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/t3d/tokenizer.py
"""T3D 텍스트를 들여쓰기를 보존한 줄 단위로 분해한다."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    number: int   # 1-based 원본 줄 번호
    indent: int   # 선행 공백 수
    text: str     # strip된 줄 내용


def tokenize_lines(src: str) -> list[Line]:
    out: list[Line] = []
    for i, raw in enumerate(src.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        indent = len(raw) - len(raw.lstrip())
        out.append(Line(number=i, indent=indent, text=stripped))
    return out
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d/test_tokenizer.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/tokenizer.py tests/core/t3d/test_tokenizer.py
git commit -m "feat(t3d): line tokenizer preserving indentation"
```

---

## Task 3: T3D 값 파서 — `core/t3d/values.py`

`Key=Value` 의 우변을 재귀적으로 파싱한다. 값 종류: `Scalar`(원시 토큰), `QuotedString`, `Struct`(`(K=V,K=V)`), `ArrayLiteral`(`(v,v)` 또는 빈 `()`). 빈 `()` 는 `Struct(items=[])` 로 통일한다. 구조체와 배열 구분: `(` 안 첫 요소가 `IDENT=` 형태면 `Struct`, 아니면 `ArrayLiteral`.

**Files:**
- Create: `src/t3dgraph/core/t3d/values.py`
- Test: `tests/core/t3d/test_values.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/t3d/test_values.py
from t3dgraph.core.t3d.values import parse_value, Scalar, QuotedString, Struct, ArrayLiteral


def test_scalar():
    assert parse_value("Output") == Scalar("Output")


def test_quoted_string():
    assert parse_value('"hello world"') == QuotedString("hello world")


def test_struct():
    v = parse_value("(X=1.0,Y=2.0)")
    assert v == Struct([("X", Scalar("1.0")), ("Y", Scalar("2.0"))])


def test_nested_struct():
    v = parse_value("(A=(X=0),B=1)")
    assert v == Struct([("A", Struct([("X", Scalar("0"))])), ("B", Scalar("1"))])


def test_empty_paren_is_empty_struct():
    assert parse_value("()") == Struct([])


def test_array_literal():
    assert parse_value("(1,2,3)") == ArrayLiteral([Scalar("1"), Scalar("2"), Scalar("3")])


def test_quoted_string_with_comma_and_parens():
    v = parse_value('"/Script/X.Y\'/Game/A.B:C\'"')
    assert isinstance(v, QuotedString)
    assert v.text == "/Script/X.Y'/Game/A.B:C'"


def test_struct_value_can_be_quoted():
    v = parse_value('(Name="a,b",Count=2)')
    assert v == Struct([("Name", QuotedString("a,b")), ("Count", Scalar("2"))])
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_values.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/t3d/values.py
"""T3D 속성값의 재귀 하강 파서."""
from __future__ import annotations
from dataclasses import dataclass


class Value:
    """모든 값 노드의 베이스."""


@dataclass(frozen=True)
class Scalar(Value):
    text: str


@dataclass(frozen=True)
class QuotedString(Value):
    text: str


@dataclass(frozen=True)
class Struct(Value):
    items: list[tuple[str, "Value"]]


@dataclass(frozen=True)
class ArrayLiteral(Value):
    items: list["Value"]


class ValueParseError(ValueError):
    pass


def parse_value(text: str) -> Value:
    p = _Parser(text)
    v = p.parse()
    p.skip_ws()
    if not p.at_end():
        raise ValueParseError(f"값 뒤에 남은 입력: {text!r} (pos {p.i})")
    return v


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0

    def at_end(self) -> bool:
        return self.i >= len(self.s)

    def skip_ws(self) -> None:
        while not self.at_end() and self.s[self.i] in " \t":
            self.i += 1

    def parse(self) -> Value:
        self.skip_ws()
        if self.at_end():
            return Scalar("")
        c = self.s[self.i]
        if c == '"':
            return self._quoted()
        if c == "(":
            return self._paren()
        return self._scalar()

    def _quoted(self) -> QuotedString:
        assert self.s[self.i] == '"'
        self.i += 1
        buf = []
        while not self.at_end():
            c = self.s[self.i]
            if c == "\\" and self.i + 1 < len(self.s):
                buf.append(self.s[self.i + 1])
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                return QuotedString("".join(buf))
            buf.append(c)
            self.i += 1
        raise ValueParseError("닫히지 않은 따옴표 문자열")

    def _scalar(self) -> Scalar:
        start = self.i
        while not self.at_end() and self.s[self.i] not in ",()":
            self.i += 1
        return Scalar(self.s[start:self.i].strip())

    def _paren(self) -> Value:
        assert self.s[self.i] == "("
        self.i += 1
        self.skip_ws()
        if not self.at_end() and self.s[self.i] == ")":
            self.i += 1
            return Struct([])  # 빈 () = 빈 구조체
        # 구조체 vs 배열: 첫 요소가 IDENT= 인지 미리 본다
        if self._looks_like_struct():
            return self._struct_body()
        return self._array_body()

    def _looks_like_struct(self) -> bool:
        j = self.i
        # IDENT
        while j < len(self.s) and (self.s[j].isalnum() or self.s[j] in "_"):
            j += 1
        while j < len(self.s) and self.s[j] in " \t":
            j += 1
        return j < len(self.s) and self.s[j] == "="

    def _read_ident(self) -> str:
        start = self.i
        while not self.at_end() and (self.s[self.i].isalnum() or self.s[self.i] == "_"):
            self.i += 1
        return self.s[start:self.i]

    def _struct_body(self) -> Struct:
        items: list[tuple[str, Value]] = []
        while True:
            self.skip_ws()
            key = self._read_ident()
            self.skip_ws()
            if self.at_end() or self.s[self.i] != "=":
                raise ValueParseError(f"구조체 키 뒤 '=' 기대 (pos {self.i})")
            self.i += 1
            val = self.parse()
            items.append((key, val))
            self.skip_ws()
            if self.at_end():
                raise ValueParseError("닫히지 않은 구조체")
            if self.s[self.i] == ",":
                self.i += 1
                continue
            if self.s[self.i] == ")":
                self.i += 1
                return Struct(items)
            raise ValueParseError(f"구조체에서 ',' 또는 ')' 기대 (pos {self.i})")

    def _array_body(self) -> ArrayLiteral:
        items: list[Value] = []
        while True:
            val = self.parse()
            items.append(val)
            self.skip_ws()
            if self.at_end():
                raise ValueParseError("닫히지 않은 배열")
            if self.s[self.i] == ",":
                self.i += 1
                continue
            if self.s[self.i] == ")":
                self.i += 1
                return ArrayLiteral(items)
            raise ValueParseError(f"배열에서 ',' 또는 ')' 기대 (pos {self.i})")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d/test_values.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/values.py tests/core/t3d/test_values.py
git commit -m "feat(t3d): recursive-descent value parser"
```

---

## Task 4: T3D 객체 트리 파서 — `core/t3d/objects.py`

`Begin Object … End Object` 중첩 트리와 `Key=Value` 속성을 파싱한다. 인덱스 프로퍼티(`Pins(0)=...`)는 키를 `Pins(0)` 그대로 보존(무손실). 헤더의 `Class=`/`Name=`/`ExportPath=` 는 별도 필드로 추출하되 원본도 보존.

**Files:**
- Create: `src/t3dgraph/core/t3d/objects.py`
- Test: `tests/core/t3d/test_objects.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/t3d/test_objects.py
from t3dgraph.core.t3d.objects import parse_objects
from t3dgraph.core.t3d.values import Scalar, QuotedString

SAMPLE = (
    'Begin Object Class=/Script/X.Node Name="N1"\n'
    '   Begin Object Class=/Script/X.Pin Name="P1"\n'
    '   End Object\n'
    '   Direction=Output\n'
    '   Pins(0)="/Script/X.Pin\'P1\'"\n'
    'End Object\n'
)


def test_top_level_object():
    objs = parse_objects(SAMPLE)
    assert len(objs) == 1
    assert objs[0].cls == "/Script/X.Node"
    assert objs[0].name == "N1"


def test_nested_child():
    objs = parse_objects(SAMPLE)
    assert len(objs[0].children) == 1
    assert objs[0].children[0].name == "P1"


def test_properties_indexed_key_preserved():
    obj = parse_objects(SAMPLE)[0]
    assert obj.properties["Direction"] == Scalar("Output")
    assert isinstance(obj.properties["Pins(0)"], QuotedString)


def test_declaration_block_has_no_class_optional():
    src = 'Begin Object Name="N1"\n   Direction=Input\nEnd Object\n'
    obj = parse_objects(src)[0]
    assert obj.cls is None
    assert obj.name == "N1"


def test_unbalanced_raises():
    import pytest
    from t3dgraph.core.t3d.objects import T3DParseError
    with pytest.raises(T3DParseError):
        parse_objects('Begin Object Name="N1"\n')
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_objects.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/t3d/objects.py
"""Begin/End Object 트리와 Key=Value 속성 파싱."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from .tokenizer import tokenize_lines, Line
from .values import Value, parse_value


class T3DParseError(Exception):
    def __init__(self, line: int, col: int, message: str):
        self.line, self.col = line, col
        super().__init__(f"line {line}:{col}: {message}")


@dataclass
class T3DObject:
    cls: str | None                       # Class= 값 (정의 블록엔 없을 수 있음)
    name: str | None                      # Name= 값
    export_path: str | None               # ExportPath= 값
    header_raw: str                       # 원본 헤더 줄 (무손실)
    properties: dict[str, Value] = field(default_factory=dict)
    children: list["T3DObject"] = field(default_factory=list)
    line: int = 0                         # Begin 줄 번호


_HEADER_ATTR = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def _header_attrs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _HEADER_ATTR.finditer(text):
        key, val = m.group(1), m.group(2)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        out[key] = val
    return out


def parse_objects(src: str) -> list[T3DObject]:
    lines = tokenize_lines(src)
    pos = 0

    def parse_block(open_line: Line) -> tuple[T3DObject, int]:
        nonlocal pos
        attrs = _header_attrs(open_line.text)
        obj = T3DObject(
            cls=attrs.get("Class"),
            name=attrs.get("Name"),
            export_path=attrs.get("ExportPath"),
            header_raw=open_line.text,
            line=open_line.number,
        )
        while pos < len(lines):
            ln = lines[pos]
            if ln.text.startswith("Begin Object"):
                pos += 1
                child, _ = parse_block(ln)
                obj.children.append(child)
            elif ln.text == "End Object":
                pos += 1
                return obj, pos
            elif "=" in ln.text:
                key, _, raw = ln.text.partition("=")
                obj.properties[key.strip()] = parse_value(raw.strip())
                pos += 1
            else:
                pos += 1  # 알 수 없는 줄은 무손실 차원에서 무시하지 않고…
        raise T3DParseError(open_line.number, 0, "End Object 없이 입력 종료")

    objs: list[T3DObject] = []
    while pos < len(lines):
        ln = lines[pos]
        if ln.text.startswith("Begin Object"):
            pos += 1
            obj, pos = parse_block(ln)
            objs.append(obj)
        else:
            pos += 1
    return objs
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d/test_objects.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/objects.py tests/core/t3d/test_objects.py
git commit -m "feat(t3d): Begin/End Object tree parser"
```

---

## Task 5: T3DDocument + 2단계 병합 — `core/t3d/document.py`

같은 형제 레벨에서 같은 `Name`을 가진 객체가 ① 선언 블록(`Class=` 있음, 자식만)·② 정의 블록(`Class=` 없음, 속성 채움) 두 번 등장한다. 이를 하나로 병합한다: `cls`는 선언 블록에서, `properties`는 정의 블록에서, `children`은 같은 이름끼리 재귀 병합.

**Files:**
- Create: `src/t3dgraph/core/t3d/document.py`
- Test: `tests/core/t3d/test_document.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/t3d/test_document.py
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.values import Scalar

TWO_PHASE = (
    'Begin Object Class=/Script/X.Node Name="N"\n'
    '   Begin Object Class=/Script/X.Pin Name="P"\n'
    '   End Object\n'
    'End Object\n'
    'Begin Object Name="N"\n'
    '   Begin Object Name="P"\n'
    '      Direction=Output\n'
    '   End Object\n'
    '   Position=(X=1)\n'
    'End Object\n'
)


def test_two_phase_merge_unifies_object():
    doc = parse_document(TWO_PHASE)
    assert len(doc.objects) == 1                       # 두 블록이 하나로
    n = doc.objects[0]
    assert n.cls == "/Script/X.Node"                   # 선언 블록에서
    assert n.properties["Position"] is not None        # 정의 블록에서


def test_two_phase_merge_recurses_into_children():
    doc = parse_document(TWO_PHASE)
    pin = doc.objects[0].children[0]
    assert pin.cls == "/Script/X.Pin"
    assert pin.properties["Direction"] == Scalar("Output")


def test_real_file_parses(orion_dir):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    doc = parse_document(f.read_text(encoding="utf-8"))
    assert len(doc.objects) > 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_document.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/t3d/document.py
"""무손실 T3DDocument — 2단계(선언/정의) 블록 병합."""
from __future__ import annotations
from dataclasses import dataclass, field
from .objects import T3DObject, parse_objects


@dataclass
class T3DDocument:
    objects: list[T3DObject] = field(default_factory=list)


def _merge_into(target: T3DObject, other: T3DObject) -> None:
    """other(보통 정의 블록)의 정보를 target에 합친다."""
    if target.cls is None and other.cls is not None:
        target.cls = other.cls
    if other.export_path:
        target.export_path = other.export_path
    target.properties.update(other.properties)
    _merge_sibling_list(target.children, other.children)


def _merge_sibling_list(dst: list[T3DObject], src: list[T3DObject]) -> None:
    by_name: dict[str, T3DObject] = {o.name: o for o in dst if o.name}
    for o in src:
        existing = by_name.get(o.name) if o.name else None
        if existing is not None:
            _merge_into(existing, o)
        else:
            dst.append(o)
            if o.name:
                by_name[o.name] = o


def parse_document(src: str) -> T3DDocument:
    raw = parse_objects(src)
    merged: list[T3DObject] = []
    _merge_sibling_list(merged, raw)
    return T3DDocument(objects=merged)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d/test_document.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/document.py tests/core/t3d/test_document.py
git commit -m "feat(t3d): T3DDocument with two-phase block merge"
```

---

## Task 6: 추상 그래프 모델 — `core/base/graph_model.py`

인터프리터가 산출하고 분석·뷰가 소비하는 추상 데이터 모델. 순수 dataclass.

**Files:**
- Create: `src/t3dgraph/core/base/graph_model.py`
- Test: `tests/core/base/test_graph_model.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/base/test_graph_model.py
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_build_and_lookup():
    p_out = Pin(name="ExecOut", cpp_type="FRigVMExecuteContext", direction="Output")
    p_in = Pin(name="ExecIn", cpp_type="FRigVMExecuteContext", direction="Input")
    a = Node(name="A", cls="UnitNode", pins=[p_out])
    b = Node(name="B", cls="UnitNode", pins=[p_in])
    link = Link(source_path="A.ExecOut", target_path="B.ExecIn")
    g = GraphModel(nodes=[a, b], links=[link])
    assert g.node_by_name("B") is b
    assert g.node_by_name("Z") is None


def test_pin_subpins_default_empty():
    assert Pin(name="X", cpp_type="double", direction="Input").subpins == []


def test_external_refs_recorded():
    g = GraphModel(nodes=[], links=[], external_refs=["IK_Rig.ExecuteContext"])
    assert "IK_Rig.ExecuteContext" in g.external_refs
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/base/test_graph_model.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/base/graph_model.py
"""그래프 종류 무관 추상 데이터 모델."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Pin:
    name: str
    cpp_type: str | None
    direction: str | None                       # Input | Output | IO | Hidden | None
    default_value: str | None = None            # DefaultValue 원본 문자열
    subpins: list["Pin"] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)   # 무손실 — 모든 원본 속성


@dataclass
class Node:
    name: str
    cls: str | None
    pins: list[Pin] = field(default_factory=list)
    position: tuple[float, float] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    is_generic: bool = False                    # 알 수 없는 클래스 → 제네릭 폴백


@dataclass
class Link:
    source_path: str
    target_path: str


@dataclass
class VariableRef:
    variable_name: str
    cpp_type: str | None
    node_name: str


@dataclass
class GraphModel:
    nodes: list[Node] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    variable_refs: list[VariableRef] = field(default_factory=list)
    external_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def node_by_name(self, name: str) -> Node | None:
        for n in self.nodes:
            if n.name == name:
                return n
        return None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/base/test_graph_model.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/base/graph_model.py tests/core/base/test_graph_model.py
git commit -m "feat(base): abstract GraphModel/Node/Pin/Link"
```

---

## Task 7: 추상 인터프리터 + 플러그인 계약 — `core/base/interpreter.py`, `core/base/plugin.py`

**Files:**
- Create: `src/t3dgraph/core/base/interpreter.py`
- Create: `src/t3dgraph/core/base/plugin.py`
- Test: `tests/core/base/test_plugin.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/base/test_plugin.py
import pytest
from t3dgraph.core.base.interpreter import AbstractGraphInterpreter
from t3dgraph.core.base.plugin import GraphTypePlugin
from t3dgraph.core.base.graph_model import GraphModel
from t3dgraph.core.t3d.document import T3DDocument


def test_interpreter_is_abstract():
    with pytest.raises(TypeError):
        AbstractGraphInterpreter()


def test_concrete_interpreter_works():
    class Dummy(AbstractGraphInterpreter):
        def interpret(self, doc: T3DDocument) -> GraphModel:
            return GraphModel()

    assert isinstance(Dummy().interpret(T3DDocument()), GraphModel)


def test_plugin_matches_class_prefix():
    plugin = GraphTypePlugin(
        id="dummy",
        class_prefixes=["/Script/Foo."],
        interpreter_factory=lambda: None,
    )
    assert plugin.matches("/Script/Foo.Bar")
    assert not plugin.matches("/Script/Other.Baz")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/base/test_plugin.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/base/interpreter.py
"""최상위 추상 인터프리터 — 그래프 종류 모듈이 구현한다."""
from __future__ import annotations
from abc import ABC, abstractmethod
from .graph_model import GraphModel
from ..t3d.document import T3DDocument


class AbstractGraphInterpreter(ABC):
    @abstractmethod
    def interpret(self, doc: T3DDocument) -> GraphModel:
        """T3DDocument를 추상 GraphModel로 변환한다."""
        raise NotImplementedError
```

```python
# src/t3dgraph/core/base/plugin.py
"""그래프 타입 플러그인 계약."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
from .interpreter import AbstractGraphInterpreter


@dataclass
class GraphTypePlugin:
    id: str
    class_prefixes: list[str]
    interpreter_factory: Callable[[], AbstractGraphInterpreter]
    # view/controller는 Phase 2에서 지연 참조(문자열)로 추가된다.
    view_ref: str | None = None
    controller_ref: str | None = None

    def matches(self, class_path: str) -> bool:
        return any(class_path.startswith(p) for p in self.class_prefixes)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/base/test_plugin.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/base/interpreter.py src/t3dgraph/core/base/plugin.py tests/core/base/test_plugin.py
git commit -m "feat(base): AbstractGraphInterpreter and GraphTypePlugin contract"
```

---

## Task 8: 플러그인 레지스트리 — `core/registry.py`

플러그인을 등록받고, `T3DDocument`의 최상위 객체 `Class=` 들로 매칭 플러그인을 찾는다. `plugins/` 하위 패키지를 import해 self-register를 트리거한다.

**Files:**
- Create: `src/t3dgraph/core/registry.py`
- Test: `tests/core/test_registry.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/test_registry.py
import pytest
from t3dgraph.core.registry import Registry
from t3dgraph.core.base.plugin import GraphTypePlugin
from t3dgraph.core.t3d.document import parse_document


def _plugin(pid, prefixes):
    return GraphTypePlugin(id=pid, class_prefixes=prefixes, interpreter_factory=lambda: None)


def test_register_and_detect():
    reg = Registry()
    reg.register(_plugin("rigvm", ["/Script/RigVMDeveloper."]))
    doc = parse_document('Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\nEnd Object\n')
    assert reg.detect(doc).id == "rigvm"


def test_detect_no_match_raises():
    reg = Registry()
    doc = parse_document('Begin Object Class=/Script/Other.Thing Name="N"\nEnd Object\n')
    with pytest.raises(LookupError):
        reg.detect(doc)


def test_duplicate_id_raises():
    reg = Registry()
    reg.register(_plugin("x", ["/A."]))
    with pytest.raises(ValueError):
        reg.register(_plugin("x", ["/B."]))
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/test_registry.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/registry.py
"""플러그인 등록·그래프 타입 디스패치."""
from __future__ import annotations
import importlib
import pkgutil
from .base.plugin import GraphTypePlugin
from .t3d.document import T3DDocument


class Registry:
    def __init__(self) -> None:
        self._plugins: dict[str, GraphTypePlugin] = {}

    def register(self, plugin: GraphTypePlugin) -> None:
        if plugin.id in self._plugins:
            raise ValueError(f"플러그인 id 중복: {plugin.id}")
        self._plugins[plugin.id] = plugin

    def plugins(self) -> list[GraphTypePlugin]:
        return list(self._plugins.values())

    def detect(self, doc: T3DDocument) -> GraphTypePlugin:
        classes = [o.cls for o in doc.objects if o.cls]
        for plugin in self._plugins.values():
            if any(plugin.matches(c) for c in classes):
                return plugin
        raise LookupError(
            f"매칭되는 그래프 타입 플러그인 없음. 최상위 클래스: {classes[:5]} "
            f"— config/graph_types.toml 확인"
        )


_DEFAULT: Registry | None = None


def default_registry() -> Registry:
    """plugins/ 하위 패키지를 import해 self-register를 트리거한 전역 레지스트리."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Registry()
        import t3dgraph.plugins as plugins_pkg
        for mod in pkgutil.iter_modules(plugins_pkg.__path__):
            importlib.import_module(f"t3dgraph.plugins.{mod.name}")
    return _DEFAULT
```

> 주: `plugins/rigvm/__init__.py`(Task 11)가 import 시 `default_registry().register(...)` 를 호출한다. Task 8 단계에서는 `default_registry()`가 빈 `rigvm/__init__.py`를 import해도 무해하다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/test_registry.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/registry.py tests/core/test_registry.py
git commit -m "feat(core): plugin registry with graph-type detection"
```

---

## Task 9: RigVM 타입 분류 — `plugins/rigvm/types.py`

RigVM 클래스 상수와 분류 헬퍼. 실행 핀 판정(`CPPType == "FRigVMExecuteContext"`), 노드 클래스 여부.

**Files:**
- Create: `src/t3dgraph/plugins/rigvm/types.py`
- Test: `tests/plugins/rigvm/test_types.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/plugins/rigvm/test_types.py
from t3dgraph.plugins.rigvm import types as t


def test_node_class_detection():
    assert t.is_node_class("/Script/RigVMDeveloper.RigVMUnitNode")
    assert t.is_node_class("/Script/RigVMDeveloper.RigVMDispatchNode")
    assert not t.is_node_class("/Script/RigVMDeveloper.RigVMPin")


def test_link_class_detection():
    assert t.is_link_class("/Script/RigVMDeveloper.RigVMLink")
    assert not t.is_link_class("/Script/RigVMDeveloper.RigVMUnitNode")


def test_execution_pin_by_cpp_type():
    assert t.is_execution_cpp_type("FRigVMExecuteContext")
    assert not t.is_execution_cpp_type("double")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/plugins/rigvm/test_types.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/plugins/rigvm/types.py
"""RigVM 클래스 상수·분류 헬퍼."""
from __future__ import annotations

CLASS_PREFIXES = ["/Script/RigVMDeveloper.", "/Script/ControlRigDeveloper."]

NODE_CLASS_SUFFIXES = (
    "RigVMUnitNode", "RigVMDispatchNode", "RigVMFunctionEntryNode",
    "RigVMFunctionReturnNode", "RigVMVariableNode", "RigVMCollapseNode",
    "RigVMFunctionReferenceNode", "RigVMRerouteNode",
)
LINK_CLASS_SUFFIX = "RigVMLink"
PIN_CLASS_SUFFIX = "RigVMPin"
EXECUTE_CPP_TYPE = "FRigVMExecuteContext"


def _suffix(class_path: str) -> str:
    return class_path.rsplit(".", 1)[-1]


def is_node_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) in NODE_CLASS_SUFFIXES


def is_link_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) == LINK_CLASS_SUFFIX


def is_pin_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) == PIN_CLASS_SUFFIX


def is_execution_cpp_type(cpp_type: str | None) -> bool:
    return cpp_type == EXECUTE_CPP_TYPE
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/plugins/rigvm/test_types.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/plugins/rigvm/types.py tests/plugins/rigvm/test_types.py
git commit -m "feat(rigvm): RigVM class constants and classification helpers"
```

---

## Task 10: RigVM 인터프리터 — `plugins/rigvm/interpreter.py`

`T3DDocument` → `GraphModel`. 노드 클래스 객체 → `Node`(+ 중첩 `RigVMPin` → `Pin` 트리), `RigVMLink` 객체 → `Link`, `RigVMVariableNode` → `VariableRef`. 알 수 없는 클래스 → `is_generic=True` 노드 + warning. `Position` 파싱.

**Files:**
- Create: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Test: `tests/plugins/rigvm/test_interpreter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/plugins/rigvm/test_interpreter.py
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter

LINK_SRC = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
    '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Exec"\n'
    '   End Object\n'
    'End Object\n'
    'Begin Object Name="A"\n'
    '   Begin Object Name="Exec"\n'
    '      Direction=Output\n'
    '      CPPType="FRigVMExecuteContext"\n'
    '   End Object\n'
    '   Position=(X=10.000000,Y=-20.000000)\n'
    'End Object\n'
    'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
    '   SourcePinPath="A.Exec"\n'
    '   TargetPinPath="B.Exec"\n'
    'End Object\n'
)


def test_nodes_and_pins():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    a = g.node_by_name("A")
    assert a is not None and a.cls.endswith("RigVMUnitNode")
    assert a.position == (10.0, -20.0)
    assert a.pins[0].name == "Exec"
    assert a.pins[0].cpp_type == "FRigVMExecuteContext"


def test_links_extracted():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    assert len(g.links) == 1
    assert g.links[0].source_path == "A.Exec"
    assert g.links[0].target_path == "B.Exec"


def test_unknown_class_becomes_generic_with_warning():
    src = 'Begin Object Class=/Script/RigVMDeveloper.RigVMFutureNode Name="F"\nEnd Object\n'
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.node_by_name("F").is_generic is True
    assert any("RigVMFutureNode" in w for w in g.warnings)


def test_variable_node_extracted():
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMVariableNode Name="V"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Variable"\n'
        '   End Object\n'
        'End Object\n'
        'Begin Object Name="V"\n'
        '   Begin Object Name="Variable"\n'
        '      DefaultValue="IKTarget"\n'
        '   End Object\n'
        'End Object\n'
    )
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.variable_refs[0].variable_name == "IKTarget"


def test_real_rigvmmodel_file(orion_dir):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    g = RigVMGraphInterpreter().interpret(parse_document(f.read_text(encoding="utf-8")))
    assert len(g.nodes) > 0
    assert len(g.links) > 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/plugins/rigvm/test_interpreter.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/plugins/rigvm/interpreter.py
"""RigVM T3DDocument → 추상 GraphModel."""
from __future__ import annotations
from ..rigvm import types as t
from ...core.base.interpreter import AbstractGraphInterpreter
from ...core.base.graph_model import GraphModel, Node, Pin, Link, VariableRef
from ...core.t3d.document import T3DDocument
from ...core.t3d.objects import T3DObject
from ...core.t3d.values import Value, Scalar, QuotedString, Struct


def _text(v: Value | None) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


def _position(obj: T3DObject) -> tuple[float, float] | None:
    v = obj.properties.get("Position")
    if not isinstance(v, Struct):
        return None
    d = {k: _text(val) for k, val in v.items}
    try:
        return (float(d.get("X", "0")), float(d.get("Y", "0")))
    except (TypeError, ValueError):
        return None


def _build_pin(obj: T3DObject) -> Pin:
    return Pin(
        name=obj.name or "",
        cpp_type=_text(obj.properties.get("CPPType")),
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        subpins=[_build_pin(c) for c in obj.children],
        raw=dict(obj.properties),
    )


class RigVMGraphInterpreter(AbstractGraphInterpreter):
    def interpret(self, doc: T3DDocument) -> GraphModel:
        g = GraphModel()
        for obj in doc.objects:
            if t.is_link_class(obj.cls):
                self._add_link(obj, g)
            elif t.is_node_class(obj.cls):
                self._add_node(obj, g)
            elif obj.cls is None:
                continue  # 병합되지 않은 잔여 정의 블록 (정상적으론 없음)
            else:
                self._add_generic(obj, g)
        return g

    def _add_link(self, obj: T3DObject, g: GraphModel) -> None:
        src = _text(obj.properties.get("SourcePinPath"))
        tgt = _text(obj.properties.get("TargetPinPath"))
        if src and tgt:
            g.links.append(Link(source_path=src, target_path=tgt))

    def _add_node(self, obj: T3DObject, g: GraphModel) -> None:
        node = Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children if t.is_pin_class(c.cls) or c.cls is None],
            position=_position(obj),
            raw=dict(obj.properties),
        )
        g.nodes.append(node)
        if obj.cls and obj.cls.rsplit(".", 1)[-1] == "RigVMVariableNode":
            self._add_variable_ref(node, g)

    def _add_variable_ref(self, node: Node, g: GraphModel) -> None:
        var_pin = next((p for p in node.pins if p.name == "Variable"), None)
        val_pin = next((p for p in node.pins if p.name == "Value"), None)
        if var_pin and var_pin.default_value:
            g.variable_refs.append(VariableRef(
                variable_name=var_pin.default_value,
                cpp_type=val_pin.cpp_type if val_pin else None,
                node_name=node.name,
            ))

    def _add_generic(self, obj: T3DObject, g: GraphModel) -> None:
        suffix = obj.cls.rsplit(".", 1)[-1] if obj.cls else "?"
        g.warnings.append(f"알 수 없는 클래스 '{obj.cls}' — 제네릭 노드로 폴백")
        g.nodes.append(Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children],
            position=_position(obj),
            raw=dict(obj.properties),
            is_generic=True,
        ))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/plugins/rigvm/test_interpreter.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/plugins/rigvm/interpreter.py tests/plugins/rigvm/test_interpreter.py
git commit -m "feat(rigvm): T3DDocument to GraphModel interpreter"
```

---

## Task 11: RigVM 플러그인 등록 — `plugins/rigvm/__init__.py` + config

import 시 `GraphTypePlugin`을 구성해 전역 레지스트리에 self-register.

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/__init__.py` (Task 1에서 빈 파일로 생성됨)
- Modify: `config/graph_types.toml`
- Test: `tests/plugins/rigvm/test_registration.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/plugins/rigvm/test_registration.py
from t3dgraph.core.registry import default_registry


def test_rigvm_plugin_auto_registered():
    reg = default_registry()
    ids = [p.id for p in reg.plugins()]
    assert "rigvm" in ids


def test_rigvm_interpreter_factory_returns_interpreter():
    from t3dgraph.core.base.interpreter import AbstractGraphInterpreter
    reg = default_registry()
    plugin = next(p for p in reg.plugins() if p.id == "rigvm")
    assert isinstance(plugin.interpreter_factory(), AbstractGraphInterpreter)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/plugins/rigvm/test_registration.py -q`
Expected: FAIL — `assert "rigvm" in []`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/plugins/rigvm/__init__.py
"""RigVM 그래프 타입 플러그인 — import 시 self-register."""
from __future__ import annotations
from ...core.registry import default_registry
from ...core.base.plugin import GraphTypePlugin
from .types import CLASS_PREFIXES
from .interpreter import RigVMGraphInterpreter

_PLUGIN = GraphTypePlugin(
    id="rigvm",
    class_prefixes=list(CLASS_PREFIXES),
    interpreter_factory=RigVMGraphInterpreter,
    # Phase 2에서 view_ref/controller_ref(문자열 지연 참조) 추가
)


def register() -> None:
    reg = default_registry()
    if _PLUGIN.id not in [p.id for p in reg.plugins()]:
        reg.register(_PLUGIN)


register()
```

> 주: `default_registry()`가 `register()` 호출 → 다시 `default_registry()` 진입 시 `_DEFAULT`는 이미 생성돼 있어 재귀 import는 없다. `register()`의 멱등 체크가 중복 등록을 막는다.

`config/graph_types.toml`:

```toml
# graph type → interpreter 매핑.
# 내장 플러그인은 plugins/<id>/__init__.py 가 self-register 한다.
# 이 파일은 활성화·class_prefix 오버라이드용 (Phase 2부터 본격 사용).
[graph_types.rigvm]
class_prefixes = ["/Script/RigVMDeveloper.", "/Script/ControlRigDeveloper."]
interpreter    = "t3dgraph.plugins.rigvm.interpreter:RigVMGraphInterpreter"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/plugins/rigvm/test_registration.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/plugins/rigvm/__init__.py config/graph_types.toml tests/plugins/rigvm/test_registration.py
git commit -m "feat(rigvm): plugin self-registration via __init__.py"
```

---

## Task 12: 흐름 분석 — fan-in 수렴점 — `core/analysis/flow.py`

`GraphModel`에서 노드 단위 실행 그래프를 유도한다. 핀 경로(`"Node.Pin"` 또는 `"Node.Pin.Sub"`)의 첫 세그먼트가 노드 이름. 실행 링크 = 양끝 핀의 `cpp_type`이 실행 타입인 링크. 수렴점 = 들어오는 실행 엣지 ≥ 2 인 노드.

**Files:**
- Create: `src/t3dgraph/core/analysis/flow.py`
- Test: `tests/core/analysis/test_flow.py`

- [ ] **Step 1: 실패하는 테스트 작성 (합성 픽스처 — fan-in 포함)**

```python
# tests/core/analysis/test_flow.py
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.flow import analyze_flow


def _exec_pin(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=direction)


def _node(name, *pins):
    return Node(name=name, cls="RigVMUnitNode", pins=list(pins))


def _fan_in_graph():
    # A ─┐
    #    ├─> C ─> D
    # B ─┘
    a = _node("A", _exec_pin("Out", "Output"))
    b = _node("B", _exec_pin("Out", "Output"))
    c = _node("C", _exec_pin("In", "Input"), _exec_pin("Out", "Output"))
    d = _node("D", _exec_pin("In", "Input"))
    links = [
        Link("A.Out", "C.In"),
        Link("B.Out", "C.In"),
        Link("C.Out", "D.In"),
    ]
    return GraphModel(nodes=[a, b, c, d], links=links)


def test_convergence_point_detected():
    r = analyze_flow(_fan_in_graph())
    assert r.convergence_points == ["C"]


def test_convergence_prefixes_and_downstream():
    r = analyze_flow(_fan_in_graph())
    conv = r.convergence("C")
    assert set(conv.incoming_nodes) == {"A", "B"}
    assert conv.common_downstream == ["D"]


def test_linear_graph_has_no_convergence():
    a = _node("A", _exec_pin("Out", "Output"))
    b = _node("B", _exec_pin("In", "Input"))
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")]))
    assert r.convergence_points == []


def test_data_links_ignored_for_flow():
    # 데이터(비실행) 링크는 실행 그래프에 안 들어감
    a = _node("A", Pin(name="V", cpp_type="double", direction="Output"))
    b = _node("B", Pin(name="V", cpp_type="double", direction="Input"))
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.V", "B.V")]))
    assert r.execution_edges == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/analysis/test_flow.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/analysis/flow.py
"""실행 흐름 분석 — fan-in 수렴점, 공통 다운스트림."""
from __future__ import annotations
from dataclasses import dataclass, field
from ..base.graph_model import GraphModel, Pin


@dataclass
class Convergence:
    node: str
    incoming_nodes: list[str]
    common_downstream: list[str]


@dataclass
class FlowResult:
    execution_edges: list[tuple[str, str]] = field(default_factory=list)  # (src_node, tgt_node)
    convergence_points: list[str] = field(default_factory=list)
    branch_points: list[str] = field(default_factory=list)
    _convergences: dict[str, Convergence] = field(default_factory=dict)

    def convergence(self, node: str) -> Convergence:
        return self._convergences[node]


def _node_of(pin_path: str) -> str:
    return pin_path.split(".", 1)[0]


def _exec_pin_index(graph: GraphModel) -> set[tuple[str, str]]:
    """(node_name, pin_name) 중 실행 타입인 것."""
    out: set[tuple[str, str]] = set()

    def walk(node_name: str, pin: Pin) -> None:
        if pin.cpp_type == "FRigVMExecuteContext":
            out.add((node_name, pin.name))
        for sp in pin.subpins:
            walk(node_name, sp)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p)
    return out


def _pin_name(pin_path: str) -> str:
    parts = pin_path.split(".")
    return parts[1] if len(parts) > 1 else ""


def analyze_flow(graph: GraphModel) -> FlowResult:
    exec_pins = _exec_pin_index(graph)
    edges: list[tuple[str, str]] = []
    for link in graph.links:
        s_node, t_node = _node_of(link.source_path), _node_of(link.target_path)
        s_pin, t_pin = _pin_name(link.source_path), _pin_name(link.target_path)
        if (s_node, s_pin) in exec_pins and (t_node, t_pin) in exec_pins:
            edges.append((s_node, t_node))

    in_edges: dict[str, list[str]] = {}
    out_edges: dict[str, list[str]] = {}
    for s, t in edges:
        in_edges.setdefault(t, []).append(s)
        out_edges.setdefault(s, []).append(t)

    result = FlowResult(execution_edges=edges)
    result.convergence_points = sorted(n for n, srcs in in_edges.items() if len(srcs) >= 2)
    result.branch_points = sorted(n for n, tgts in out_edges.items() if len(tgts) >= 2)

    for node in result.convergence_points:
        result._convergences[node] = Convergence(
            node=node,
            incoming_nodes=sorted(in_edges[node]),
            common_downstream=_reachable(node, out_edges),
        )
    return result


def _reachable(start: str, out_edges: dict[str, list[str]]) -> list[str]:
    """start에서 실행 엣지를 따라 도달 가능한 노드 (start 제외, BFS)."""
    seen: set[str] = set()
    queue = list(out_edges.get(start, []))
    while queue:
        n = queue.pop(0)
        if n in seen:
            continue
        seen.add(n)
        queue.extend(out_edges.get(n, []))
    return sorted(seen)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/analysis/test_flow.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/analysis/flow.py tests/core/analysis/test_flow.py
git commit -m "feat(analysis): execution flow and fan-in convergence detection"
```

---

## Task 13: 실행 순서 분석 — `core/analysis/execution_order.py`

실행 그래프를 진입 노드부터 위상 순회해 선형 실행 순서를 산출한다. v1은 **선형 순서 + 깊이**만(루프/시퀀스 중첩 렌더는 Phase 2 뷰어에서 개선). 각 항목은 `(node_name, depth)`. 분기점에서는 각 분기를 깊이+1로.

**Files:**
- Create: `src/t3dgraph/core/analysis/execution_order.py`
- Test: `tests/core/analysis/test_execution_order.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/analysis/test_execution_order.py
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.execution_order import compute_execution_order


def _ep(name, d):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=d)


def _n(name, *pins):
    return Node(name=name, cls="RigVMUnitNode", pins=list(pins))


def test_linear_order():
    a = _n("A", _ep("O", "Output"))
    b = _n("B", _ep("I", "Input"), _ep("O", "Output"))
    c = _n("C", _ep("I", "Input"))
    g = GraphModel(nodes=[a, b, c], links=[Link("A.O", "B.I"), Link("B.O", "C.I")])
    order = compute_execution_order(g)
    assert [step.node for step in order] == ["A", "B", "C"]
    assert [step.depth for step in order] == [0, 0, 0]


def test_branch_increases_depth():
    a = _n("A", _ep("O", "Output"))
    b = _n("B", _ep("I", "Input"))
    c = _n("C", _ep("I", "Input"))
    # A 가 B, C 둘로 분기
    g = GraphModel(nodes=[a, b, c], links=[Link("A.O", "B.I"), Link("A.O", "C.I")])
    order = compute_execution_order(g)
    assert order[0].node == "A" and order[0].depth == 0
    assert {s.node for s in order[1:]} == {"B", "C"}
    assert all(s.depth == 1 for s in order[1:])


def test_empty_graph():
    assert compute_execution_order(GraphModel()) == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/analysis/test_execution_order.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/analysis/execution_order.py
"""구조화된 실행 순서 — 진입 노드부터 위상 순회."""
from __future__ import annotations
from dataclasses import dataclass
from ..base.graph_model import GraphModel
from .flow import analyze_flow


@dataclass
class ExecutionStep:
    node: str
    depth: int


def compute_execution_order(graph: GraphModel) -> list[ExecutionStep]:
    flow = analyze_flow(graph)
    out_edges: dict[str, list[str]] = {}
    in_count: dict[str, int] = {}
    nodes_in_flow: set[str] = set()
    for s, t in flow.execution_edges:
        out_edges.setdefault(s, []).append(t)
        in_count[t] = in_count.get(t, 0) + 1
        nodes_in_flow.update((s, t))

    # 진입 노드: 실행 그래프에 있으면서 들어오는 실행 엣지가 없는 노드
    entries = sorted(n for n in nodes_in_flow if in_count.get(n, 0) == 0)

    steps: list[ExecutionStep] = []
    visited: set[str] = set()

    def walk(node: str, depth: int) -> None:
        if node in visited:
            return
        visited.add(node)
        steps.append(ExecutionStep(node=node, depth=depth))
        succ = out_edges.get(node, [])
        child_depth = depth if len(succ) <= 1 else depth + 1
        for nxt in succ:
            walk(nxt, child_depth)

    for e in entries:
        walk(e, 0)
    return steps
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/analysis/test_execution_order.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/analysis/execution_order.py tests/core/analysis/test_execution_order.py
git commit -m "feat(analysis): linear execution order traversal"
```

---

## Task 14: CLI — `src/t3dgraph/cli.py`

`.t3d` 파일을 받아 파싱·해석·분석하고 요약을 출력한다. 라이브러리 동작을 명령행에서 검증하는 용도. `argparse`.

**Files:**
- Create: `src/t3dgraph/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_cli.py
from t3dgraph.cli import run


def test_cli_summary_on_real_file(orion_dir, capsys):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    exit_code = run([str(f)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "graph type: rigvm" in out
    assert "nodes:" in out
    assert "links:" in out


def test_cli_missing_file_returns_nonzero(capsys):
    exit_code = run(["nonexistent.t3d.txt"])
    assert exit_code != 0
    assert "찾을 수 없" in capsys.readouterr().err
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/cli.py
"""t3dgraph CLI — .t3d 파싱·해석·분석 요약."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from .core.t3d.document import parse_document
from .core.registry import default_registry
from .core.analysis.flow import analyze_flow
from .core.analysis.execution_order import compute_execution_order


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="t3dgraph", description="UE T3D 그래프 파서·분석")
    parser.add_argument("file", help=".t3d(.txt) 파일 경로")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2

    doc = parse_document(path.read_text(encoding="utf-8"))
    registry = default_registry()
    try:
        plugin = registry.detect(doc)
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 3

    graph = plugin.interpreter_factory().interpret(doc)
    flow = analyze_flow(graph)
    order = compute_execution_order(graph)

    print(f"graph type: {plugin.id}")
    print(f"nodes: {len(graph.nodes)}  (generic: {sum(n.is_generic for n in graph.nodes)})")
    print(f"links: {len(graph.links)}")
    print(f"variable refs: {len(graph.variable_refs)}")
    print(f"execution edges: {len(flow.execution_edges)}")
    print(f"convergence points (fan-in): {flow.convergence_points or '없음'}")
    print(f"execution steps: {len(order)}")
    for w in graph.warnings:
        print(f"  warning: {w}", file=sys.stderr)
    return 0


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/cli.py tests/test_cli.py
git commit -m "feat(cli): t3dgraph parse/analyze summary command"
```

---

## Task 15: 통합 테스트 — 11개 실제 Orion 파일

무손실·해석·분석이 실제 데이터 전부에서 깨지지 않는지 골든 테스트.

**Files:**
- Test: `tests/test_integration_orion.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_integration_orion.py
import pytest
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.registry import default_registry
from t3dgraph.core.analysis.flow import analyze_flow


def _all_files(orion_dir):
    return sorted(orion_dir.glob("*.t3d.txt"))


def test_eleven_fixture_files_present(orion_dir):
    assert len(_all_files(orion_dir)) == 11


def test_every_file_parses_and_interprets(orion_dir):
    reg = default_registry()
    for f in _all_files(orion_dir):
        doc = parse_document(f.read_text(encoding="utf-8"))
        plugin = reg.detect(doc)                       # rigvm 매칭
        assert plugin.id == "rigvm"
        graph = plugin.interpreter_factory().interpret(doc)
        assert len(graph.nodes) > 0
        analyze_flow(graph)                            # 예외 없이 분석 완료


def test_rigvmmodel_has_known_link(orion_dir):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    doc = parse_document(f.read_text(encoding="utf-8"))
    graph = default_registry().detect(doc).interpreter_factory().interpret(doc)
    pairs = {(l.source_path, l.target_path) for l in graph.links}
    # spec 2.2 에서 확인된 실제 링크
    assert ("IK_Rig.ExecuteContext", "StepPhysicsSolver.ExecutePin") in pairs


def test_samples_have_no_fan_in(orion_dir):
    # spec 2.3: 제공 샘플은 실행 흐름이 전부 선형
    reg = default_registry()
    for f in _all_files(orion_dir):
        doc = parse_document(f.read_text(encoding="utf-8"))
        graph = reg.detect(doc).interpreter_factory().interpret(doc)
        assert analyze_flow(graph).convergence_points == []
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/test_integration_orion.py -q`
Expected: 처음엔 FAIL 가능 — 실제 파일의 미처리 문법(예: 특이 값 표기)이 드러나면 해당 파서 모듈을 수정하고 그 수정에 대한 회귀 테스트를 해당 모듈 테스트 파일에 추가한 뒤 다시 실행. 모두 PASS할 때까지 반복.

- [ ] **Step 3: 전체 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration_orion.py
git commit -m "test: integration coverage over 11 real Orion .t3d files"
```

---

## Self-Review

**1. Spec coverage**
- spec §4 아키텍처/디렉터리 → Task 1~14 파일 구조 일치 (단 `core/app/`·플러그인 `view/controller`는 Phase 2)
- spec §5.1 T3D 파서 → Task 2~5
- spec §5.2 추상 계약 → Task 6~7
- spec §5.3 레지스트리 → Task 8
- spec §5.4 RigVM 플러그인 → Task 9~11
- spec §5.5 분석(fan-in·실행 순서) → Task 12~13
- spec §8 에러 처리: `T3DParseError`(Task 4), 알 수 없는 클래스 제네릭 폴백(Task 10), 그래프 타입 미매칭(Task 8), 파일 없음(Task 14) 반영. `--lenient` 플래그는 v1 선택 기능 — Phase 1 미포함, Phase 2 또는 후속에서 추가(spec §3 비목표 아님이므로 후속 plan에 명시 필요)
- spec §9 테스트: 합성 fan-in 픽스처(Task 12), 11개 골든 파일(Task 15) 반영
- **갭**: spec §5.4의 "미해결 외부 참조 → external ref 보존" — Task 10 인터프리터가 `external_refs`를 채우지 않음. → 아래 보강 참고

**2. Placeholder scan** — "TBD/TODO" 없음. 모든 코드 단계에 실제 코드 포함.

**3. Type consistency** — `GraphModel`/`Node`/`Pin`/`Link`/`VariableRef` 필드명이 Task 6 정의와 Task 10·12·13·14 사용처에서 일치 확인. `FlowResult.execution_edges`·`convergence_points` 일관.

**보강 — Task 10 external_refs**: spec §3.2의 에셋 단위 seam을 위해, 인터프리터가 링크의 `source/target` 노드 중 `GraphModel.nodes`에 없는 노드 이름을 `external_refs`에 기록하도록 Task 10 `interpret()` 끝에 다음을 추가한다(이 보강 자체를 Task 10 Step 1 테스트에 케이스로 포함):

```python
        known = {n.name for n in g.nodes}
        for link in g.links:
            for path in (link.source_path, link.target_path):
                node = path.split(".", 1)[0]
                if node not in known and path not in g.external_refs:
                    g.external_refs.append(path)
        return g
```

대응 테스트(Task 10 Step 1에 추가):

```python
def test_external_ref_recorded_for_unknown_target():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    # LINK_SRC: 링크 타깃 "B.Exec" 의 노드 B는 정의 안 됨
    assert "B.Exec" in g.external_refs
```

---

## 다음 단계 (Phase 2)

Phase 1 완료 후 별도 plan `2026-05-19-t3dgraph-viewer.md` 작성:
- `core/app/` — `AbstractGraphView`/`AbstractGraphController`, `main_window.py`, `app.py`
- `plugins/rigvm/view.py`·`controller.py` + `plugin.py` 지연 참조 등록
- QGraphicsView 노드/핀/링크 아이템, "분석 중심" 레이아웃, 노드 타입 필터·속성 인스펙터(연결됨 네비게이션·변경됨 휴리스틱)·분석/실행순서 도크
- `--lenient` 파싱 플래그
- pytest-qt 기반 테스트
