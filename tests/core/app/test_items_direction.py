"""g1 (F21) — Direction-aware 렌더링."""
from PySide6.QtWidgets import QGraphicsEllipseItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem, collect_pin_rows


def _dots_on_side(item: NodeItem, x_threshold: float, *, left: bool) -> int:
    """left=True면 x < threshold, False면 x > threshold."""
    n = 0
    for c in item.childItems():
        if not isinstance(c, QGraphicsEllipseItem):
            continue
        cx = c.rect().center().x()
        if (left and cx < x_threshold) or (not left and cx > x_threshold):
            n += 1
    return n


def test_hidden_pin_no_dot(qtbot) -> None:
    n = Node(name="N", cls="T",
             pins=[Pin(name="Cfg", cpp_type="bool", direction="Hidden")])
    item = NodeItem(n)
    # Hidden → dot 0개
    assert _dots_on_side(item, 100, left=True) == 0
    assert _dots_on_side(item, 100, left=False) == 0


def test_io_pin_both_sides(qtbot) -> None:
    n = Node(name="N", cls="T",
             pins=[Pin(name="Exec", cpp_type="FRigVMExecuteContext",
                       direction="IO", is_execution=True)])
    item = NodeItem(n)
    assert _dots_on_side(item, 100, left=True) == 1
    assert _dots_on_side(item, 100, left=False) == 1


def test_output_subpin_inherits_parent_direction(qtbot) -> None:
    sub_x = Pin(name="X", cpp_type="float", direction=None)
    sub_y = Pin(name="Y", cpp_type="float", direction=None)
    parent = Pin(name="Out", cpp_type="FVector", direction="Output",
                 subpins=[sub_x, sub_y])
    n = Node(name="N", cls="T", pins=[parent])
    item = NodeItem(n, expanded_paths=frozenset({"N.Out"}))
    # 부모와 자식 모두 RIGHT — 좌측 dot 0개, 우측 2개 이상 (subpin 최소 2, 부모는 has_dot=False when expanded)
    assert _dots_on_side(item, 100, left=True) == 0
    assert _dots_on_side(item, 100, left=False) >= 2


def test_input_unchanged(qtbot) -> None:
    n = Node(name="N", cls="T",
             pins=[Pin(name="In", cpp_type="bool", direction="Input")])
    item = NodeItem(n)
    assert _dots_on_side(item, 100, left=True) == 1


def test_hidden_pin_label_muted(qtbot) -> None:
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    n = Node(name="N", cls="T",
             pins=[Pin(name="Cfg", cpp_type="bool", direction="Hidden")])
    item = NodeItem(n)
    # 라벨 'Cfg'의 brush 색이 muted (#969696 또는 그 근사)
    label = next(c for c in item.childItems()
                 if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "Cfg")
    color = label.brush().color()
    # 일반 라벨(#D2D2D2)보다 어두움
    assert color.lightness() < 180
