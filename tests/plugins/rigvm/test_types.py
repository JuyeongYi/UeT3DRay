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
