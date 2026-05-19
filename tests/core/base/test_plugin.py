import pytest
from t3dgraph.core.base.interpreter import AbstractGraphInterpreter
from t3dgraph.core.base.plugin import GraphTypePlugin
from t3dgraph.core.base.graph_model import GraphModel
from t3dgraph.core.t3d.document import T3DDocument


def test_interpreter_is_abstract():
    with pytest.raises(TypeError):
        AbstractGraphInterpreter()


def test_concrete_interpreter_works():
    class Dummy(AbstractGraphInterpreter):
        def interpret(self, doc: T3DDocument) -> GraphModel:
            return GraphModel()

    assert isinstance(Dummy().interpret(T3DDocument()), GraphModel)


def test_plugin_matches_class_prefix():
    plugin = GraphTypePlugin(
        id="dummy",
        class_prefixes=["/Script/Foo."],
        interpreter_factory=lambda: None,
    )
    assert plugin.matches("/Script/Foo.Bar")
    assert not plugin.matches("/Script/Other.Baz")
