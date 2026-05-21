from t3dgraph.core.base.paths import (
    node_of, pin_segment, pin_rel_path, type_suffix,
)


def test_node_of_basic():
    assert node_of("MyNode.Pin.Sub") == "MyNode"
    assert node_of("Only") == "Only"


def test_pin_segment_indices():
    assert pin_segment("A.B.C", 0) == "A"
    assert pin_segment("A.B.C", 1) == "B"
    assert pin_segment("A.B.C", 5) == ""


def test_pin_rel_path_strips_node_prefix():
    assert pin_rel_path("N", "N.Pin") == "Pin"
    assert pin_rel_path("N", "N.Pin.Sub") == "Pin.Sub"


def test_pin_rel_path_node_only_returns_empty():
    assert pin_rel_path("N", "N") == ""


def test_pin_rel_path_wrong_prefix_returns_empty():
    assert pin_rel_path("N", "M.Pin") == ""


def test_type_suffix_basic():
    assert type_suffix("/Script/X.RigVMUnitNode") == "RigVMUnitNode"
    assert type_suffix(None) == "?"
