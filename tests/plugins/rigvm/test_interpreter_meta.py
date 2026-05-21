from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.values import QuotedString
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_interpret_fills_display_name_and_role():
    obj = T3DObject(
        cls="/Script/RigVMDeveloper.RigVMUnitNode",
        name="RigUnit_BeginExecution",
        export_path=None,
        header_raw="",
        properties={"ScriptStruct": QuotedString("/Script/ControlRig.RigUnit_BeginExecution")},
        children=[],
    )
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1
    n = g.nodes[0]
    assert n.name == "RigUnit_BeginExecution"
    assert n.display_name == "Begin Execution"
    assert n.role_summary == "RigUnit_BeginExecution"
    assert n.role_category == "Unit"


def test_interpret_preserves_node_even_when_meta_missing():
    """PRESERVE-ALL: 메타 결정 실패해도 노드는 그대로."""
    obj = T3DObject(
        cls="/Script/RigVMDeveloper.RigVMUnitNode",
        name="X",
        export_path=None,
        header_raw="",
        properties={},
        children=[],
    )
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1
    n = g.nodes[0]
    assert n.name == "X"
    assert n.display_name == "X"  # fallback to name
    assert n.role_category == "Unit"
