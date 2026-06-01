# batch ⑫ c3 — Struct 메서드 + Cycle Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `Struct.find_path` + `Struct.find_first` 메서드 추가 (α-B1). cycle/depth guard 동시 도입 (α-A1). 인터프리터의 `_walk_struct*` 메서드 제거 → Struct 메서드 사용.

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-12-cleanup-design.md` §5

**Pre-condition:** master `0d5892c` 이상. c1/c2/c4와 병렬.

---

## Task 1: Struct.find_path + find_first — TDD

**Files:**
- Modify: `src/t3dgraph/core/t3d/values.py`
- Create: `tests/core/t3d/test_struct_methods.py`

- [ ] **Step 1: 테스트**

```python
"""c3 — Struct.find_path + find_first 메서드 단위."""
from t3dgraph.core.t3d.values import Struct, Scalar


def _s(*items):
    return Struct(items=list(items))


def test_find_path_top_level() -> None:
    s = _s(("Key", Scalar("value")))
    assert s.find_path("Key") == Scalar("value")


def test_find_path_nested() -> None:
    inner = _s(("Leaf", Scalar("L")))
    s = _s(("Outer", inner))
    assert s.find_path("Outer", "Leaf") == Scalar("L")


def test_find_path_missing_returns_none() -> None:
    s = _s(("Key", Scalar("value")))
    assert s.find_path("Missing") is None
    assert s.find_path("Key", "DeeperNotExist") is None


def test_find_first_shallow() -> None:
    s = _s(("X", Scalar("x")), ("Y", Scalar("y")))
    assert s.find_first("Y") == Scalar("y")


def test_find_first_deep() -> None:
    inner = _s(("Target", Scalar("t")))
    s = _s(("A", _s(("B", inner))))
    assert s.find_first("Target") == Scalar("t")


def test_find_first_max_depth_guard() -> None:
    """깊은 nesting에서도 max_depth 절단."""
    deepest = _s(("Target", Scalar("t")))
    s = deepest
    for _ in range(20):
        s = _s(("Nest", s))
    # max_depth=8이면 깊이 20에 있는 Target 못 찾음
    assert s.find_first("Target", max_depth=8) is None
    # max_depth=21이면 찾음
    assert s.find_first("Target", max_depth=21) == Scalar("t")


def test_find_first_missing() -> None:
    s = _s(("X", Scalar("x")))
    assert s.find_first("Missing") is None
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/core/t3d/test_struct_methods.py -v`
Expected: FAIL — 메서드 미존재.

- [ ] **Step 3: 구현**

`src/t3dgraph/core/t3d/values.py`:

```python
@dataclass(frozen=True)
class Struct(Value):
    items: list[tuple[str, "Value"]]

    def find_path(self, *keys: str) -> "Value | None":
        """key 시퀀스를 따라 struct 내려가서 값 반환."""
        cur: "Value | None" = self
        for key in keys:
            if not isinstance(cur, Struct):
                return None
            cur = next((v for k, v in cur.items if k == key), None)
            if cur is None:
                return None
        return cur

    def find_first(self, target_key: str, *, max_depth: int = 8) -> "Value | None":
        """generic walk으로 target_key 첫 매치."""
        if max_depth <= 0:
            return None
        for k, v in self.items:
            if k == target_key:
                return v
            if isinstance(v, Struct):
                found = v.find_first(target_key, max_depth=max_depth - 1)
                if found is not None:
                    return found
        return None
```

- [ ] **Step 4: 실행 — 통과**

Run: `pytest tests/core/t3d/test_struct_methods.py -v`
Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/core/t3d/test_struct_methods.py src/t3dgraph/core/t3d/values.py
git commit -m "feat(t3d): Struct.find_path + find_first with depth guard (α-A1 + α-B1)"
```

---

## Task 2: 인터프리터 `_walk_struct*` 제거

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`

- [ ] **Step 1: `_extract_lib_node_path_from_header` 갱신**

`src/t3dgraph/plugins/rigvm/interpreter.py`:

```python
def _extract_lib_node_path_from_header(self, obj: T3DObject) -> str | None:
    header = obj.properties.get("ReferencedFunctionHeader")
    if not isinstance(header, Struct):
        return None
    known = header.find_path("LibraryPointer", "LibraryNodePath")
    if known is not None:
        return _text(known)
    found = header.find_first("LibraryNodePath")
    return _text(found) if found else None
```

`_walk_struct`·`_walk_struct_find_key` 메서드 자체 제거.

- [ ] **Step 2: 회귀**

Run: `pytest tests -v`
Expected: 전체 통과 (F20 헤더 폴백 테스트가 같은 결과).

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "refactor(rigvm): use Struct.find_path/find_first in header walker (α-B1)"
```

## 완료 후

α-A1, α-B1 해소.
