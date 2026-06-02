"""u8 Task 2 — Sequence kind 노드는 핀 라벨 숨김."""
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _all_text_items(item):
    return [c for c in item.childItems() if isinstance(c, QGraphicsSimpleTextItem)]


def test_sequence_node_hides_pin_labels(qtbot) -> None:
    n = Node(
        name="Seq",
        cls="X",
        kind="sequence",
        pins=[
            Pin(name="ExecuteContext", cpp_type="FRigVMExecuteContext",
                direction="IO", is_execution=True),
            Pin(name="A", cpp_type="FRigVMExecuteContext",
                direction="Output", is_execution=True),
            Pin(name="B", cpp_type="FRigVMExecuteContext",
                direction="Output", is_execution=True),
        ],
    )
    item = NodeItem(n)
    texts = [t.text() for t in _all_text_items(item)]
    # 핀 이름 A·B는 표시 안 됨
    assert "A" not in texts
    assert "B" not in texts


def test_non_sequence_node_shows_pin_labels(qtbot) -> None:
    """sequence 외 노드는 라벨 그대로 표시 (회귀 없음)."""
    n = Node(
        name="Regular",
        cls="X",
        kind="node",
        pins=[Pin(name="DataIn", cpp_type="float", direction="Input")],
    )
    item = NodeItem(n)
    texts = [t.text() for t in _all_text_items(item)]
    assert "DataIn" in texts
