from t3dgraph.core.app.view_state import ViewState
from t3dgraph.core.app.persistent_state import GraphState


def test_defaults():
    vs = ViewState()
    assert vs.selected_node is None
    assert vs.hidden_node_types == set()


def test_no_observer_api():
    vs = ViewState()
    assert not hasattr(vs, "subscribe")
    assert not hasattr(vs, "_notify")


def test_select_sets_value():
    vs = ViewState()
    vs.select("NodeA")
    assert vs.selected_node == "NodeA"


def test_set_type_hidden_toggles():
    vs = ViewState()
    vs.set_type_hidden("X", True)
    assert vs.is_type_hidden("X") is True
    vs.set_type_hidden("X", False)
    assert vs.is_type_hidden("X") is False


def test_is_type_hidden():
    vs = ViewState()
    vs.set_type_hidden("X", True)
    assert vs.is_type_hidden("X") is True
    assert vs.is_type_hidden("Y") is False


def test_view_mode_defaults_false():
    vs = ViewState()
    assert vs.connected_pins_only is False
    assert vs.fan_in_highlight is False


def test_view_mode_setters():
    vs = ViewState()
    vs.set_connected_pins_only(True)
    vs.set_fan_in_highlight(True)
    assert (vs.connected_pins_only, vs.fan_in_highlight) == (True, True)


def test_set_fan_in_highlight():
    vs = ViewState()
    vs.set_fan_in_highlight(True)
    assert vs.fan_in_highlight is True


def test_pin_expand_toggle_round_trip():
    vs = ViewState()
    path = "MyNode.MyPin"
    assert vs.is_pin_expanded(path) is False
    vs.toggle_pin_expanded(path)
    assert vs.is_pin_expanded(path) is True
    vs.toggle_pin_expanded(path)
    assert vs.is_pin_expanded(path) is False


def test_expand_all_and_collapse_all():
    vs = ViewState()
    vs.expand_all_pins(["N.A", "N.B", "N.A.X"])
    assert vs.is_pin_expanded("N.A") is True
    assert vs.is_pin_expanded("N.B") is True
    assert vs.is_pin_expanded("N.A.X") is True
    vs.collapse_all_pins()
    assert vs.is_pin_expanded("N.A") is False


def test_view_state_from_graph_state() -> None:
    gs = GraphState(
        connected_pins_only=True,
        fan_in_highlight=True,
        expanded_pin_paths=["N.A", "N.B"],
        hidden_node_types=["sequence"],
        node_positions={"N": (1.0, 2.0)},
    )
    vs = ViewState.from_graph_state(gs)
    assert vs.connected_pins_only is True
    assert vs.fan_in_highlight is True
    assert vs.expanded_pin_paths == {"N.A", "N.B"}
    assert vs.hidden_node_types == {"sequence"}
    assert vs.selected_node is None
