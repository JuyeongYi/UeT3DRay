# batch ⑬ g2 — 실행 핀 우선 정렬 (F22) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** node.pins 안에서 실행 핀(`is_execution=True`)을 안정 정렬로 앞에 배치. 원순서 보존.

**Spec:** §4

**Pre-condition:** master `f8fa09d` 이상. 다른 슬라이스와 파일 충돌 없음.

---

## Task 1: `_sort_pins_exec_first` + `_add_node` 적용

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Create: `tests/base/test_pin_exec_sort.py`

- [ ] **Step 1: 테스트**

```python
"""g2 (F22) — 실행 핀 우선 정렬."""
from t3dgraph.core.base.graph_model import Pin
from t3dgraph.plugins.rigvm.interpreter import _sort_pins_exec_first


def _p(name: str, exec_: bool = False) -> Pin:
    return Pin(name=name, cpp_type=None, direction=None, is_execution=exec_)


def test_exec_pin_moves_to_front() -> None:
    pins = [_p("A"), _p("B"), _p("Exec", exec_=True), _p("C")]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["Exec", "A", "B", "C"]


def test_multiple_execs_preserve_relative_order() -> None:
    pins = [_p("A"), _p("Main", exec_=True), _p("B"), _p("Completed", exec_=True)]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["Main", "Completed", "A", "B"]


def test_no_exec_pins_no_change() -> None:
    pins = [_p("A"), _p("B"), _p("C")]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["A", "B", "C"]


def test_all_exec_pins_no_change() -> None:
    pins = [_p("Main", True), _p("Loop", True)]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["Main", "Loop"]


def test_empty_list() -> None:
    assert _sort_pins_exec_first([]) == []
```

- [ ] **Step 2: 헬퍼 구현**

`src/t3dgraph/plugins/rigvm/interpreter.py` `_sort_array_subpins` 근처에 추가:

```python
def _sort_pins_exec_first(pins: list[Pin]) -> list[Pin]:
    """실행 핀(is_execution=True)을 앞쪽으로 안정 정렬. 그 외 순서 보존."""
    return sorted(pins, key=lambda p: (not p.is_execution,))
```

- [ ] **Step 3: `_add_node`에 적용**

```python
def _add_node(self, obj, g, *, diagnostics, depth=0, max_depth=64) -> None:
    summary, category = role_for(obj)
    raw_pins = [_build_pin(c) for c in obj.children
                if t.is_pin_class(c.cls) or c.cls is None]
    node = Node(
        name=obj.name or "",
        cls=obj.cls,
        pins=_sort_pins_exec_first(raw_pins),
        ...
    )
```

- [ ] **Step 4: 실행 — 통과**

Run: `pytest tests/base/test_pin_exec_sort.py -v`
Expected: 5 passed.

Run: `pytest tests -v`
Expected: 전체 통과. (기존 통합 테스트가 특정 pin 순서 가정하면 갱신 — 보통 노드별 핀 검색은 이름 기반이라 영향 적음.)

- [ ] **Step 5: 커밋**

```bash
git add tests/base/test_pin_exec_sort.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "feat(rigvm): _sort_pins_exec_first — exec pins always first (F22)"
```

## 완료 후

F22 해소. F23 부수 효과 (실행 핀 위로 와서 에디터 컨벤션 정합).
