# batch ⑫ c1 — Boundary Public API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** boundary leak 3건 해소 — `LayoutOverrides.graph_keys()` public, `AssetResolver.extract_target_path` public + `resolve_function_reference` 튜플 반환, `DeprecationWarning stacklevel=3`.

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-12-cleanup-design.md` §3

**Pre-condition:** master `0d5892c` 이상. c2/c3/c4와 병렬 가능 (다른 파일).

---

## Task 1: LayoutOverrides.graph_keys public (⑪-A1)

**Files:**
- Modify: `src/t3dgraph/core/app/layout_overrides.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/app/test_layout_overrides.py`

- [ ] **Step 1: 테스트 추가**

```python
def test_graph_keys_returns_current_keys() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "N1", 1.0, 2.0)
    lo.set("graph-B", "N1", 3.0, 4.0)
    assert set(lo.graph_keys()) == {"graph-A", "graph-B"}


def test_graph_keys_empty_when_no_overrides() -> None:
    assert list(LayoutOverrides().graph_keys()) == []
```

- [ ] **Step 2: 구현**

`layout_overrides.py`:

```python
from typing import Iterable

class LayoutOverrides:
    ...
    def graph_keys(self) -> Iterable[str]:
        """현재 보관 중인 graph_key 목록 (public)."""
        return self._by_graph.keys()
```

`main_window._save_persistent_state`에서 `layout_overrides._by_graph.keys()` → `layout_overrides.graph_keys()` 치환.

- [ ] **Step 3: 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_layout_overrides.py src/t3dgraph/core/app/layout_overrides.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): LayoutOverrides.graph_keys() public API (⑪-A1)"
```

---

## Task 2: AssetResolver.extract_target_path public + resolve_function_reference 튜플 (⑪-A2)

**Files:**
- Modify: `src/t3dgraph/core/t3d/resolver.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Modify: `tests/base/test_resolver_extract_target.py`

- [ ] **Step 1: 테스트 갱신 (public name)**

```python
# 기존 _extract_target_path 호출을 extract_target_path로 변경
def test_extract_class_pattern() -> None:
    r = AssetResolver()
    assert r.extract_target_path("Class'/Game/Lib.Lib:RigVMModel.F'") == \
           "/Game/Lib.Lib:RigVMModel.F"
# ... 모든 테스트 동일
```

- [ ] **Step 2: 신규 테스트 — `resolve_function_reference` 튜플**

```python
def test_resolve_function_reference_returns_tuple_unparseable() -> None:
    r = AssetResolver()
    obj, reason = r.resolve_function_reference("not a ref")
    assert obj is None
    assert "unparseable" in reason


def test_resolve_function_reference_returns_tuple_not_found(orion_folder) -> None:
    r = AssetResolver()
    r.load_folder(orion_folder)
    obj, reason = r.resolve_function_reference(
        "Class'/Game/NonExistent.NonExistent:RigVMModel.NoFunc'"
    )
    assert obj is None
    assert "not found" in reason


def test_resolve_function_reference_returns_tuple_success(orion_folder) -> None:
    r = AssetResolver()
    r.load_folder(orion_folder)
    # Orion 샘플에서 실제 함수 ref 사용
    ...
    obj, reason = r.resolve_function_reference(real_ref_path)
    assert obj is not None
    assert reason is None
```

- [ ] **Step 3: 구현**

`resolver.py`:

```python
class AssetResolver:
    ...
    def extract_target_path(self, ref_path: str) -> str | None:
        """ref 경로에서 타겟 추출. 비표준이면 None (public)."""
        # 기존 _extract_target_path 본문 그대로
        ...

    # 호환을 위해 한 사이클 별칭
    _extract_target_path = extract_target_path

    def resolve_function_reference(
        self, ref_path: str
    ) -> tuple["T3DObject | None", str | None]:
        target = self.extract_target_path(ref_path)
        if target is None:
            return None, "ref unparseable"
        # 기존 룩업 로직
        target_doc = self._docs_by_pkg.get(...)
        ...
        if target_doc is None:
            return None, "asset not found"
        ...
        return found, None
```

`interpreter.py`의 호출부:

```python
ext_obj, reason = self._resolver.resolve_function_reference(ref_path_raw)
if ext_obj is None:
    suffix = f" ({reason})" if reason else ""
    diagnostics.external_refs_unresolved.append(f"{ref_path_raw}{suffix}")
else:
    # 기존 subgraph 연결
    ...
```

`self._resolver._extract_target_path` 직접 호출은 제거 — `resolve_function_reference`가 reason을 돌려주므로 인터프리터가 plugin internals 안 만짐.

- [ ] **Step 4: 회귀**

Run: `pytest tests -v`

- [ ] **Step 5: 커밋**

```bash
git add tests/base/test_resolver_extract_target.py src/t3dgraph/core/t3d/resolver.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "feat(resolver): extract_target_path public + tuple return (⑪-A2)"
```

---

## Task 3: DeprecationWarning stacklevel=3 (⑪-A3)

**Files:**
- Modify: `src/t3dgraph/core/app/controller.py`
- Modify: `tests/core/app/test_controller_factory_deprecation.py`

- [ ] **Step 1: 테스트 — 호출자 모듈 추적**

```python
def test_deprecation_warning_points_to_caller() -> None:
    """stacklevel=3이면 호출자(test 함수)를 가리킴."""
    f = _FactoryWithoutResolver()
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        _call_interpreter_factory(f, resolver="R")
    deprecation = next(
        (w for w in ws if issubclass(w.category, DeprecationWarning)), None
    )
    assert deprecation is not None
    # 경고의 filename이 controller.py가 아닌 본 테스트 파일
    assert "test_controller_factory_deprecation" in deprecation.filename, (
        f"stacklevel 부정확 — filename={deprecation.filename}"
    )
```

- [ ] **Step 2: 변경**

`controller.py::_call_interpreter_factory`의 `stacklevel=2` → `stacklevel=3`.

- [ ] **Step 3: 실행**

Run: `pytest tests/core/app/test_controller_factory_deprecation.py -v`
Expected: 전 통과.

- [ ] **Step 4: 풀스위트 회귀**

Run: `pytest tests -v`

- [ ] **Step 5: 커밋**

```bash
git add tests/core/app/test_controller_factory_deprecation.py src/t3dgraph/core/app/controller.py
git commit -m "fix(app): DeprecationWarning stacklevel=3 for accurate caller (⑪-A3)"
```

## 완료 후

⑪-A1·A2·A3 해소. boundary public API 정상화.
