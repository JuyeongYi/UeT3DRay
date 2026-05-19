from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.flow import analyze_flow


def _exec_pin(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=direction, is_execution=True)


def _node(name, *pins):
    return Node(name=name, cls="RigVMUnitNode", pins=list(pins))


def _fan_in_graph():
    a = _node("A", _exec_pin("Out", "Output"))
    b = _node("B", _exec_pin("Out", "Output"))
    c = _node("C", _exec_pin("In", "Input"), _exec_pin("Out", "Output"))
    d = _node("D", _exec_pin("In", "Input"))
    links = [
        Link("A.Out", "C.In"),
        Link("B.Out", "C.In"),
        Link("C.Out", "D.In"),
    ]
    return GraphModel(nodes=[a, b, c, d], links=links)


def test_convergence_point_detected():
    r = analyze_flow(_fan_in_graph())
    assert r.convergence_points == ["C"]


def test_convergence_prefixes_and_downstream():
    r = analyze_flow(_fan_in_graph())
    conv = r.convergence("C")
    assert set(conv.incoming_nodes) == {"A", "B"}
    assert conv.common_downstream == ["D"]


def test_linear_graph_has_no_convergence():
    a = _node("A", _exec_pin("Out", "Output"))
    b = _node("B", _exec_pin("In", "Input"))
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")]))
    assert r.convergence_points == []


def test_data_links_ignored_for_flow():
    a = _node("A", Pin(name="V", cpp_type="double", direction="Output"))
    b = _node("B", Pin(name="V", cpp_type="double", direction="Input"))
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.V", "B.V")]))
    assert r.execution_edges == []


def test_flow_uses_abstract_is_execution_not_rigvm_string():
    a = Node(name="A", cls="X",
             pins=[Pin(name="O", cpp_type="SomeOtherExecType", direction="Output", is_execution=True)])
    b = Node(name="B", cls="X",
             pins=[Pin(name="I", cpp_type="SomeOtherExecType", direction="Input", is_execution=True)])
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")]))
    assert r.execution_edges == [("A", "B")]


def test_flow_ignores_rigvm_string_when_flag_false():
    a = Node(name="A", cls="X",
             pins=[Pin(name="O", cpp_type="FRigVMExecuteContext", direction="Output", is_execution=False)])
    b = Node(name="B", cls="X",
             pins=[Pin(name="I", cpp_type="FRigVMExecuteContext", direction="Input", is_execution=False)])
    r = analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")]))
    assert r.execution_edges == []
