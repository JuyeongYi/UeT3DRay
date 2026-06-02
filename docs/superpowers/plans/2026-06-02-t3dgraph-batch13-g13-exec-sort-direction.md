# batch ⑬ g13 — 실행 핀 사이 IO/Output 정렬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `_sort_pins_exec_first` 확장 — 실행 핀 그룹 내에서도 IO(주 실행) > Output(보조 실행) > 기타 순서로 정렬. 사용자가 요청한 "Dispatch Array Iterator에서 ExecuteContext 위, Completed 아래" 충족.

**Pre-condition:** master 최신 (g2 머지 완료, b23b931 이후).

---

## Task 1: 정렬 키에 direction rank 추가

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Modify: `tests/base/test_pin_exec_sort.py`

- [ ] **Step 1: 테스트 추가**

```python
def test_exec_io_before_exec_output() -> None:
    """실행 핀 그룹 내에서 IO(주 실행)가 Output(보조 실행) 위로."""
    from t3dgraph.core.base.graph_model import Pin
    pins = [
        Pin(name="Completed", cpp_type="FRigVMExecuteContext",
            direction="Output", is_execution=True),
        Pin(name="ExecuteContext", cpp_type="FRigVMExecuteContext",
            direction="IO", is_execution=True),
        Pin(name="Array", cpp_type="TArray<float>",
            direction="Input"),
    ]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["ExecuteContext", "Completed", "Array"]


def test_exec_input_after_io_and_output() -> None:
    """exec Input(드물지만) 가능 — IO·Output 다음."""
    from t3dgraph.core.base.graph_model import Pin
    pins = [
        Pin(name="ExecIn", cpp_type="FRigVMExecuteContext",
            direction="Input", is_execution=True),
        Pin(name="ExecOut", cpp_type="FRigVMExecuteContext",
            direction="Output", is_execution=True),
        Pin(name="ExecIO", cpp_type="FRigVMExecuteContext",
            direction="IO", is_execution=True),
    ]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["ExecIO", "ExecOut", "ExecIn"]


def test_two_exec_same_direction_preserve_order() -> None:
    """같은 direction 내에서는 원순서 보존."""
    from t3dgraph.core.base.graph_model import Pin
    pins = [
        Pin(name="ExecB", cpp_type="FRigVMExecuteContext",
            direction="Output", is_execution=True),
        Pin(name="ExecA", cpp_type="FRigVMExecuteContext",
            direction="Output", is_execution=True),
    ]
    result = _sort_pins_exec_first(pins)
    # 둘 다 Output → 원순서 그대로
    assert [p.name for p in result] == ["ExecB", "ExecA"]
```

- [ ] **Step 2: 구현 갱신**

`src/t3dgraph/plugins/rigvm/interpreter.py`의 `_sort_pins_exec_first`:

```python
def _sort_pins_exec_first(pins: list[Pin]) -> list[Pin]:
    """실행 핀(is_execution=True)을 앞쪽으로 안정 정렬.

    실행 핀 그룹 내에서 IO(주 실행) > Output(보조 실행) > 기타 순.
    같은 direction 내에서는 원순서 보존(stable sort).
    """
    def _exec_dir_rank(direction: str | None) -> int:
        d = (direction or "").lower()
        if d == "io":
            return 0
        if d == "output":
            return 1
        return 2   # Input/Hidden/None

    return sorted(pins, key=lambda p: (
        not p.is_execution,
        _exec_dir_rank(p.direction) if p.is_execution else 0,
    ))
```

- [ ] **Step 3: 실행**

Run: `pytest tests/base/test_pin_exec_sort.py -v`
Expected: 기존 5건 + 신규 3건 = 8 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (회귀 테스트가 정확한 순서 가정 시 갱신 — exec 핀이 더 정밀하게 정렬됨).

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 샘플의 Dispatch Array Iterator 노드 — 출력 핀 순서:
- ExecuteContext (위)
- Completed (아래)
- (다음에 데이터 출력 — Ratio, Count, Index, Element)

- [ ] **Step 5: 커밋**

```bash
git add tests/base/test_pin_exec_sort.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "feat(rigvm): exec pin sort — IO before Output within exec group"
```

## 완료 후

Dispatch 노드의 ExecuteContext(IO)·Completed(Output) 순서 정상화.
