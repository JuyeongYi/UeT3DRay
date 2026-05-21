from t3dgraph.core.base.pin_ref import PinRef


def test_parse_node_dot_pin():
    p = PinRef.parse("MyNode.MyPin")
    assert p.node == "MyNode"
    assert p.pin_path == "MyPin"
    assert p.full == "MyNode.MyPin"


def test_parse_deep_path():
    p = PinRef.parse("N.V.X")
    assert p.node == "N"
    assert p.pin_path == "V.X"
    assert p.full == "N.V.X"


def test_parse_node_only():
    p = PinRef.parse("Only")
    assert p.node == "Only"
    assert p.pin_path == ""
    assert p.full == "Only"


def test_frozen_hashable():
    p = PinRef(node="N", pin_path="P")
    s = {p, PinRef(node="N", pin_path="P")}
    assert len(s) == 1
