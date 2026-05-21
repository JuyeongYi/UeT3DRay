from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem, LinkItem, NODE_WIDTH, ROW_HEIGHT, HEADER_HEIGHT


def _node():
    return Node(
        name="N", cls="X", position=(100.0, 50.0),
        pins=[
            Pin(name="In", cpp_type="exec", direction="Input"),
            Pin(name="Out", cpp_type="exec", direction="Output"),
        ],
    )


def test_node_item_positioned_by_data(qtbot):
    item = NodeItem(_node())
    assert item.pos().x() == 100.0
    assert item.pos().y() == 50.0


def test_node_item_height_scales_with_pins(qtbot):
    item = NodeItem(_node())
    expected = HEADER_HEIGHT + 2 * ROW_HEIGHT
    assert item.rect().height() == expected
    assert item.rect().width() == NODE_WIDTH


def test_node_item_pin_anchor_input_on_left(qtbot):
    item = NodeItem(_node())
    anchor = item.pin_anchor("In", "Input")
    assert anchor.x() == 100.0
    assert anchor.y() == 50.0 + HEADER_HEIGHT + ROW_HEIGHT / 2


def test_node_item_pin_anchor_output_on_right(qtbot):
    item = NodeItem(_node())
    anchor = item.pin_anchor("Out", "Output")
    assert anchor.x() == 100.0 + NODE_WIDTH


def test_node_item_unknown_pin_anchor_falls_back_to_center(qtbot):
    item = NodeItem(_node())
    anchor = item.pin_anchor("Missing", "Input")
    assert anchor.x() == 100.0 + NODE_WIDTH / 2


def test_subpins_rendered_when_expanded(qtbot):
    sub = Pin(name="X", cpp_type="double", direction="Input")
    parent_pin = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[sub])
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[parent_pin])
    flat = NodeItem(node, expanded_paths=frozenset({"N.T"}))
    deep = NodeItem(node, expanded_paths=frozenset())
    assert flat.rect().height() == HEADER_HEIGHT + 2 * ROW_HEIGHT
    assert deep.rect().height() == HEADER_HEIGHT + 1 * ROW_HEIGHT


def test_connected_only_filters_unconnected_pins(qtbot):
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[
        Pin(name="A", cpp_type="exec", direction="Output"),
        Pin(name="B", cpp_type="double", direction="Input"),
    ])
    item = NodeItem(node, connected_paths=frozenset({"N.A"}), connected_only=True)
    assert item.rect().height() == HEADER_HEIGHT + 1 * ROW_HEIGHT
    assert item.has_pin_row("N.A") is True
    assert item.has_pin_row("N.B") is False


def test_highlighted_node_has_distinct_pen(qtbot):
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[])
    plain = NodeItem(node)
    hot = NodeItem(node, highlighted=True)
    assert hot.pen().color() != plain.pen().color()


def test_pin_anchor_uses_full_path_keying(qtbot):
    node = Node(name="N", cls="X", position=(100.0, 50.0), pins=[
        Pin(name="In", cpp_type="exec", direction="Input"),
    ])
    item = NodeItem(node)
    anchor = item.pin_anchor("In", "Input")
    assert anchor.x() == 100.0


def test_pin_anchor_resolves_subpin_when_expanded(qtbot):
    sub = Pin(name="X", cpp_type="double", direction="Input")
    parent = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[sub])
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[parent])
    item = NodeItem(node, expanded_paths=frozenset({"N.T"}))
    sub_anchor = item.pin_anchor("T.X", "Input")
    parent_anchor = item.pin_anchor("T", "Input")
    assert sub_anchor.y() != parent_anchor.y()


def test_pin_anchor_subpin_falls_back_to_parent_when_collapsed(qtbot):
    sub = Pin(name="X", cpp_type="double", direction="Input")
    parent = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[sub])
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[parent])
    item = NodeItem(node, expanded_paths=frozenset())
    assert item.pin_anchor("T.X", "Input").y() == item.pin_anchor("T", "Input").y()
