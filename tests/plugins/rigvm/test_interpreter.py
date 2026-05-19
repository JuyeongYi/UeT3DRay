from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter

LINK_SRC = (
    'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
    '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Exec"\n'
    '   End Object\n'
    'End Object\n'
    'Begin Object Name="A"\n'
    '   Begin Object Name="Exec"\n'
    '      Direction=Output\n'
    '      CPPType="FRigVMExecuteContext"\n'
    '   End Object\n'
    '   Position=(X=10.000000,Y=-20.000000)\n'
    'End Object\n'
    'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
    '   SourcePinPath="A.Exec"\n'
    '   TargetPinPath="B.Exec"\n'
    'End Object\n'
)


def test_nodes_and_pins():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    a = g.node_by_name("A")
    assert a is not None and a.cls.endswith("RigVMUnitNode")
    assert a.position == (10.0, -20.0)
    assert a.pins[0].name == "Exec"
    assert a.pins[0].cpp_type == "FRigVMExecuteContext"


def test_links_extracted():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    assert len(g.links) == 1
    assert g.links[0].source_path == "A.Exec"
    assert g.links[0].target_path == "B.Exec"


def test_unknown_class_becomes_generic_with_warning():
    src = 'Begin Object Class=/Script/RigVMDeveloper.RigVMFutureNode Name="F"\nEnd Object\n'
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.node_by_name("F").is_generic is True
    assert any("RigVMFutureNode" in w for w in g.warnings)


def test_variable_node_extracted():
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMVariableNode Name="V"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Variable"\n'
        '   End Object\n'
        'End Object\n'
        'Begin Object Name="V"\n'
        '   Begin Object Name="Variable"\n'
        '      DefaultValue="IKTarget"\n'
        '   End Object\n'
        'End Object\n'
    )
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.variable_refs[0].variable_name == "IKTarget"


def test_external_ref_recorded_for_unknown_target():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    # LINK_SRC: 링크 타깃 "B.Exec" 의 노드 B는 정의 안 됨
    assert "B.Exec" in g.external_refs


def test_real_rigvmmodel_file(orion_dir):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    g = RigVMGraphInterpreter().interpret(parse_document(f.read_text(encoding="utf-8")))
    assert len(g.nodes) > 0
    assert len(g.links) > 0


def test_interpreter_marks_execution_pins():
    g = RigVMGraphInterpreter().interpret(parse_document(LINK_SRC))
    exec_pin = g.node_by_name("A").pins[0]
    assert exec_pin.cpp_type == "FRigVMExecuteContext"
    assert exec_pin.is_execution is True


def test_interpreter_non_execution_pin_flag_false():
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="V"\n'
        '   End Object\n'
        'End Object\n'
        'Begin Object Name="A"\n'
        '   Begin Object Name="V"\n'
        '      CPPType="double"\n'
        '   End Object\n'
        'End Object\n'
    )
    g = RigVMGraphInterpreter().interpret(parse_document(src))
    assert g.node_by_name("A").pins[0].is_execution is False
