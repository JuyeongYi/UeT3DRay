# batch ⑩ χ (chi) — 배열 sort 일반화 (σ-A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `_sort_array_subpins`가 `Item_0`/`Element_0` 같은 prefix+digit 패턴 배열도 인덱스 순으로 정렬. digit-only 회귀 없음.

**Architecture:** `_ARRAY_PATTERN = re.compile(r"^([A-Za-z_]*?)(\d+)$")` 모듈 상수. 모든 subpin이 같은 prefix + 끝에 digits면 digit으로 정렬.

**Tech Stack:** Python 3.11 (`re`), pytest. 외부 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-10-hotfix-design.md` §6

**Pre-condition:** master `d07a130` 이상. 다른 슬라이스와 파일 충돌 없음 (`interpreter.py`의 `_sort_array_subpins`만 만짐).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (`_sort_array_subpins` 본문 + `_ARRAY_PATTERN` 모듈 상수) |
| `tests/base/test_pin_array_sort.py` | 확장 (prefix+digit 케이스) |

---

## Task 1: 패턴 일반화 — TDD

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Modify: `tests/base/test_pin_array_sort.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/base/test_pin_array_sort.py` 끝에 추가:

```python
def test_prefixed_digits_sorted() -> None:
    """Item_N 패턴 — digit 순서로 정렬."""
    pins = [_pin("Item_10"), _pin("Item_2"), _pin("Item_0"), _pin("Item_1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Item_0", "Item_1", "Item_2", "Item_10"]


def test_mixed_prefix_preserves_order() -> None:
    """prefix가 일관 안 하면 원순서 — 보수적 동작."""
    pins = [_pin("Item_0"), _pin("Element_0"), _pin("Item_1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Item_0", "Element_0", "Item_1"]


def test_underscore_only_prefix() -> None:
    pins = [_pin("Element_2"), _pin("Element_1"), _pin("Element_0")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Element_0", "Element_1", "Element_2"]


def test_camel_prefix() -> None:
    pins = [_pin("ItemAt2"), _pin("ItemAt0"), _pin("ItemAt1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["ItemAt0", "ItemAt1", "ItemAt2"]


def test_pure_digits_still_sorted() -> None:
    """기존 digit-only 동작 회귀 없음 (σ 슬라이스 결과 보존)."""
    pins = [_pin("10"), _pin("9"), _pin("0")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["0", "9", "10"]


def test_no_digit_suffix_preserves_order() -> None:
    """이름 끝이 digit이 아니면 원순서."""
    pins = [_pin("Alpha"), _pin("Beta"), _pin("Gamma")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Alpha", "Beta", "Gamma"]
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_pin_array_sort.py -v`
Expected: 신규 테스트 일부 FAIL (특히 prefixed 케이스 — 현재는 digit-only만 정렬).

- [ ] **Step 3: `_sort_array_subpins` 일반화**

`src/t3dgraph/plugins/rigvm/interpreter.py`에서 `_sort_array_subpins` 위(또는 helper 근처)에 모듈 상수 추가:

```python
import re

_ARRAY_PATTERN = re.compile(r"^([A-Za-z_]*?)(\d+)$")
```

(`import re` 이미 있는지 확인 — α 슬라이스에서 추가됐을 수 있음.)

`_sort_array_subpins` 본문 교체:

```python
def _sort_array_subpins(subpins: list[Pin]) -> list[Pin]:
    """T3D 배열 직렬화 quirk 정정.

    name이 전부 같은 prefix + 끝 digits면 digit 부분으로 int 정렬.
    예: '0','1','2'           → 0,1,2 (digit-only)
        'Item_0','Item_1'     → 0,1 정렬
        'X','Y','Z'           → 원순서 (배열 아님)
        'Item_0','Element_1'  → 원순서 (prefix 불일치, 안전)
    """
    if not subpins:
        return subpins
    matches = [_ARRAY_PATTERN.match(p.name) for p in subpins]
    if not all(matches):
        return subpins
    prefixes = {m.group(1) for m in matches}
    if len(prefixes) != 1:
        return subpins
    return sorted(subpins, key=lambda p: int(_ARRAY_PATTERN.match(p.name).group(2)))
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/base/test_pin_array_sort.py -v`
Expected: 전 통과 (기존 + 신규 6건).

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과. 특히 F17 repro 테스트(Orion ItemArray)가 그대로 통과 — digit-only 케이스가 새 코드에서도 동일 결과.

- [ ] **Step 6: 커밋**

```bash
git add tests/base/test_pin_array_sort.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "fix(rigvm): generalize array sort to prefix+digit pattern (σ-A1)"
```

---

## Self-Review 체크리스트

- Spec §6.1 `_ARRAY_PATTERN` 모듈 상수 + prefix 일관성 검사 — Task 1 ✅
- Spec §6.2 테스트 6건 — Task 1 ✅
- PRESERVE-ALL — subpin 수 동일, 순서만 정정 ✅
- σ 회귀 없음 (digit-only 패턴 그대로 작동) — Task 1 `test_pure_digits_still_sorted` ✅

---

## 완료 후

- improver 자동 리뷰 → backlog
- σ-A1 백로그 해소
- ψ 머지 시 충돌 없음 (다른 함수)
