from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.inspector_panel import InspectorPanel


def _graph():
    a = Node(name="A", cls="X", pins=[
        Pin(name="Out", cpp_type="exec", direction="Output"),
        Pin(name="Scale", cpp_type="double", direction="Input", default_value="1.000000"),
    ])
    b = Node(name="B", cls="X", pins=[Pin(name="In", cpp_type="exec", direction="Input")])
    return GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")])


def test_show_node_lists_pins(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    assert panel.pin_count() == 2


def test_connected_pin_marked(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    assert panel.is_pin_connected("Out") is True
    assert panel.is_pin_connected("Scale") is False


def test_changed_pin_marked(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    assert panel.is_pin_changed("Scale") is True
    assert panel.is_pin_changed("Out") is False


def test_navigate_signal_on_connected_pin(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    g = _graph()
    panel.show_node(g.node_by_name("A"), g)
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_pin("Out")
    assert sig.args == ["B"]


def test_clear_when_none(qtbot):
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(None, _graph())
    assert panel.pin_count() == 0
