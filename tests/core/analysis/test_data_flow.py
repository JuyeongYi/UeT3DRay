from t3dgraph.core.analysis.data_flow import analyze_data_flow, DataFlowResult, dependency_tree
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def _node(name, *pins):
    return Node(name=name, cls=None, pins=list(pins))


def _data_pin(name, direction):
    return Pin(name=name, cpp_type="float", direction=direction, is_execution=False)


def _exec_pin(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def test_data_edges_exclude_exec_links():
    g = GraphModel(
        nodes=[
            _node("Src", _data_pin("Out", "Output")),
            _node("Dst", _data_pin("In", "Input")),
            _node("ExecA", _exec_pin("EOut", "Output")),
            _node("ExecB", _exec_pin("EIn", "Input")),
        ],
        links=[
            Link(source_path="Src.Out", target_path="Dst.In"),
            Link(source_path="ExecA.EOut", target_path="ExecB.EIn"),
        ],
    )
    r = analyze_data_flow(g)
    assert ("Src", "Dst") in r.data_edges
    assert ("ExecA", "ExecB") not in r.data_edges


def test_inputs_outputs_indices():
    g = GraphModel(
        nodes=[
            _node("A", _data_pin("O", "Output")),
            _node("B", _data_pin("O", "Output")),
            _node("C", _data_pin("I1", "Input"), _data_pin("I2", "Input")),
        ],
        links=[
            Link(source_path="A.O", target_path="C.I1"),
            Link(source_path="B.O", target_path="C.I2"),
        ],
    )
    r = analyze_data_flow(g)
    assert sorted(r.inputs_of["C"]) == ["A", "B"]
    assert r.outputs_of["A"] == ["C"]
    assert r.outputs_of["B"] == ["C"]


def test_sinks_and_sources():
    g = GraphModel(
        nodes=[
            _node("Const", _data_pin("Out", "Output")),
            _node("Compute", _data_pin("In", "Input"), _data_pin("Out", "Output")),
            _node("Sink", _data_pin("In", "Input")),
        ],
        links=[
            Link(source_path="Const.Out", target_path="Compute.In"),
            Link(source_path="Compute.Out", target_path="Sink.In"),
        ],
    )
    r = analyze_data_flow(g)
    assert r.sources == ["Const"]
    assert r.sinks == ["Sink"]


def test_isolated_nodes_in_all_nodes():
    """PRESERVE-ALL: 고립 노드도 결과에 모두 등장(고립 그룹용)."""
    g = GraphModel(
        nodes=[_node("X", _data_pin("In", "Input")), _node("Y", _data_pin("Out", "Output"))],
        links=[],
    )
    r = analyze_data_flow(g)
    assert set(r.all_nodes) == {"X", "Y"}
    assert r.isolated == ["X", "Y"]


def test_handles_cycles_without_recursion_blowup():
    g = GraphModel(
        nodes=[
            _node("A", _data_pin("I", "Input"), _data_pin("O", "Output")),
            _node("B", _data_pin("I", "Input"), _data_pin("O", "Output")),
        ],
        links=[
            Link(source_path="A.O", target_path="B.I"),
            Link(source_path="B.O", target_path="A.I"),
        ],
    )
    r = analyze_data_flow(g)
    assert ("A", "B") in r.data_edges
    assert ("B", "A") in r.data_edges


def test_dependency_tree_basic():
    inputs_of = {
        "Sink": ["Mul"],
        "Mul": ["A", "B"],
        "A": [],
        "B": [],
    }
    tree = dependency_tree("Sink", inputs_of)
    assert tree.node == "Sink"
    children = [c.node for c in tree.children]
    assert children == ["Mul"]
    leaf_kids = [c.node for c in tree.children[0].children]
    assert sorted(leaf_kids) == ["A", "B"]


def test_dependency_tree_cycle_protection():
    inputs_of = {
        "A": ["B"],
        "B": ["A"],
    }
    tree = dependency_tree("A", inputs_of, max_depth=10)

    def walk(n, seen):
        seen.append(n.node)
        for c in n.children:
            walk(c, seen)

    seen = []
    walk(tree, seen)
    assert seen.count("A") == 1
