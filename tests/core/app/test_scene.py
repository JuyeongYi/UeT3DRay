from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.items import NodeItem, LinkItem


def _graph():
    a = Node(name="A", cls="X", position=(0.0, 0.0),
             pins=[Pin(name="O", cpp_type="exec", direction="Output")])
    b = Node(name="B", cls="X", position=(300.0, 0.0),
             pins=[Pin(name="I", cpp_type="exec", direction="Input")])
    return GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")])


def test_scene_creates_one_item_per_node(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    assert sum(isinstance(i, NodeItem) for i in scene.items()) == 2


def test_scene_creates_one_link_item_per_link(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    assert sum(isinstance(i, LinkItem) for i in scene.items()) == 1


def test_scene_node_lookup(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    assert scene.node_item("A").node.name == "A"
    assert scene.node_item("Z") is None


def test_scene_repopulate_clears_previous(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    scene.populate(GraphModel(nodes=[Node(name="solo", cls="X")], links=[]))
    assert sum(isinstance(i, NodeItem) for i in scene.items()) == 1


def test_scene_link_to_unknown_node_skipped(qtbot):
    g = GraphModel(nodes=[Node(name="A", cls="X", pins=[Pin("O", "exec", "Output")])],
                   links=[Link("A.O", "Ghost.I")])
    scene = GraphScene()
    scene.populate(g)
    assert sum(isinstance(i, LinkItem) for i in scene.items()) == 0


def test_selected_node_name(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    scene.select_node("B")
    assert scene.selected_node_name() == "B"


def test_apply_hidden_types_hides_nodes(qtbot):
    from t3dgraph.core.base.graph_model import GraphModel, Node
    g = GraphModel(
        nodes=[Node(name="A", cls="/X.RigVMUnitNode", position=(0.0, 0.0)),
               Node(name="C", cls="/X.RigVMDispatchNode", position=(300.0, 0.0))],
        links=[],
    )
    scene = GraphScene()
    scene.populate(g)
    scene.apply_hidden_types({"RigVMUnitNode"})
    assert scene.node_item("A").isVisible() is False
    assert scene.node_item("C").isVisible() is True


def test_hidden_node_also_hides_its_links(qtbot):
    from t3dgraph.core.app.items import LinkItem
    scene = GraphScene()
    scene.populate(_graph())
    cls_suffix = _graph().nodes[0].cls.rsplit(".", 1)[-1] if _graph().nodes[0].cls else "?"
    scene.apply_hidden_types({cls_suffix})
    link_items = [i for i in scene.items() if isinstance(i, LinkItem)]
    assert all(not li.isVisible() for li in link_items)
