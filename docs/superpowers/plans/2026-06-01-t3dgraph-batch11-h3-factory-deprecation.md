# batch ⑪ h3 — InterpreterFactory deprecation 폴백 (ψ-A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** ψ가 제거한 `inspect.signature` 폴백을 한 사이클 유지 — 외부 플러그인 backward break 차단. `DeprecationWarning`으로 마이그레이션 유도.

**Architecture:** `controller.py`에 `_call_interpreter_factory(factory, *, resolver)` 헬퍼 — `resolver` 키워드 받는지 검사해 분기. 받지 않으면 `warnings.warn(... DeprecationWarning, ...)`.

**Spec:** §5

**Pre-condition:** master `6ebd03d` 이상. h1/h2/h4와 병렬.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/controller.py` | 수정 (`_call_interpreter_factory` helper + 호출부) |
| `tests/core/app/test_controller_factory_deprecation.py` | 신규 |

---

## Task 1: deprecation 폴백 helper — TDD

- [ ] **Step 1: 테스트 작성**

`tests/core/app/test_controller_factory_deprecation.py`:

```python
"""h3 (ψ-A1) — InterpreterFactory backward-compat fallback."""
import warnings
import pytest

from t3dgraph.core.app.controller import _call_interpreter_factory


class _FactoryWithResolver:
    def __call__(self, *, resolver=None):
        return f"with-resolver:{resolver}"


class _FactoryWithoutResolver:
    def __call__(self):
        return "without-resolver"


def test_factory_with_resolver_no_warning() -> None:
    f = _FactoryWithResolver()
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        result = _call_interpreter_factory(f, resolver="R")
    assert result == "with-resolver:R"
    assert not any(issubclass(w.category, DeprecationWarning) for w in ws)


def test_factory_without_resolver_deprecation_warning() -> None:
    f = _FactoryWithoutResolver()
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        result = _call_interpreter_factory(f, resolver="R")
    assert result == "without-resolver"
    assert any(
        issubclass(w.category, DeprecationWarning) for w in ws
    ), "DeprecationWarning 발사 안 됨"
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/core/app/test_controller_factory_deprecation.py -v`
Expected: FAIL — `_call_interpreter_factory` 미존재.

- [ ] **Step 3: helper 구현 + 호출부 변경**

`src/t3dgraph/core/app/controller.py` 상단:

```python
import inspect
import warnings


def _call_interpreter_factory(factory, *, resolver):
    """InterpreterFactory 호출 — 'resolver' 키워드 미수신 시 deprecation 경고 후 폴백."""
    sig = inspect.signature(factory)
    if "resolver" in sig.parameters:
        return factory(resolver=resolver)
    warnings.warn(
        "InterpreterFactory does not accept resolver= keyword. "
        "Update factory to InterpreterFactory protocol "
        "(see core/app/contracts.py::InterpreterFactory). "
        "Backward-compat fallback will be removed in a future batch.",
        DeprecationWarning, stacklevel=2,
    )
    return factory()
```

기존 `factory(resolver=self.view.resolver)` 직접 호출을 `_call_interpreter_factory(factory, resolver=self.view.resolver)`로 교체.

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/core/app/test_controller_factory_deprecation.py -v`
Expected: 2 passed.

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과. `RigVMGraphInterpreter`는 `resolver` 키워드 받으므로 warning 발사 없음.

- [ ] **Step 6: 마이그레이션 노트 추가 (`2026-05-19-t3d-rig-graph-tool-design.md` 끝부분)**

```markdown
## 마이그레이션 노트 — InterpreterFactory (batch ⑩ ψ → ⑪ h3)

batch ⑩ ψ가 `inspect.signature` 디스패치 글루를 제거하면서 `InterpreterFactory` Protocol을 도입했다. 모든 플러그인 인터프리터 팩토리는 `(resolver: AssetResolver | None = None)` 키워드를 받아야 한다. batch ⑪ h3에서 한 사이클 deprecation 폴백을 복구해 외부 플러그인이 자기 사이클에 맞춰 마이그레이션 가능하게 했다. 다음 정리 batch에서 폴백 제거 예정.
```

- [ ] **Step 7: 커밋**

```bash
git add tests/core/app/test_controller_factory_deprecation.py src/t3dgraph/core/app/controller.py docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md
git commit -m "fix(app): InterpreterFactory deprecation fallback for backward compat (ψ-A1)"
```

## 완료 후

ψ-A1 해소. 외부 플러그인 backward break 차단.
