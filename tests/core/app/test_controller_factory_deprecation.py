"""h3 (ψ-A1) — InterpreterFactory backward-compat fallback."""
import warnings

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


def _invoke_via_helper(factory, resolver):
    """_call_interpreter_factory를 한 단계 감싸 stacklevel=3 검증용 간접 호출자."""
    return _call_interpreter_factory(factory, resolver=resolver)


def test_deprecation_warning_points_to_caller() -> None:
    """stacklevel=3이면 경고가 직접 호출자(_invoke_via_helper)의 호출자(test함수)를 가리킴."""
    f = _FactoryWithoutResolver()
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        _invoke_via_helper(f, resolver="R")
    dep = next((w for w in ws if issubclass(w.category, DeprecationWarning)), None)
    assert dep is not None
    assert "test_controller_factory_deprecation" in dep.filename, (
        f"stacklevel 부정확 — filename={dep.filename}"
    )
