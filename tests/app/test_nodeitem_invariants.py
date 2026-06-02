"""v2-A1/B1 — NodeItem cached state setter + header/row children separation."""
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


def test_header_children_not_cleared_on_rebuild(qtbot) -> None:
    """헤더 영역(title·chevron·badge)은 set_expanded_paths로 사라지지 않는다."""
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X.RigVMCollapseNode",
             pins=[parent], subgraph="dummy")
    item = NodeItem(n)
    headers_before = list(item._header_children)
    item.set_expanded_paths(frozenset({"N.Pos"}))
    headers_after = list(item._header_children)
    assert headers_before == headers_after
    for h in headers_after:
        if isinstance(h, QGraphicsSimpleTextItem):
            _ = h.text()


def test_row_children_replaced_on_rebuild(qtbot) -> None:
    """행 자식만 _clear_rows로 제거 + 새 _install_rows."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    item = NodeItem(n)
    rows_before = list(item._row_children)
    item.set_expanded_paths(frozenset({"N.Pos"}))
    rows_after = list(item._row_children)
    assert not any(r in rows_before for r in rows_after)
    assert len(rows_after) > len(rows_before)
