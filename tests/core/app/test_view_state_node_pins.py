"""F19 ViewState 노드 단위 펼침/접기 helper."""
from __future__ import annotations

from t3dgraph.core.app.view_state import ViewState


def test_expand_node_pins_adds_paths() -> None:
    vs = ViewState()
    vs.expand_node_pins("N1", ["N1.P", "N1.P.X", "N1.P.Y"])
    assert vs.expanded_pin_paths == {"N1.P", "N1.P.X", "N1.P.Y"}


def test_collapse_node_pins_removes_node_paths_only() -> None:
    vs = ViewState()
    vs.expand_node_pins("N1", ["N1.P", "N1.P.X"])
    vs.expand_node_pins("N2", ["N2.Q"])
    vs.collapse_node_pins("N1")
    assert vs.expanded_pin_paths == {"N2.Q"}


def test_collapse_node_pins_noop_when_absent() -> None:
    vs = ViewState()
    vs.expand_node_pins("N2", ["N2.Q"])
    vs.collapse_node_pins("N1")
    assert vs.expanded_pin_paths == {"N2.Q"}
