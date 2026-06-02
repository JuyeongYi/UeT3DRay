"""u6 — 수정된 핀 라벨 bold 표시."""
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _label_for(item, pin_name):
    for c in item.childItems():
        if isinstance(c, QGraphicsSimpleTextItem) and c.text().startswith(pin_name):
            return c
    return None


def test_connected_pin_label_bold(qtbot) -> None:
    n = Node(name="N", cls="X",
             pins=[Pin(name="ConnectedPin", cpp_type="float",
                       direction="Input")])
    item = NodeItem(n, connected_paths=frozenset({"N.ConnectedPin"}))
    label = _label_for(item, "ConnectedPin")
    assert label is not None
    assert label.font().bold() is True


def test_changed_pin_label_bold(qtbot) -> None:
    n = Node(name="N", cls="X",
             pins=[Pin(name="ChangedPin", cpp_type="float",
                       direction="Input", default_value="42.5")])
    item = NodeItem(n, changed_paths=frozenset({"N.ChangedPin"}))
    label = _label_for(item, "ChangedPin")
    assert label is not None
    assert label.font().bold() is True


def test_unchanged_unconnected_pin_label_not_bold(qtbot) -> None:
    n = Node(name="N", cls="X",
             pins=[Pin(name="DefaultPin", cpp_type="float",
                       direction="Input", default_value="0.0")])
    item = NodeItem(n)
    label = _label_for(item, "DefaultPin")
    assert label is not None
    assert label.font().bold() is False


def test_exec_pin_still_bold(qtbot) -> None:
    """exec 핀은 기존대로 bold (F26 회귀 없음)."""
    n = Node(name="N", cls="X",
             pins=[Pin(name="Exec", cpp_type="FRigVMExecuteContext",
                       direction="Output", is_execution=True)])
    item = NodeItem(n)
    label = _label_for(item, "Exec")
    assert label is not None
    assert label.font().bold() is True
