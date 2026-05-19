from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_build_and_lookup():
    p_out = Pin(name="ExecOut", cpp_type="FRigVMExecuteContext", direction="Output")
    p_in = Pin(name="ExecIn", cpp_type="FRigVMExecuteContext", direction="Input")
    a = Node(name="A", cls="UnitNode", pins=[p_out])
    b = Node(name="B", cls="UnitNode", pins=[p_in])
    link = Link(source_path="A.ExecOut", target_path="B.ExecIn")
    g = GraphModel(nodes=[a, b], links=[link])
    assert g.node_by_name("B") is b
    assert g.node_by_name("Z") is None


def test_pin_subpins_default_empty():
    assert Pin(name="X", cpp_type="double", direction="Input").subpins == []


def test_external_refs_recorded():
    g = GraphModel(nodes=[], links=[], external_refs=["IK_Rig.ExecuteContext"])
    assert "IK_Rig.ExecuteContext" in g.external_refs


def test_pin_is_execution_defaults_false():
    assert Pin(name="X", cpp_type="double", direction="Input").is_execution is False
