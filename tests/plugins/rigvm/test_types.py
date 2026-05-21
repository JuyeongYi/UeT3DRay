from t3dgraph.plugins.rigvm import types as t


def test_node_class_detection():
    assert t.is_node_class("/Script/RigVMDeveloper.RigVMUnitNode")
    assert t.is_node_class("/Script/RigVMDeveloper.RigVMDispatchNode")
    assert not t.is_node_class("/Script/RigVMDeveloper.RigVMPin")


def test_link_class_detection():
    assert t.is_link_class("/Script/RigVMDeveloper.RigVMLink")
    assert not t.is_link_class("/Script/RigVMDeveloper.RigVMUnitNode")


def test_execution_pin_by_cpp_type():
    assert t.is_execution_cpp_type("FRigVMExecuteContext")
    assert not t.is_execution_cpp_type("double")


def test_is_graph_class_true():
    assert t.is_graph_class("/Script/RigVMDeveloper.RigVMGraph") is True


def test_is_graph_class_false_for_node():
    assert t.is_graph_class("/Script/RigVMDeveloper.RigVMUnitNode") is False


def test_is_graph_class_false_for_none():
    assert t.is_graph_class(None) is False
