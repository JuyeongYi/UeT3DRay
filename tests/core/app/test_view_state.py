from t3dgraph.core.app.view_state import ViewState


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
    assert vs.expand_subpins is False
    assert vs.fan_in_highlight is False


def test_view_mode_setters():
    vs = ViewState()
    vs.set_connected_pins_only(True)
    vs.set_expand_subpins(True)
    vs.set_fan_in_highlight(True)
    assert (vs.connected_pins_only, vs.expand_subpins, vs.fan_in_highlight) == (True, True, True)


def test_set_expand_subpins_and_fan_in():
    vs = ViewState()
    vs.set_expand_subpins(True)
    vs.set_fan_in_highlight(True)
    assert vs.expand_subpins is True
    assert vs.fan_in_highlight is True
