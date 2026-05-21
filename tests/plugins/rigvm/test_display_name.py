from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.values import Scalar, QuotedString
from t3dgraph.plugins.rigvm.display_name import display_name_for


def _obj(name, cls, **props):
    return T3DObject(cls=cls, name=name, export_path=None, header_raw="", properties=props, children=[])


def test_unit_node_strips_rigunit_prefix():
    o = _obj("RigUnit_BeginExecution",
             "/Script/RigVMDeveloper.RigVMUnitNode")
    assert display_name_for(o) == "Begin Execution"


def test_unit_node_camelcase_split():
    o = _obj("RigUnit_StepPhysicsSolver",
             "/Script/RigVMDeveloper.RigVMUnitNode")
    assert display_name_for(o) == "Step Physics Solver"


def test_dispatch_uses_resolved_function_prefix():
    o = _obj(
        "RigVMDispatch_GetItemAtIndex_3",
        "/Script/RigVMDeveloper.RigVMDispatchNode",
        ResolvedFunctionName=QuotedString("GetItemAtIndex::Execute(in Array,in Index,out Item)"),
    )
    assert display_name_for(o) == "Get Item At Index"


def test_dispatch_falls_back_to_template_notation():
    o = _obj(
        "RigVMDispatch_Foo_2",
        "/Script/RigVMDeveloper.RigVMDispatchNode",
        TemplateNotation=QuotedString("Foo(in A,in B,out Result)"),
    )
    assert display_name_for(o) == "Foo"


def test_variable_uses_variable_pin_default():
    var_pin = T3DObject(
        cls="/Script/RigVMDeveloper.RigVMPin",
        name="Variable",
        export_path=None,
        header_raw="",
        properties={"DefaultValue": QuotedString("IKTarget")},
        children=[],
    )
    o = T3DObject(
        cls="/Script/RigVMDeveloper.RigVMVariableNode",
        name="RigVMVariableNode_4",
        export_path=None,
        header_raw="",
        properties={},
        children=[var_pin],
    )
    assert display_name_for(o) == "IKTarget"


def test_unknown_falls_back_to_name():
    o = _obj("SomeWeird_5", "/Script/RigVMDeveloper.RigVMRerouteNode")
    assert display_name_for(o) == "SomeWeird_5"


def test_no_cls_returns_name():
    o = _obj("Anon", None)
    assert display_name_for(o) == "Anon"
