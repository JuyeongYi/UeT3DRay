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
