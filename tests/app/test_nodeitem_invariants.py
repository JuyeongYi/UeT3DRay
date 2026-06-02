"""v2-A1 — NodeItem cached state setter."""
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def test_update_state_changes_subsequent_rebuild(qtbot) -> None:
    """update_state() 후 set_expanded_paths()가 새 connected/changed set으로 재구성."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    item = NodeItem(n)   # 기본 빈 set
    item.set_expanded_paths(frozenset({"N.Pos"}))
    item.update_state(connected_paths=frozenset(),
                      changed_paths=frozenset({"N.Pos.X"}),
                      pin_colors=None)
    # 같은 expanded set으로 재호출하면 no-op이므로 먼저 접은 뒤 다시 펼친다
    item.set_expanded_paths(frozenset())
    item.set_expanded_paths(frozenset({"N.Pos"}))
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    bold_labels = [
        c.text() for c in item.childItems()
        if isinstance(c, QGraphicsSimpleTextItem) and c.font().bold()
    ]
    assert "X" in bold_labels or any(
        "X" in t for t in bold_labels
    ), f"changed_paths setter 효과 없음 — bold_labels={bold_labels}"


def test_update_state_no_op_when_unchanged(qtbot) -> None:
    """동일 set/색 재호출은 변화 없음 (idempotent)."""
    n = Node(name="N", cls="X", pins=[Pin(name="P", cpp_type="float", direction="Input")])
    item = NodeItem(n)
    cnt_before = len(item.childItems())
    item.update_state(connected_paths=frozenset(),
                      changed_paths=frozenset(),
                      pin_colors=None)
    assert len(item.childItems()) == cnt_before
