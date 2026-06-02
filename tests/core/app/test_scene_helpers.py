from t3dgraph.core.app.scene import _connected_paths_by_node
from t3dgraph.core.base.graph_model import GraphModel, Node, Link


def test_connected_paths_includes_parent_prefixes():
    g = GraphModel(
        nodes=[Node(name="A", cls=None), Node(name="B", cls=None)],
        links=[Link(source_path="A.OutPin.Sub", target_path="B.InPin")],
    )
    by_node = _connected_paths_by_node(g)
    assert "A.OutPin.Sub" in by_node["A"]
    assert "A.OutPin" in by_node["A"]  # prefix closure
    assert "B.InPin" in by_node["B"]
