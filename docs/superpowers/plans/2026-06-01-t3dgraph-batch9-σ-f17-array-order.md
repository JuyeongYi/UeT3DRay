# batch ⑨ σ (sigma) — F17 Array Order Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UE T3D가 배열 RigVMPin 자식을 역순(`10,9,8,...,0`)으로 직렬화하는 quirk를 인터프리터에서 정렬해 인덱스 순으로 보이게 한다.

**Architecture:** `_build_pin`에서 subpins이 전부 digit-only name이면 `int(name)` 순으로 정렬. parser/시각 레이어 무변경 — 모델 단계에서 한 번만 정정.

**Tech Stack:** Python 3.11, pytest.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` §5

**Pre-condition:** master `ad934a5` 이상 — π 머지. ρ와 interpreter.py 공유 — 작은 패치라 rebase 비용 적음.

**Data-informed scope (π 데이터)**:
- Orion 샘플 `test_array_subpin_order_preserved_orion` FAIL — `['10','9','8','7','6','5','4','3','2','1','0']` 정확 역순. T3D 원본 자체 quirk.
- F14 동시 처리 옵션은 **scope 제외** — Orion 샘플 회귀 미관측. 사용자 추가 보고 시 별도 슬라이스.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (`_sort_array_subpins` helper 신설 + `_build_pin` 적용) |
| `tests/repro/test_f17_array_order.py` | 통과 확인 (변경 없음) |
| `tests/base/test_pin_array_sort.py` | 신규 |

---

## Task 1: digit-only subpins 정렬 helper + `_build_pin` 통합

**Files:**
- Create: `tests/base/test_pin_array_sort.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`

- [ ] **Step 1: 실패하는 단위 테스트 작성**

`tests/base/test_pin_array_sort.py`:

```python
"""F17 — _sort_array_subpins helper 단위 테스트."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import Pin
from t3dgraph.plugins.rigvm.interpreter import _sort_array_subpins


def _pin(name: str, subs: list[Pin] | None = None) -> Pin:
    return Pin(name=name, cpp_type=None, direction=None,
               subpins=subs or [])


def test_all_digit_subpins_sorted_by_int_value() -> None:
    """digit-only subpin name이면 int 순서로."""
    pins = [_pin("10"), _pin("9"), _pin("8"), _pin("7"), _pin("6"),
            _pin("5"), _pin("4"), _pin("3"), _pin("2"), _pin("1"), _pin("0")]
    sorted_pins = _sort_array_subpins(pins)
    assert [p.name for p in sorted_pins] == [str(i) for i in range(11)]


def test_mixed_names_not_sorted() -> None:
    """일부만 digit이면 원순서 유지 — struct 핀 등 비배열."""
    pins = [_pin("X"), _pin("Y"), _pin("Z")]
    sorted_pins = _sort_array_subpins(pins)
    assert [p.name for p in sorted_pins] == ["X", "Y", "Z"]


def test_partial_digit_not_sorted() -> None:
    """digit + 비-digit 섞이면 원순서 — 보수적 동작."""
    pins = [_pin("0"), _pin("X"), _pin("1")]
    sorted_pins = _sort_array_subpins(pins)
    assert [p.name for p in sorted_pins] == ["0", "X", "1"]


def test_empty_list_passthrough() -> None:
    assert _sort_array_subpins([]) == []


def test_single_digit_pin() -> None:
    assert [p.name for p in _sort_array_subpins([_pin("0")])] == ["0"]
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_pin_array_sort.py -v`
Expected: FAIL — `_sort_array_subpins` 미존재.

- [ ] **Step 3: helper + `_build_pin` 통합**

`src/t3dgraph/plugins/rigvm/interpreter.py` 모듈 함수로 helper 추가 (`_build_pin` 위):

```python
def _sort_array_subpins(subpins: list[Pin]) -> list[Pin]:
    """T3D 배열 직렬화 quirk 정정.

    UE는 array RigVMPin 자식을 인덱스 역순(10,9,...,0)으로 serialize한다.
    name이 전부 digit-only이면 int 순으로 재정렬. 그 외엔 원순서 유지.
    """
    if not subpins:
        return subpins
    if all(p.name.isdigit() for p in subpins):
        return sorted(subpins, key=lambda p: int(p.name))
    return subpins
```

`_build_pin`을 다음으로 갱신:

```python
def _build_pin(obj: T3DObject) -> Pin:
    cpp_type = _text(obj.properties.get("CPPType"))
    subpins = _sort_array_subpins([_build_pin(c) for c in obj.children])
    return Pin(
        name=obj.name or "",
        cpp_type=cpp_type,
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        is_execution=t.is_execution_cpp_type(cpp_type),
        subpins=subpins,
        raw=dict(obj.properties),
    )
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/base/test_pin_array_sort.py -v`
Expected: 5 passed

- [ ] **Step 5: F17 repro 통과 확인**

Run: `T3DGRAPH_ORION_SAMPLE=Orion_WorkStation_Rig_Analysis/<sample>.t3d.txt pytest tests/repro/test_f17_array_order.py -v`
Expected:
- `test_array_subpin_order_preserved_synth` — PASS
- `test_array_subpin_order_preserved_orion` — **PASS** (이전 FAIL → 정렬로 해소)

- [ ] **Step 6: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 7: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

Orion 샘플 로드 → `ItemArray` 노드 선택 → 인스펙터 `Value` 핀 펼침 → 자식 핀이 `0,1,2,...,10` 정순.

- [ ] **Step 8: 커밋**

```bash
git add tests/base/test_pin_array_sort.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "fix(rigvm): sort digit-only array subpins by int — UE serialization reverse (F17)"
```

---

## Self-Review 체크리스트

- Spec §5 F17 fix — Task 1 ✅
- digit-only subpins만 정렬 (struct 등 보존) — Task 1 Step 1 ✅
- T3D 원본 quirk 정정 위치(`_build_pin`) — Task 1 Step 3 ✅
- F17 repro 통과(synth + Orion) — Task 1 Step 5 ✅
- PRESERVE-ALL — subpin 수 동일, 순서만 정정 ✅
- F14 scope 제외 — Orion 미재현, 사용자 추가 보고 시 별도 슬라이스 (spec §9.6 deferred)

---

## 완료 후

- improver 자동 리뷰 → backlog
- ρ와 σ 머지 후 batch ⑨ 마감
- F14 잔존: 사용자 추가 보고 또는 명시적 재현 케이스 확보 시 별도 슬라이스
