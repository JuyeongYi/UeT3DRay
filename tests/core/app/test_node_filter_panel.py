from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.node_filter_panel import NodeFilterPanel


def _graph():
    return GraphModel(nodes=[
        Node(name="A", cls="/Script/RigVMDeveloper.RigVMUnitNode"),
        Node(name="B", cls="/Script/RigVMDeveloper.RigVMUnitNode"),
        Node(name="C", cls="/Script/RigVMDeveloper.RigVMDispatchNode"),
    ])


def test_one_checkbox_per_distinct_type(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    assert set(panel.type_names()) == {"RigVMUnitNode", "RigVMDispatchNode"}


def test_all_checked_initially(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    assert all(panel.is_checked(t) for t in panel.type_names())


def test_uncheck_emits_toggled(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    with qtbot.waitSignal(panel.type_toggled, timeout=1000) as sig:
        panel.set_checked("RigVMUnitNode", False)
    assert sig.args == ["RigVMUnitNode", True]


def test_set_graph_rebuilds(qtbot):
    panel = NodeFilterPanel()
    qtbot.addWidget(panel)
    panel.set_graph(_graph())
    panel.set_graph(GraphModel(nodes=[Node(name="Z", cls="/X.RigVMRerouteNode")]))
    assert panel.type_names() == ["RigVMRerouteNode"]
