from t3dgraph.core.registry import default_registry


def test_rigvm_plugin_auto_registered():
    reg = default_registry()
    ids = [p.id for p in reg.plugins()]
    assert "rigvm" in ids


def test_rigvm_interpreter_factory_returns_interpreter():
    from t3dgraph.core.base.interpreter import AbstractGraphInterpreter
    reg = default_registry()
    plugin = next(p for p in reg.plugins() if p.id == "rigvm")
    assert isinstance(plugin.interpreter_factory(), AbstractGraphInterpreter)
