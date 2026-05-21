from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.values import QuotedString
from t3dgraph.plugins.rigvm.role import role_for


def _obj(name, cls, **props):
    return T3DObject(cls=cls, name=name, export_path=None, header_raw="", properties=props, children=[])


def test_dispatch_signature_from_resolved():
    o = _obj(
        "RigVMDispatch_GetItemAtIndex_3",
        "/Script/RigVMDeveloper.RigVMDispatchNode",
        ResolvedFunctionName=QuotedString("GetItemAtIndex::Execute(in TArray<float> Array,in int32 Index,out float Item)"),
    )
    summary, category = role_for(o)
    assert summary == "GetItemAtIndex(TArray<float>, int32) → float"
    assert category == "Dispatch"


def test_unit_node_signature_falls_back_to_struct():
    o = _obj(
        "RigUnit_BeginExecution",
        "/Script/RigVMDeveloper.RigVMUnitNode",
        ScriptStruct=QuotedString("/Script/ControlRig.RigUnit_BeginExecution"),
    )
    summary, category = role_for(o)
    assert summary == "RigUnit_BeginExecution"
    assert category == "Unit"


def test_variable_role():
    o = _obj("RigVMVariableNode_4",
             "/Script/RigVMDeveloper.RigVMVariableNode")
    summary, category = role_for(o)
    assert summary is None
    assert category == "Variable"


def test_collapse_role():
    o = _obj("Physics", "/Script/RigVMDeveloper.RigVMCollapseNode")
    summary, category = role_for(o)
    assert summary is None
    assert category == "Subgraph"


def test_unknown_returns_none():
    o = _obj("X", None)
    assert role_for(o) == (None, None)
