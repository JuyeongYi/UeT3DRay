"""ν slice reviewer fixes — regression guard (I-1 ~ I-6)."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsScene

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.layout_overrides import LayoutOverrides
from t3dgraph.core.app.view_state import ViewState
from t3dgraph.core.app.main_window import MainWindow


# ── I-1: _populating try/finally ─────────────────────────────────────────────

def test_populating_flag_false_after_populate(qtbot) -> None:
    """populate 완료 후 _populating 이 False 여야 한다."""
    scene = GraphScene()
    g = GraphModel(nodes=[Node("N", "T", pins=[])], label="t")
    scene.populate(g)
    assert scene._populating is False


def test_drag_emits_after_populate(qtbot) -> None:
    """populate 완료 후 setPos 는 position_changed 를 방출한다."""
    scene = GraphScene()
    g = GraphModel(nodes=[Node("N", "T", pins=[], position=(0., 0.))], label="t")
    scene.populate(g)
    received: list[str] = []
    scene.node_position_changed.connect(lambda n, *_: received.append(n))
    scene.node_item("N").setPos(QPointF(50., 50.))
    assert received == ["N"]


# ── I-2: link follows drag ────────────────────────────────────────────────────

def test_link_path_updates_after_node_drag(qtbot) -> None:
    """소스 노드 드래그 후 링크 bezier path 의 시작점이 이동한다."""
    pin_src = Pin(name="Out", cpp_type="bool", direction="Output")
    pin_dst = Pin(name="In", cpp_type="bool", direction="Input")
    n1 = Node(name="Src", cls="T", pins=[pin_src], position=(0., 0.))
    n2 = Node(name="Dst", cls="T", pins=[pin_dst], position=(300., 0.))
    lnk = Link(source_path="Src.Out", target_path="Dst.In")
    g = GraphModel(nodes=[n1, n2], links=[lnk], label="t")

    scene = GraphScene()
    scene.populate(g)

    link_item = scene._links[0][0]
    path_before = link_item.path().elementAt(0)

    scene.node_item("Src").setPos(QPointF(0., 100.))
    path_after = link_item.path().elementAt(0)

    assert path_after.y != pytest.approx(path_before.y)


# ── I-3/I-4: stable token, non-active tab close ──────────────────────────────

def test_non_active_tab_close_preserves_active_overrides(qtbot) -> None:
    """비활성 탭 close 가 활성 탭의 overrides 를 삭제하지 않는다."""
    w = MainWindow()
    qtbot.addWidget(w)
    g1 = GraphModel(nodes=[Node("A", "T", pins=[], position=(0., 0.))], label="G1")
    g2 = GraphModel(nodes=[Node("B", "T", pins=[], position=(0., 0.))], label="G2")
    w.open_graph(g1)  # tab 0
    w.open_graph(g2)  # tab 1, now active

    key2 = w._current_graph_key()
    w.layout_overrides.set(key2, "B", 100., 100.)

    # Close tab 0 (g1, non-active) — active tab is still g2
    w._on_tab_close(0)

    # G2's override must survive
    # After close, g2 is now tab 0 but token is unchanged
    assert w.layout_overrides.get(w._current_graph_key(), "B") == (100., 100.)


def test_active_tab_key_stable_after_left_tab_close(qtbot) -> None:
    """왼쪽 탭 제거 후에도 잔존 탭의 graph_key(토큰 기반)가 변하지 않는다."""
    w = MainWindow()
    qtbot.addWidget(w)
    g1 = GraphModel(nodes=[], label="G1")
    g2 = GraphModel(nodes=[Node("B", "T", pins=[], position=(0., 0.))], label="G2")
    w.open_graph(g1)
    w.open_graph(g2)  # tab 1, active

    key_before = w._current_graph_key()

    # Close tab 0 — g2 becomes tab 0, but token must stay same
    w._on_tab_close(0)

    key_after = w._current_graph_key()
    assert key_before == key_after


# ── I-5: clear_by_prefix ─────────────────────────────────────────────────────

def test_clear_by_prefix_removes_matching_keys() -> None:
    lo = LayoutOverrides()
    lo.set("0/G/", "N1", 1., 1.)
    lo.set("0/G/sub", "N2", 2., 2.)
    lo.set("1/G/", "N3", 3., 3.)
    lo.clear_by_prefix("0/")
    assert lo.get("0/G/", "N1") is None
    assert lo.get("0/G/sub", "N2") is None
    assert lo.get("1/G/", "N3") == (3., 3.)


# ── I-6: expand_node_pins prefix filter ──────────────────────────────────────

def test_expand_node_pins_ignores_other_node_paths() -> None:
    """다른 노드 prefix 의 경로는 expand_node_pins 에서 무시된다."""
    vs = ViewState()
    vs.expand_node_pins("N1", ["N1.P", "N2.Q"])  # N2.Q should be filtered out
    assert "N1.P" in vs.expanded_pin_paths
    assert "N2.Q" not in vs.expanded_pin_paths
