from t3dgraph.core.t3d.paths import node_of, pin_segment, type_suffix


def test_node_of():
    assert node_of("Node.Pin.Sub") == "Node"
    assert node_of("Solo") == "Solo"


def test_pin_segment():
    assert pin_segment("Node.Pin.Sub", 0) == "Node"
    assert pin_segment("Node.Pin.Sub", 1) == "Pin"
    assert pin_segment("Node.Pin.Sub", 2) == "Sub"
    assert pin_segment("Node", 1) == ""


def test_type_suffix():
    assert type_suffix("/Script/RigVMDeveloper.RigVMUnitNode") == "RigVMUnitNode"
    assert type_suffix(None) == "?"
