"""g14 — Pins(N) / SubPins(N) 권위 순서 적용."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_pins_n_reorders_node_pins() -> None:
    """Pins(N) 속성이 B,A → A,B 순으로 재정렬."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="Seq"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="ExecuteContext"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Name="Seq"\n'
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
    assert pin_names == ["ExecuteContext", "A", "B"], (
        f"Pins(N) 무시 — pin_names={pin_names}"
    )


def test_pins_n_missing_preserves_original_order() -> None:
    """Pins(N) 속성 없으면 T3D 직렬 순서 유지."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="X"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Y"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    n = g.node_by_name("N")
    # exec 정렬 후 — exec 없으니 원순서
    assert [p.name for p in n.pins] == ["X", "Y"]


def test_pins_n_with_unknown_name_kept_at_end() -> None:
    """Pins(N)에 없는 핀은 권위 핀 뒤에 원순서로."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="C"\n'
        '   End Object\n'
        '   Begin Object Name="N"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    n = g.node_by_name("N")
    # B, A (권위), C (잔여 — 원순서)
    assert [p.name for p in n.pins] == ["B", "A", "C"]


def test_subpins_n_reorders_struct_subpins() -> None:
    """SubPins(N) 속성이 구조체 핀의 자식 순서를 정렬."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Struct"\n'
        '      Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Z"\n'
        '      End Object\n'
        '      Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="X"\n'
        '      End Object\n'
        '      Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="Y"\n'
        '      End Object\n'
        '      Begin Object Name="Struct"\n'
        '         SubPins(0)="/Script/RigVMDeveloper.RigVMPin\'X\'"\n'
        '         SubPins(1)="/Script/RigVMDeveloper.RigVMPin\'Y\'"\n'
        '         SubPins(2)="/Script/RigVMDeveloper.RigVMPin\'Z\'"\n'
        '      End Object\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    n = g.node_by_name("N")
    struct_pin = n.pins[0]
    sub_names = [sp.name for sp in struct_pin.subpins]
    assert sub_names == ["X", "Y", "Z"]
