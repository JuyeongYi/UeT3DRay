"""u7 — 위상적 layered layout."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.auto_layout import hierarchical_arrange


def _exec(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def test_linear_chain_layers() -> None:
    """A -> B -> C 가 column 0, 1, 2에."""
    a = Node(name="A", cls="X", pins=[_exec("Out", "Output")])
    b = Node(name="B", cls="X",
             pins=[_exec("In", "Input"), _exec("Out", "Output")])
    c = Node(name="C", cls="X", pins=[_exec("In", "Input")])
    g = GraphModel(
        nodes=[a, b, c],
        links=[Link(source_path="A.Out", target_path="B.In"),
               Link(source_path="B.Out", target_path="C.In")],
    )
    positions = hierarchical_arrange(g)
    ax, _ = positions["A"]
    bx, _ = positions["B"]
    cx, _ = positions["C"]
    assert ax < bx < cx


def test_pin_order_determines_child_vertical_order() -> None:
    """A의 출력 핀 a(위), b(아래) — a에 연결된 X 위, b에 연결된 Y 아래."""
    a = Node(name="A", cls="X",
             pins=[
                 _exec("a", "Output"),
                 _exec("b", "Output"),
             ])
    x_node = Node(name="X", cls="X",
                  pins=[_exec("In", "Input")])
    y_node = Node(name="Y", cls="X",
                  pins=[_exec("In", "Input")])
    g = GraphModel(
        nodes=[a, x_node, y_node],
        links=[
            Link(source_path="A.a", target_path="X.In"),
            Link(source_path="A.b", target_path="Y.In"),
        ],
    )
    positions = hierarchical_arrange(g)
    _, x_y = positions["X"]
    _, y_y = positions["Y"]
    assert x_y < y_y, f"X y={x_y} should be above Y y={y_y}"


def test_unconnected_nodes_placed_separately() -> None:
    """exec link 없는 노드는 별도 위치(다른 column 또는 최하단)."""
    a = Node(name="A", cls="X")
    isolated = Node(name="Floating", cls="X")
    g = GraphModel(nodes=[a, isolated], links=[])
    positions = hierarchical_arrange(g)
    assert "A" in positions
    assert "Floating" in positions
    # 둘이 다른 위치
    assert positions["A"] != positions["Floating"]


def test_returns_dict_for_all_nodes() -> None:
    g = GraphModel(nodes=[
        Node(name="N1", cls="X"),
        Node(name="N2", cls="X"),
    ])
    positions = hierarchical_arrange(g)
    assert set(positions.keys()) == {"N1", "N2"}
