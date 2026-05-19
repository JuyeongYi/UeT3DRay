from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.execution_order import compute_execution_order


def _ep(name, d):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=d, is_execution=True)


def _n(name, *pins):
    return Node(name=name, cls="RigVMUnitNode", pins=list(pins))


def test_linear_order():
    a = _n("A", _ep("O", "Output"))
    b = _n("B", _ep("I", "Input"), _ep("O", "Output"))
    c = _n("C", _ep("I", "Input"))
    g = GraphModel(nodes=[a, b, c], links=[Link("A.O", "B.I"), Link("B.O", "C.I")])
    order = compute_execution_order(g)
    assert [step.node for step in order] == ["A", "B", "C"]
    assert [step.depth for step in order] == [0, 0, 0]


def test_branch_increases_depth():
    a = _n("A", _ep("O", "Output"))
    b = _n("B", _ep("I", "Input"))
    c = _n("C", _ep("I", "Input"))
    g = GraphModel(nodes=[a, b, c], links=[Link("A.O", "B.I"), Link("A.O", "C.I")])
    order = compute_execution_order(g)
    assert order[0].node == "A" and order[0].depth == 0
    assert {s.node for s in order[1:]} == {"B", "C"}
    assert all(s.depth == 1 for s in order[1:])


def test_empty_graph():
    assert compute_execution_order(GraphModel()) == []
