"""u2 통합 — 미니맵에서 임의 subgraph 진입."""
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow


def test_minimap_click_enters_subgraph(qtbot) -> None:
    leaf = GraphModel(label="leaf")
    root = GraphModel(
        label="root",
        nodes=[Node(name="Container", cls="X", subgraph=leaf)],
    )
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(root)
    # 미니맵에 leaf 항목 클릭
    w.minimap._click_for_test(0, leaf)
    assert w.graph_stack.current() is leaf


def test_minimap_click_sibling_subgraph(qtbot) -> None:
    """현재 path 아닌 형제 subgraph 클릭."""
    leaf_a = GraphModel(label="A")
    leaf_b = GraphModel(label="B")
    root = GraphModel(
        label="root",
        nodes=[
            Node(name="CA", cls="X", subgraph=leaf_a),
            Node(name="CB", cls="X", subgraph=leaf_b),
        ],
    )
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(root)
    w.minimap._click_for_test(0, leaf_a)
    assert w.graph_stack.current() is leaf_a
    # leaf_b로 직접 클릭 (다른 path)
    w.minimap._click_for_test(0, leaf_b)
    assert w.graph_stack.current() is leaf_b
