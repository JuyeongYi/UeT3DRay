# batch ⑮ x2 — `_scalar` paren-balanced 흡수 (UE 매크로 호출형 value) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `Category=NSLOCTEXT("KismetSchema", "Default", "Default")` 같은 UE 매크로 호출형 value(`ident(paren-list)`)에서 `values.py:_struct_body`가 `"구조체에서 ',' 또는 ')' 기대"` 폭발하는 문제 fix.

**Repro:** `Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D` line 397283 — `NewVariables(N) = (..., Category=NSLOCTEXT("...", "...", "..."), ...)`.

**원인 (확인됨):**
- `_scalar`가 `,()` 만나면 종료. `Category=NSLOCTEXT(...)` 에서 `NSLOCTEXT`까지만 scalar로 읽고 `(`에서 멈춤.
- `_struct_body`는 value parse 후 `,` 또는 `)` 기대. 실제는 `(` → `ValueParseError("구조체에서 ',' 또는 ')' 기대")`.
- `NSLOCTEXT`/`LOCTEXT`/`INVTEXT` 등 UE localization 매크로가 광범위 사용 — 큰 t3d 파일에서 보편적.

**해법:** `_scalar`에 paren-balance + quote 보호 — `(` depth++, `)` depth--, depth 0에서 `,` 또는 outer `)` 만나면 종료. 따옴표 안 내용은 paren/comma 무시. 결과: `NSLOCTEXT("a","b","c")` 전체가 한 scalar로 흡수.

**회귀 영향:** depth 0에서 종료 조건은 기존과 동일 (`,`·`)`). paren 없는 입력은 동작 동일. struct/array는 시작이 `(`라 `_paren` 진입 — `_scalar` 변경 무관. 공백 포함 scalar(`RigUnit_X 2466...`)도 그대로.

**Pre-condition:** master `ad9591b`, 651 tests (x1 머지 후).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/t3d/values.py` | 수정 (`_scalar`에 paren depth + quote skip) |
| `tests/core/t3d/test_macro_call_value.py` | 신규 (재현 + UE 매크로 회귀 + smoke) |

---

## Task 1: TDD — 재현 → paren-balanced `_scalar`

**Files:**
- Modify: `src/t3dgraph/core/t3d/values.py`
- Create: `tests/core/t3d/test_macro_call_value.py`

- [ ] **Step 1: 재현 + 회귀 테스트**

```python
"""x2 — _scalar paren-balanced for UE macro-call values."""
from pathlib import Path
import pytest
from t3dgraph.core.t3d.values import parse_value, Struct, Scalar, ArrayLiteral
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.objects import parse_objects


def test_nsloctext_macro_in_struct_value() -> None:
    """Category=NSLOCTEXT(...) 가 한 scalar로 흡수."""
    text = '(VarName="X",Category=NSLOCTEXT("KismetSchema", "Default", "Default"),Flags=1)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    keys = [k for k, _ in v.items]
    assert keys == ["VarName", "Category", "Flags"]
    category = next(val for k, val in v.items if k == "Category")
    assert isinstance(category, Scalar)
    # paren 포함 전체 흡수
    assert "NSLOCTEXT" in category.text
    assert '"KismetSchema"' in category.text
    assert category.text.endswith(")")


def test_nested_macro_call() -> None:
    """nested paren도 정확히 balance."""
    text = '(X=A(B(C),D(E,F)),Y=2)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    x_val = next(val for k, val in v.items if k == "X")
    assert isinstance(x_val, Scalar)
    assert x_val.text == "A(B(C),D(E,F))"


def test_quote_inside_paren_protects_comma() -> None:
    """따옴표 안 `,`·`(` 가 paren depth/comma 종료 영향 안 줌."""
    text = '(Cat=FN("a,b","c)d"),Z=1)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    cat = next(val for k, val in v.items if k == "Cat")
    assert isinstance(cat, Scalar)
    assert cat.text == 'FN("a,b","c)d")'


def test_plain_scalar_no_regression() -> None:
    """paren 없는 일반 scalar는 동작 동일."""
    text = '(A=hello,B=42)'
    v = parse_value(text)
    assert isinstance(v, Struct)
    a = next(val for k, val in v.items if k == "A")
    b = next(val for k, val in v.items if k == "B")
    assert isinstance(a, Scalar) and a.text == "hello"
    assert isinstance(b, Scalar) and b.text == "42"


def test_array_of_macro_scalars() -> None:
    """array element가 매크로 호출형."""
    text = '(NSLOCTEXT("a","b","c"),NSLOCTEXT("d","e","f"))'
    v = parse_value(text)
    assert isinstance(v, ArrayLiteral)
    assert len(v.items) == 2
    assert all(isinstance(item, Scalar) for item in v.items)


def test_spaced_scalar_with_guid_still_works() -> None:
    """기존 `RigUnit_X SP GUID` 공백 scalar 회귀 없음."""
    text = '(LinkedTo=(RigUnit_X 2466091D48C71EBA1D2EF4BB6AEED3DD,))'
    v = parse_value(text)
    assert isinstance(v, Struct)
    linked = next(val for k, val in v.items if k == "LinkedTo")
    assert isinstance(linked, ArrayLiteral)
    assert len(linked.items) == 1
    elem = linked.items[0]
    assert isinstance(elem, Scalar)
    assert "RigUnit_X" in elem.text and "2466091D" in elem.text


def test_new_variables_full_line_struct() -> None:
    """397283 형 실제 line 통과."""
    text = (
        '(VarName="L_mouth_suck_blow_offset",'
        'VarGuid=D03976AB34474BBB0B2807CD14D7A95,'
        'VarType=(PinCategory="real",PinSubCategory="double",bSerializeAsSinglePrecisionFloat=True),'
        'FriendlyName="L Mouth Suck Blow Offset",'
        'Category=NSLOCTEXT("KismetSchema", "Default", "Default"),'
        'PropertyFlags=65541,'
        'MetaDataArray=((DataKey="MultiLine",DataValue="true")))'
    )
    v = parse_value(text)
    assert isinstance(v, Struct)
    keys = [k for k, _ in v.items]
    assert "VarName" in keys
    assert "Category" in keys
    assert "MetaDataArray" in keys


@pytest.mark.skipif(
    not Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").exists(),
    reason="repro file 미존재 환경",
)
def test_simple_face_ctrlrig_full_parse() -> None:
    """전체 파일이 폭발 없이 parse_document 통과."""
    raw = Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").read_text(
        encoding="utf-16",
    )
    doc = parse_document(raw)
    assert doc is not None
```

- [ ] **Step 2: 재현 (fix 전)**

Run: `pytest tests/core/t3d/test_macro_call_value.py -v`
Expected: `test_nsloctext_macro_in_struct_value` FAIL with `ValueParseError("구조체에서 ',' 또는 ')' 기대" ...)`.

- [ ] **Step 3: `_scalar` paren-balance + quote 보호**

`src/t3dgraph/core/t3d/values.py` `_scalar`를 교체:

```python
    def _scalar(self) -> Scalar:
        """Paren-balanced scalar: `(...)` block을 통째 흡수하면서
        outer terminator(`,` at depth 0, `)` at depth 0)에서만 종료.
        따옴표 내부는 모든 paren/comma 무시.
        """
        start = self.i
        depth = 0
        while not self.at_end():
            c = self.s[self.i]
            if c == '"':
                # quoted segment 안전 통과
                self.i += 1
                while not self.at_end() and self.s[self.i] != '"':
                    if self.s[self.i] == "\\" and self.i + 1 < len(self.s):
                        self.i += 2
                        continue
                    self.i += 1
                if not self.at_end():
                    self.i += 1   # 닫는 "
                continue
            if c == "(":
                depth += 1
                self.i += 1
                continue
            if c == ")":
                if depth == 0:
                    break
                depth -= 1
                self.i += 1
                continue
            if c == "," and depth == 0:
                break
            self.i += 1
        return Scalar(self.s[start:self.i].strip())
```

기존 4줄 구현 대체. `_paren`·`_struct_body`·`_array_body`·`_quoted`는 변경 없음.

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/t3d/test_macro_call_value.py -v`
Expected: 7 passed + smoke (file 존재 시) pass.

Run: `pytest tests -v`
Expected: 전체 통과 (651 + 7 신규 + smoke = 658~659).

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

`Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D` 열기 — 폭발 없이 완전 로드. ControlRig 변수 목록·노드들 정상 표시.

- [ ] **Step 6: 커밋**

```bash
git add tests/core/t3d/test_macro_call_value.py src/t3dgraph/core/t3d/values.py
git commit -m "fix(t3d): paren-balanced scalar absorbs UE macro-call values (x2)"
```

---

## 무엇이 깨질 수 있나

| 위험 | 완화 |
|---|---|
| paren depth가 unbalanced 입력에서 무한 흡수 → 다음 토큰 잠식 | `at_end`로 종료. 실제 t3d는 balanced; 깨진 입력은 어차피 다른 곳에서 실패 |
| escape 처리 차이로 `\"` 가 quote close로 오인 | 기존 `_quoted`와 동일한 `\\` skip 패턴 사용 — 일관성 |
| `_array_body`/`_struct_body`가 새 scalar 종료 조건과 충돌 | 종료 조건(depth 0의 `,`·`)`)이 기존과 동일 — 외부 caller 변경 없음 |
| 매우 큰 t3d 입력에서 성능 — 문자별 loop는 기존과 동일 O(N) | 동일 복잡도, 상수 배수 약간 증가. measurable 영향 없음 |

## 완료 후

- `NSLOCTEXT`/`LOCTEXT`/`INVTEXT` 등 UE 매크로 호출형 value를 포함한 t3d 파일이 폭발 없이 파싱
- ControlRig 블루프린트 변수 정의(`NewVariables(N)=...`)가 정상 흡수
- 다음 단계에서 ControlRig 변수 정보가 graph_model에 반영될 여지 (현재는 RigVM model 인터프리트만 — YAGNI)
