"""g10 (F32) — NodeItem 폭 자동 맞춤."""
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem, MIN_NODE_WIDTH, MAX_NODE_WIDTH


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_node_width_at_least_min(qapp) -> None:
    n = Node(name="X", cls="T")
    item = NodeItem(n)
    assert item._node_width >= MIN_NODE_WIDTH


def test_long_title_expands_width(qapp) -> None:
    """긴 display_name이 폭 확장."""
    short = Node(name="N", cls="T", display_name="X")
    long_ = Node(name="N", cls="T",
                 display_name="VeryLongFunctionNameThatExceedsDefault")
    short_item = NodeItem(short)
    long_item = NodeItem(long_)
    assert long_item._node_width > short_item._node_width


def test_long_pin_labels_expand_width(qapp) -> None:
    """긴 핀 라벨이 폭 확장."""
    short = Node(name="N", cls="T",
                 pins=[Pin(name="A", cpp_type="bool", direction="Input")])
    long_ = Node(name="N", cls="T",
                 pins=[Pin(name="VeryLongInputParameterName",
                           cpp_type="bool", direction="Input")])
    s = NodeItem(short)
    l = NodeItem(long_)
    assert l._node_width > s._node_width


def test_node_width_capped(qapp) -> None:
    """극단적으로 긴 라벨도 MAX_NODE_WIDTH로 제한."""
    n = Node(name="N", cls="T",
             pins=[Pin(name="A" * 200, cpp_type="bool", direction="Input")])
    item = NodeItem(n)
    assert item._node_width <= MAX_NODE_WIDTH


def test_pin_anchor_uses_instance_width(qapp) -> None:
    """pin_anchor가 instance node_width 기준으로 우측 좌표 반환."""
    from PySide6.QtCore import QPointF
    long_ = Node(name="N", cls="T",
                 pins=[Pin(name="LongPinName_AAAAAA", cpp_type="bool",
                           direction="Output")])
    item = NodeItem(long_)
    anchor = item.pin_anchor("LongPinName_AAAAAA", "Output")
    expected_x = item.pos().x() + item._node_width
    assert abs(anchor.x() - expected_x) < 1.0
