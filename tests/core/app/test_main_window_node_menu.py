"""F18 + F19 MainWindow 통합 — 노드 컨텍스트 메뉴 액션 및 LayoutOverrides 흐름."""
from __future__ import annotations
from PySide6.QtCore import QPointF, QPoint

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin
from t3dgraph.core.app.main_window import MainWindow


def _graph() -> GraphModel:
    sub_a = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="P", cpp_type="FVector", direction="Input", subpins=[sub_a])
    n1 = Node(name="N1", cls="T", pins=[parent], position=(0.0, 0.0))
    n2 = Node(name="N2", cls="T", pins=[], position=(300.0, 0.0))
    return GraphModel(nodes=[n1, n2], label="root")


def test_expand_node_pins_via_action(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    w._invoke_node_action("N1", "expand_all")
    assert "N1.P" in w.view_state.expanded_pin_paths
    assert "N1.P.X" in w.view_state.expanded_pin_paths


def test_collapse_node_pins_via_action(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    w._invoke_node_action("N1", "expand_all")
    w._invoke_node_action("N1", "collapse_all")
    assert not any(p.startswith("N1.") for p in w.view_state.expanded_pin_paths)


def test_reset_position_clears_override(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    key = w._current_graph_key()
    w.layout_overrides.set(key, "N1", 500.0, 500.0)
    w._invoke_node_action("N1", "reset_position")
    assert w.layout_overrides.get(key, "N1") is None


def test_position_changed_updates_overrides(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    item = w.scene.node_item("N1")
    assert item is not None
    item.setPos(QPointF(123.0, 45.0))
    key = w._current_graph_key()
    assert w.layout_overrides.get(key, "N1") == (123.0, 45.0)


def test_override_survives_rebuild(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph())
    item = w.scene.node_item("N1")
    assert item is not None
    item.setPos(QPointF(123.0, 45.0))
    w._rebuild_scene()
    item2 = w.scene.node_item("N1")
    assert item2 is not None
    assert item2.pos() == QPointF(123.0, 45.0)
