"""w1-C — 핀 토글이 scene rebuild 없이 in-place 처리."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene


def test_node_item_identity_preserved_after_toggle(qtbot) -> None:
    """핀 토글 후 NodeItem 객체 동일성 유지 (rebuild 아님)."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])

    scene = GraphScene()
    scene.populate(g)
    item_before = scene._nodes["N"]
    scene.update_node_expansion("N", frozenset({"N.Pos"}))
    item_after = scene._nodes["N"]
    assert item_after is item_before, "in-place rebuild 이 객체를 갈아끼웠다"
    # 자식 행이 늘어났는지 — rows에 N.Pos.X 포함
    assert "N.Pos.X" in item_after._rows


def test_link_endpoint_updates_after_neighbor_expansion(qtbot) -> None:
    """이웃 노드가 펼쳐지면 관련 LinkItem endpoint도 새 anchor로 이동."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    target = Node(name="T", cls="X", pins=[parent])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Pos.X")],
    )
    scene = GraphScene()
    scene.populate(g)
    link_item_before = scene._links[0][0]
    scene.update_node_expansion("T", frozenset({"T.Pos"}))
    target_item = scene._nodes["T"]
    new_anchor = target_item.pin_anchor("Pos.X", "Input")
    assert link_item_before._p2 == new_anchor or link_item_before.boundingRect().contains(new_anchor - link_item_before.pos())


def test_selection_preserved_across_pin_toggle(qtbot) -> None:
    """핀 토글 시 selection 유지."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    scene = GraphScene()
    scene.populate(g)
    scene._nodes["N"].setSelected(True)
    scene.update_node_expansion("N", frozenset({"N.Pos"}))
    assert scene._nodes["N"].isSelected()


def test_update_node_expansion_unknown_name_noop(qtbot) -> None:
    g = GraphModel(nodes=[Node(name="N", cls="X")])
    scene = GraphScene()
    scene.populate(g)
    scene.update_node_expansion("Unknown", frozenset())   # 폭발 없이 noop


def test_row_children_not_growing_on_repeated_toggle(qtbot) -> None:
    """expand → collapse → expand 반복 후 _row_children 수가 고정."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    scene = GraphScene()
    scene.populate(g)
    item = scene._nodes["N"]
    scene.update_node_expansion("N", frozenset({"N.Pos"}))
    count_after_first = len(item._row_children)
    scene.update_node_expansion("N", frozenset())           # 접기
    scene.update_node_expansion("N", frozenset({"N.Pos"}))  # 다시 펼치기
    assert len(item._row_children) == count_after_first
