from t3dgraph.core.app.view_state import ViewState


def test_defaults():
    vs = ViewState()
    assert vs.selected_node is None
    assert vs.hidden_node_types == set()


def test_select_notifies():
    vs = ViewState()
    seen = []
    vs.subscribe(lambda: seen.append(vs.selected_node))
    vs.select("NodeA")
    assert vs.selected_node == "NodeA"
    assert seen == ["NodeA"]


def test_set_type_hidden_toggles_and_notifies():
    vs = ViewState()
    calls = []
    vs.subscribe(lambda: calls.append(set(vs.hidden_node_types)))
    vs.set_type_hidden("RigVMUnitNode", True)
    vs.set_type_hidden("RigVMUnitNode", False)
    assert calls == [{"RigVMUnitNode"}, set()]


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


def test_set_connected_only_notifies():
    vs = ViewState()
    seen = []
    vs.subscribe(lambda: seen.append(vs.connected_pins_only))
    vs.set_connected_pins_only(True)
    assert vs.connected_pins_only is True
    assert seen == [True]


def test_set_expand_subpins_and_fan_in():
    vs = ViewState()
    vs.set_expand_subpins(True)
    vs.set_fan_in_highlight(True)
    assert vs.expand_subpins is True
    assert vs.fan_in_highlight is True
