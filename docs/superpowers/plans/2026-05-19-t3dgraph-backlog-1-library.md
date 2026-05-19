# t3dgraph 백로그 정리 ① — 라이브러리 (parser·CLI·analysis) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** improver findings 중 라이브러리 측 4건을 수정한다 — 파싱 에러 위치 정밀화, CLI의 T3DParseError 포착, 인코딩 헬퍼 중복 제거, 경로 파싱 헬퍼 중앙화.

**Architecture:** 기존 t3dgraph 구조 유지. `core/t3d/`에 공유 헬퍼 모듈 2개(`encoding.py`·`paths.py`)를 신설하고 흩어진 중복 로직을 모은다. Model 레이어 stdlib-only 유지.

**Tech Stack:** Python 3.11+, stdlib only, pytest. (기존 코드베이스 — 신규 의존성 없음.)

**선행 조건:** Phase 2d 완료(master, 158 테스트 통과). 리포: `C:/Users/jylee/source/UeT3DRay`.

**근거:** `docs/superpowers/backlog.md` — improver findings.

**재검토 결과 (착수 전 backlog 규칙 적용):**
- `P1.5-A1`·`P2a-A2`·`P2a-B1`(+`P1.5-B1`)·`P2a-B3` — 현재 코드에서 **여전히 유효**, 본 계획에 포함.
- `P2a-A1`(Position 누락 노드 폴백) — 재검토 결과 인터프리터가 아니라 **뷰어 씬 레이아웃 사안**(None 위치 노드를 NodeItem이 (0,0)에 적재). → 그룹 ②(뷰어 정리)로 이관, 본 계획 제외.

---

## File Structure (백로그 정리 ①)

| 파일 | 변경 | finding |
| --- | --- | --- |
| `src/t3dgraph/core/t3d/values.py` | 수정 | `ValueParseError`에 `pos` 속성 (P1.5-A1) |
| `src/t3dgraph/core/t3d/objects.py` | 수정 | col에 `pos` 반영 (P1.5-A1) |
| `src/t3dgraph/cli.py` | 수정 | T3DParseError 포착 (P2a-A2) / 공유 헬퍼 사용 |
| `src/t3dgraph/core/t3d/encoding.py` | 생성 | `read_t3d_text` 공유 헬퍼 (P2a-B1/P1.5-B1) |
| `src/t3dgraph/core/app/controller.py` | 수정 | 로컬 `_read_text` → 공유 헬퍼 (P2a-B1) |
| `src/t3dgraph/core/t3d/paths.py` | 생성 | 경로 파싱 헬퍼 (P2a-B3) |
| `src/t3dgraph/core/analysis/flow.py` | 수정 | 경로 헬퍼 사용 (P2a-B3) |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 | 경로 헬퍼 사용 (P2a-B3) |
| `src/t3dgraph/core/app/scene.py` | 수정 | 경로 헬퍼 사용 (P2a-B3) |
| `src/t3dgraph/core/app/node_filter_panel.py` | 수정 | 경로 헬퍼 사용 (P2a-B3) |

---

## Task 1: P1.5-A1 — 파싱 에러 위치 정밀화

`ValueParseError`가 위치 정보를 메시지 문자열에만 담는다(`(pos N)`). 구조화된 `pos` 속성으로 노출하고, `objects.py`가 그 `pos`를 col에 반영해 파일 줄·열을 정밀하게 가리키게 한다.

**Files:**
- Modify: `src/t3dgraph/core/t3d/values.py`
- Modify: `src/t3dgraph/core/t3d/objects.py:67`
- Modify: `tests/core/t3d/test_values.py`, `tests/core/t3d/test_objects.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/t3d/test_values.py` 에 추가:

```python
def test_value_parse_error_has_pos():
    import pytest
    from t3dgraph.core.t3d.values import parse_value, ValueParseError
    with pytest.raises(ValueParseError) as ei:
        parse_value("(X=1")               # 닫히지 않은 구조체
    assert isinstance(ei.value.pos, int)
    assert ei.value.pos > 0
```

`tests/core/t3d/test_objects.py` 에 추가:

```python
def test_bad_value_col_reflects_value_internal_pos():
    import pytest
    from t3dgraph.core.t3d.objects import T3DParseError
    # 닫히지 않은 구조체 — 에러는 값 내부 깊숙이에서 발생
    src = 'Begin Object Name="N"\n   Bad=(X=1,Y=2\nEnd Object\n'
    with pytest.raises(T3DParseError) as ei:
        parse_objects(src)
    # col = indent(3) + len("Bad")(3) + 1 + pos(>0) → 값 시작(7)보다 큼
    assert ei.value.line == 2
    assert ei.value.col > 3 + 3 + 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_values.py::test_value_parse_error_has_pos tests/core/t3d/test_objects.py::test_bad_value_col_reflects_value_internal_pos -q`
Expected: FAIL — `ValueParseError`에 `pos` 속성 없음 (`AttributeError`)

- [ ] **Step 3: 구현**

`core/t3d/values.py` — `ValueParseError` 클래스를 다음으로 교체:

```python
class ValueParseError(ValueError):
    def __init__(self, message: str, pos: int = 0):
        self.pos = pos
        super().__init__(message)
```

그리고 `values.py`의 모든 `raise ValueParseError(...)` 사이트를 — 메시지에서 `(pos N)` 표기를 빼고 `pos`를 2번째 인자로 — 다음과 같이 바꾼다 (총 7곳):

| 위치 | 변경 후 |
| --- | --- |
| `parse_value` | `raise ValueParseError(f"값 뒤에 남은 입력: {text!r}", p.i)` |
| `_quoted` | `raise ValueParseError("닫히지 않은 따옴표 문자열", self.i)` |
| `_struct_body` `=` 기대 | `raise ValueParseError("구조체 키 뒤 '=' 기대", self.i)` |
| `_struct_body` 닫힘 없음 | `raise ValueParseError("닫히지 않은 구조체", self.i)` |
| `_struct_body` `,`/`)` 기대 | `raise ValueParseError("구조체에서 ',' 또는 ')' 기대", self.i)` |
| `_array_body` 닫힘 없음 | `raise ValueParseError("닫히지 않은 배열", self.i)` |
| `_array_body` `,`/`)` 기대 | `raise ValueParseError("배열에서 ',' 또는 ')' 기대", self.i)` |

`core/t3d/objects.py` — `parse_block` 의 `except ValueParseError` 블록(67행)에서 col 계산에 `e.pos`를 더한다:

```python
                except ValueParseError as e:
                    col = ln.indent + len(key) + 1 + e.pos
                    raise T3DParseError(ln.number, col, f"속성값 파싱 실패: {e}") from e
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d -q`
Expected: PASS — 기존 값/객체 파서 테스트 + 신규 2개

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/values.py src/t3dgraph/core/t3d/objects.py tests/core/t3d/test_values.py tests/core/t3d/test_objects.py
git commit -m "fix(t3d): structured pos on ValueParseError, precise col (P1.5-A1)"
```

---

## Task 2: P2a-A2 — CLI가 T3DParseError 포착

`cli.py`는 `UnicodeDecodeError`만 포착하고 `T3DParseError`는 놓쳐 불량 `.t3d`에서 스택트레이스를 노출한다.

**Files:**
- Modify: `src/t3dgraph/cli.py:6,30-34`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_cli.py` 에 추가:

```python
def test_cli_malformed_file_reports_error(tmp_path, capsys):
    bad = tmp_path / "bad.t3d.txt"
    bad.write_text('Begin Object Name="N"\n', encoding="utf-8")   # End Object 없음
    code = run([str(bad)])
    assert code != 0
    assert code != 1                                              # 처리된 에러 (크래시 아님)
    err = capsys.readouterr().err
    assert "파싱" in err
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_cli.py::test_cli_malformed_file_reports_error -q`
Expected: FAIL — `T3DParseError`가 미포착되어 예외가 전파 (테스트가 에러로 종료)

- [ ] **Step 3: 구현**

`cli.py` — import에 `T3DParseError` 추가:

```python
from .core.t3d.document import parse_document
from .core.t3d.objects import T3DParseError
```

`run` 함수의 parse 블록(30~34행)에 `except T3DParseError` 추가:

```python
    try:
        doc = parse_document(_read_text(path))
    except UnicodeDecodeError as e:
        print(f"파일 인코딩을 해석할 수 없습니다: {path} ({e})", file=sys.stderr)
        return 2
    except T3DParseError as e:
        print(f"T3D 파싱 실패: {path}: {e}", file=sys.stderr)
        return 4
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/cli.py tests/test_cli.py
git commit -m "fix(cli): catch T3DParseError instead of leaking traceback (P2a-A2)"
```

---

## Task 3: P2a-B1 / P1.5-B1 — 인코딩 헬퍼 중복 제거

`cli._read_text` 와 `controller._read_text` 가 동일 코드 중복. `core/t3d/encoding.py`로 통합한다.

**Files:**
- Create: `src/t3dgraph/core/t3d/encoding.py`
- Modify: `src/t3dgraph/cli.py` (로컬 `_read_text` 제거 → import)
- Modify: `src/t3dgraph/core/app/controller.py` (로컬 `_read_text` 제거 → import)
- Create: `tests/core/t3d/test_encoding.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/t3d/test_encoding.py
from t3dgraph.core.t3d.encoding import read_t3d_text


def test_plain_utf8(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("Begin Object", encoding="utf-8")
    assert read_t3d_text(f) == "Begin Object"


def test_utf8_bom(tmp_path):
    f = tmp_path / "b.txt"
    f.write_bytes(b"\xef\xbb\xbf" + "Begin Object".encode("utf-8"))
    assert read_t3d_text(f) == "Begin Object"


def test_utf16(tmp_path):
    f = tmp_path / "c.txt"
    f.write_bytes("Begin Object".encode("utf-16"))
    assert read_t3d_text(f) == "Begin Object"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_encoding.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/t3d/encoding.py
"""T3D 파일 텍스트 읽기 — BOM·UTF-16 인코딩 견고화 (cli·viewer 공유)."""
from __future__ import annotations
from pathlib import Path


def read_t3d_text(path: Path) -> str:
    """BOM·UTF-16 익스포트도 처리하는 견고한 텍스트 읽기."""
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")   # utf-8-sig: BOM 있으면 제거, 없으면 utf-8
```

`cli.py` — 로컬 `_read_text` 함수(12~17행)를 삭제하고 import 추가, 사용처(`_read_text(path)`)를 `read_t3d_text(path)`로:

```python
from .core.t3d.encoding import read_t3d_text
```
```python
        doc = parse_document(read_t3d_text(path))
```

`core/app/controller.py` — 로컬 `_read_text` 함수(19~23행)를 삭제하고 import 추가, 사용처(`_read_text(p)`)를 `read_t3d_text(p)`로:

```python
from ..t3d.encoding import read_t3d_text
```
```python
            doc = parse_document(read_t3d_text(p))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/t3d/test_encoding.py tests/test_cli.py tests/core/app/test_controller.py -q`
Expected: PASS — 신규 인코딩 테스트 + 기존 cli/controller 테스트

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/encoding.py src/t3dgraph/cli.py src/t3dgraph/core/app/controller.py tests/core/t3d/test_encoding.py
git commit -m "refactor(t3d): shared read_t3d_text encoding helper (P2a-B1)"
```

---

## Task 4: P2a-B3 — 경로 파싱 헬퍼 중앙화

핀 경로·클래스 경로의 `split(".")` 로직이 `flow.py`·`scene.py`·`interpreter.py`·`node_filter_panel.py`에 흩어져 있다(`_node_of`·`_pin_name`·`_seg`·`_type_suffix`). `core/t3d/paths.py`로 모은다.

**Files:**
- Create: `src/t3dgraph/core/t3d/paths.py`
- Modify: `src/t3dgraph/core/analysis/flow.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py:56`
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `src/t3dgraph/core/app/node_filter_panel.py`
- Create: `tests/core/t3d/test_paths.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/t3d/test_paths.py
from t3dgraph.core.t3d.paths import node_of, pin_segment, type_suffix


def test_node_of():
    assert node_of("Node.Pin.Sub") == "Node"
    assert node_of("Solo") == "Solo"


def test_pin_segment():
    assert pin_segment("Node.Pin.Sub", 0) == "Node"
    assert pin_segment("Node.Pin.Sub", 1) == "Pin"
    assert pin_segment("Node.Pin.Sub", 2) == "Sub"
    assert pin_segment("Node", 1) == ""


def test_type_suffix():
    assert type_suffix("/Script/RigVMDeveloper.RigVMUnitNode") == "RigVMUnitNode"
    assert type_suffix(None) == "?"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/t3d/test_paths.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/t3d/paths.py
"""핀 경로·클래스 경로 파싱 헬퍼 (중앙화)."""
from __future__ import annotations


def node_of(pin_path: str) -> str:
    """핀 경로의 노드 세그먼트. 'Node.Pin.Sub' → 'Node'."""
    return pin_path.split(".", 1)[0]


def pin_segment(pin_path: str, index: int) -> str:
    """핀 경로의 index번째 점-구분 세그먼트. 범위 밖이면 ''."""
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


def type_suffix(class_path: str | None) -> str:
    """클래스 경로의 마지막 세그먼트. '/Script/X.RigVMUnitNode' → 'RigVMUnitNode'.
    None이면 '?'."""
    return (class_path or "?").rsplit(".", 1)[-1]
```

`core/analysis/flow.py` — 모듈 내 `_node_of`·`_pin_name` 함수 정의를 삭제하고 import로 대체. 상단 import에 추가:

```python
from ..t3d.paths import node_of, pin_segment
```

`analyze_flow` 본문에서 `_node_of(...)` → `node_of(...)`, `_pin_name(path)` → `pin_segment(path, 1)` 로 치환.

`plugins/rigvm/interpreter.py` — 상단 import에 `from ...core.t3d.paths import node_of` 추가, `interpret`의 56행 `node = path.split(".", 1)[0]` → `node = node_of(path)`.

`core/app/scene.py` — 모듈 내 `_seg`·`_type_suffix` 함수 정의를 삭제하고 import로 대체:

```python
from ..t3d.paths import pin_segment, type_suffix
```

`_seg(x, i)` 사용처 → `pin_segment(x, i)`, `_type_suffix(x)` → `type_suffix(x)`.

`core/app/node_filter_panel.py` — 모듈 내 `_type_suffix` 정의를 삭제하고 import로 대체:

```python
from ..t3d.paths import type_suffix
```

`_type_suffix(...)` 사용처 → `type_suffix(...)`.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest -q`
Expected: 전체 PASS — 경로 헬퍼 신규 테스트 + 기존 분석·인터프리터·씬·필터 테스트 (헬퍼 치환은 동작 동일)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/t3d/paths.py src/t3dgraph/core/analysis/flow.py src/t3dgraph/plugins/rigvm/interpreter.py src/t3dgraph/core/app/scene.py src/t3dgraph/core/app/node_filter_panel.py tests/core/t3d/test_paths.py
git commit -m "refactor: centralize path-parsing helpers in core/t3d/paths (P2a-B3)"
```

---

## Task 5: 전체 회귀 검증

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS — 기존 158개 + 백로그 정리 ① 신규 테스트, 실패 0

- [ ] **Step 2: CLI 스모크 — 정상 + 불량 파일**

Run:
```bash
python -m t3dgraph.cli tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt
```
Expected: 정상 요약 출력, exit 0. (불량 파일 처리는 Task 2 테스트로 검증됨.)

(검증 전용 — 별도 커밋 없음.)

---

## Self-Review

**1. Findings coverage (그룹 ① 범위)**
- P1.5-A1 파싱 에러 위치 → Task 1 ✓
- P2a-A2 CLI T3DParseError 포착 → Task 2 ✓
- P2a-B1 / P1.5-B1 인코딩 헬퍼 중복 → Task 3 ✓
- P2a-B3 경로 헬퍼 중앙화 → Task 4 ✓
- **이관**: P2a-A1(Position 폴백) → 그룹 ②(뷰어). 재검토 결과 씬 레이아웃 사안.
- **범위 밖**: 뷰어 findings 12건 → 그룹 ②, FEAT-5 → 그룹 ③.

**2. Placeholder scan** — "TBD/TODO" 없음. Task 1의 raise-site 표는 7개 사이트의 정확한 변경 후 코드.

**3. Type consistency**
- `ValueParseError(message, pos=0)` + `.pos` — Task 1 정의, `objects.py`가 `e.pos` 사용 일치
- `read_t3d_text(path)` — Task 3 정의, cli·controller 사용 일치
- `node_of`/`pin_segment`/`type_suffix` — Task 4 정의, flow·interpreter·scene·node_filter 사용 일치. `pin_segment(path, 1)`가 기존 `_pin_name`의 "2번째 세그먼트" 동작과 동일, `type_suffix`가 기존 `_type_suffix`의 `(cls or "?").rsplit` 동작과 동일 — 치환 안전.

---

## 다음 — 그룹 ②·③

- **그룹 ②** 뷰어 정리 — P2a-A1(Position 폴백, 이관분 포함)·P2b-A1/A2/B1/B2/B3·P2c-A1/B1/B2·P2d-A1/A2/B1 (13건). planner가 별도 계획.
- **그룹 ③** FEAT-5 — 실행 순서 패널 코드형 렌더링 고도화.
- 각 그룹 착수 시 backlog.md "처리 규칙"대로 당시 코드 기준 재검토.
