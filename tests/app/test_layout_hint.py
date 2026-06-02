"""k3 (batch ⑭) — NodeItem layout_hint 처리."""
from PySide6.QtWidgets import QGraphicsEllipseItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.app.node_profiles import NodeStyleProfile


def _dots_x(item: NodeItem) -> list[float]:
    return sorted(c.rect().center().x()
                  for c in item.childItems()
                  if isinstance(c, QGraphicsEllipseItem))


def test_outputs_only_puts_all_pins_right(qtbot) -> None:
    n = Node(name="Entry", cls="X",
             pins=[Pin(name="A", cpp_type="float", direction="Output"),
                   Pin(name="B", cpp_type="float", direction="Input"),
                   Pin(name="C", cpp_type="float", direction="Hidden")])
    profile = NodeStyleProfile(layout_hint="outputs_only")
    item = NodeItem(n, profile=profile)
    xs = _dots_x(item)
    # Hidden 핀은 dot 없음, A/B 모두 우측
    assert all(x > 50 for x in xs)   # 우측(NODE_WIDTH 근처)


def test_inputs_only_puts_all_pins_left(qtbot) -> None:
    n = Node(name="Return", cls="X",
             pins=[Pin(name="A", cpp_type="float", direction="Output"),
                   Pin(name="B", cpp_type="float", direction="Input")])
    profile = NodeStyleProfile(layout_hint="inputs_only")
    item = NodeItem(n, profile=profile)
    xs = _dots_x(item)
    # 모두 좌측
    assert all(x < 50 for x in xs)


def test_default_unchanged(qtbot) -> None:
    """default hint는 기존 동작 (direction에 따라 분리)."""
    n = Node(name="N", cls="X",
             pins=[Pin(name="A", cpp_type="float", direction="Output"),
                   Pin(name="B", cpp_type="float", direction="Input")])
    profile = NodeStyleProfile()   # default
    item = NodeItem(n, profile=profile)
    xs = _dots_x(item)
    # 둘로 분리 — 하나는 좌, 하나는 우
    assert len(xs) == 2
    assert xs[0] < 50 and xs[1] > 50


def test_passthrough_single_row(qtbot) -> None:
    """passthrough — 라벨 한 줄, 최소 폭. 핀 한 쌍만 표시."""
    n = Node(name="Reroute", cls="X",
             pins=[Pin(name="In", cpp_type="float", direction="Input"),
                   Pin(name="Out", cpp_type="float", direction="Output")])
    profile = NodeStyleProfile(layout_hint="passthrough")
    item = NodeItem(n, profile=profile)
    # 노드 높이가 단일 행 수준 (HEADER + ROW_HEIGHT 정도)
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT
    assert item.rect().height() <= HEADER_HEIGHT + ROW_HEIGHT + 5
