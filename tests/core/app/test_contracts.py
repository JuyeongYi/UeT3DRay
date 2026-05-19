import pytest
from t3dgraph.core.app.contracts import AbstractGraphView, AbstractGraphController


def test_view_is_abstract():
    with pytest.raises(TypeError):
        AbstractGraphView()


def test_controller_is_abstract():
    with pytest.raises(TypeError):
        AbstractGraphController()


def test_concrete_subclasses_instantiable():
    class V(AbstractGraphView):
        def show_graph(self, graph): return None
        def show_analysis(self, flow, order): return None

    class C(AbstractGraphController):
        def open_file(self, path): return None

    assert V().show_graph(None) is None
    assert C().open_file("x") is None
