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
