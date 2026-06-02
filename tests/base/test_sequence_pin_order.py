"""u8 Task 1 — Sequence 노드는 Pins(N) 정렬 적용 안 함."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_sequence_node_preserves_t3d_order() -> None:
    """Sequence는 T3D 직렬(B, A) 순서 그대로. Pins(N) 무시."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="Seq"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="ExecuteContext"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Name="Seq"\n'
        '      ResolvedFunctionName="RigVMFunction_Sequence::Execute"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'ExecuteContext\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '      Pins(2)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    seq = g.node_by_name("Seq")
    pin_names = [p.name for p in seq.pins]
    # ExecuteContext가 첫 번째 (실행 핀 우선)
    assert pin_names[0] == "ExecuteContext"
    # 그 다음 B, A 순서 (Pins(N) 무시)
    assert pin_names[1:] == ["B", "A"], (
        f"Sequence가 Pins(N) 정렬 적용됨 — pin_names={pin_names}"
    )


def test_non_sequence_node_uses_pins_n() -> None:
    """일반 노드는 g14 동작 그대로 — Pins(N) 적용."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="Regular"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="ExecuteContext"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Name="Regular"\n'
        '      ResolvedFunctionName="RigVMFunction_Add::Execute"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'ExecuteContext\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '      Pins(2)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    reg = g.node_by_name("Regular")
    pin_names = [p.name for p in reg.pins]
    # 일반 노드 — Pins(N) 적용 (A, B 순서)
    assert pin_names == ["ExecuteContext", "A", "B"]
