from t3dgraph.core.analysis.data_flow import (
    analyze_data_flow, DataFlowResult, DataFlowEdge, dependency_tree,
)
from t3dgraph.core.base.pin_ref import PinRef
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
    assert any(e.source.node == "Src" and e.target.node == "Dst" for e in r.data_edges)
    assert not any(e.source.node == "ExecA" and e.target.node == "ExecB" for e in r.data_edges)


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
    assert sorted(r.incoming_nodes["C"]) == ["A", "B"]
    assert r.outgoing_nodes["A"] == ["C"]
    assert r.outgoing_nodes["B"] == ["C"]


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
    assert any(e.source.node == "A" and e.target.node == "B" for e in r.data_edges)
    assert any(e.source.node == "B" and e.target.node == "A" for e in r.data_edges)


def test_dependency_tree_basic():
    incoming = {
        "Sink": ["Mul"],
        "Mul": ["A", "B"],
        "A": [],
        "B": [],
    }
    tree = dependency_tree("Sink", incoming)
    assert tree.node == "Sink"
    children = [c.node for c in tree.children]
    assert children == ["Mul"]
    leaf_kids = [c.node for c in tree.children[0].children]
    assert sorted(leaf_kids) == ["A", "B"]


def test_dependency_tree_cycle_protection():
    incoming = {
        "A": ["B"],
        "B": ["A"],
    }
    tree = dependency_tree("A", incoming, max_depth=10)

    def walk(n, seen):
        seen.append(n.node)
        for c in n.children:
            walk(c, seen)

    seen = []
    walk(tree, seen)
    assert seen.count("A") == 1


# ---- 신규 테스트 (핀 단위 정보 보존 PRESERVE-INFO) ----

def test_data_edges_carry_pin_refs():
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None, pins=[_data_pin("Out", "Output")]),
            Node(name="B", cls=None, pins=[_data_pin("In", "Input")]),
        ],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )
    r = analyze_data_flow(g)
    assert len(r.data_edges) == 1
    e = r.data_edges[0]
    assert isinstance(e, DataFlowEdge)
    assert e.source == PinRef(node="A", pin_path="Out")
    assert e.target == PinRef(node="B", pin_path="In")


def test_multiple_links_same_node_pair_each_preserved():
    """같은 노드 쌍, 다른 핀 — 두 엣지 모두 보존(PRESERVE-INFO)."""
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[_data_pin("O1", "Output"), _data_pin("O2", "Output")]),
            Node(name="B", cls=None,
                 pins=[_data_pin("I1", "Input"), _data_pin("I2", "Input")]),
        ],
        links=[
            Link(source_path="A.O1", target_path="B.I1"),
            Link(source_path="A.O2", target_path="B.I2"),
        ],
    )
    r = analyze_data_flow(g)
    assert len(r.data_edges) == 2
    assert r.incoming_nodes["B"] == ["A"]


def test_inputs_of_holds_edges_no_duplication():
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None,
                 pins=[_data_pin("O1", "Output"), _data_pin("O2", "Output")]),
            Node(name="B", cls=None,
                 pins=[_data_pin("I1", "Input"), _data_pin("I2", "Input")]),
        ],
        links=[
            Link(source_path="A.O1", target_path="B.I1"),
            Link(source_path="A.O2", target_path="B.I2"),
        ],
    )
    r = analyze_data_flow(g)
    assert len(r.inputs_of["B"]) == 2
    assert all(isinstance(e, DataFlowEdge) for e in r.inputs_of["B"])
    assert r.incoming_nodes["B"] == ["A"]


def test_sinks_and_sources_node_level_unchanged():
    """노드 단위 sinks/sources는 batch ②와 동일 의미 보존."""
    g = GraphModel(
        nodes=[
            Node(name="Src", cls=None, pins=[_data_pin("O", "Output")]),
            Node(name="Mid", cls=None,
                 pins=[_data_pin("I", "Input"), _data_pin("O", "Output")]),
            Node(name="Snk", cls=None, pins=[_data_pin("I", "Input")]),
        ],
        links=[
            Link(source_path="Src.O", target_path="Mid.I"),
            Link(source_path="Mid.O", target_path="Snk.I"),
        ],
    )
    r = analyze_data_flow(g)
    assert r.sources == ["Src"]
    assert r.sinks == ["Snk"]


# g8 (F30) — isolated 판정에서 exec 연결도 포함

def test_entry_with_only_exec_not_isolated() -> None:
    """Entry 노드가 exec link로만 연결돼도 isolated 아님."""
    entry = _node("Entry", _exec_pin("ExecuteContext", "Output"))
    body = _node("Body",
                 _exec_pin("ExecuteContext", "Input"),
                 _data_pin("A", "Input"),
                 _data_pin("B", "Output"))
    consumer = _node("Consumer", _data_pin("B", "Input"))
    g = GraphModel(
        nodes=[entry, body, consumer],
        links=[
            Link(source_path="Entry.ExecuteContext", target_path="Body.ExecuteContext"),
            Link(source_path="Body.B", target_path="Consumer.B"),
        ],
    )
    result = analyze_data_flow(g)
    assert "Entry" not in result.isolated, (
        f"Entry는 exec link로 연결됨 — isolated 잘못 표시: {result.isolated}"
    )


def test_return_with_only_exec_not_isolated() -> None:
    """Return 노드가 exec link로만 들어와도 isolated 아님."""
    src = _node("Src", _exec_pin("ExecOut", "Output"))
    return_node = _node("Return", _exec_pin("ExecIn", "Input"))
    g = GraphModel(
        nodes=[src, return_node],
        links=[Link(source_path="Src.ExecOut", target_path="Return.ExecIn")],
    )
    result = analyze_data_flow(g)
    assert "Return" not in result.isolated


def test_node_with_no_link_is_isolated() -> None:
    """진짜 link가 0인 노드는 isolated 유지 (회귀 없음)."""
    floating = _node("Floating", _data_pin("A", "Input"))
    g = GraphModel(nodes=[floating], links=[])
    result = analyze_data_flow(g)
    assert "Floating" in result.isolated


def test_data_flow_edges_unchanged_by_isolated_fix() -> None:
    """isolated 검사 변경이 data_edges (exec 제외)에 영향 없음."""
    entry = _node("Entry", _exec_pin("ExecOut", "Output"))
    body = _node("Body",
                 _exec_pin("ExecIn", "Input"),
                 _data_pin("Result", "Output"))
    consumer = _node("Consumer", _data_pin("In", "Input"))
    g = GraphModel(
        nodes=[entry, body, consumer],
        links=[
            Link(source_path="Entry.ExecOut", target_path="Body.ExecIn"),
            Link(source_path="Body.Result", target_path="Consumer.In"),
        ],
    )
    result = analyze_data_flow(g)
    assert len(result.data_edges) == 1
    edge_paths = [(e.source_node, e.target_node) for e in result.data_edges]
    assert ("Body", "Consumer") in edge_paths
