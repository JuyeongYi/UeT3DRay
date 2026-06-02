"""x1 — CustomProperties Pin directive skip."""
from pathlib import Path
import pytest
from t3dgraph.core.t3d.objects import parse_objects, T3DParseError
from t3dgraph.core.t3d.document import parse_document


_MINIMAL_REPRO = '''Begin Object Class=/Script/ControlRigDeveloper.ControlRigGraphNode Name="N"
   ModelNodePath="N"
   NodeGuid=4FBE5A5442B628385572068FB6616A3D
   CustomProperties Pin (PinId=20022E6E43C8E7C68AE8E8BB600B9F63,PinName="N.Result",PinFriendlyName="Result",Direction="EGPD_Output",PinType.PinCategory="real",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,LinkedTo=(RigUnit_SetTranslation_5 2466091D48C71EBA1D2EF4BB6AEED3DD,),PersistentGuid=00000000000000000000000000000000,bHidden=False,bOrphanedPin=False,)
End Object
'''


def test_custom_properties_pin_line_does_not_raise() -> None:
    """fix 전엔 'CustomProperties Pin (...)' 라인에서 폭발했음."""
    objs = parse_objects(_MINIMAL_REPRO)
    assert len(objs) == 1
    obj = objs[0]
    assert obj.name == "N"
    assert "CustomProperties Pin (PinId" not in obj.properties
    assert "CustomProperties" not in obj.properties
    assert "ModelNodePath" in obj.properties
    assert "NodeGuid" in obj.properties


def test_multiple_custom_properties_lines_all_skipped() -> None:
    """여러 줄 directive 모두 silent skip."""
    src = (
        'Begin Object Class=X Name="N"\n'
        '   CustomProperties Pin (PinId=AAA,PinName="P1",LinkedTo=(X Y,),)\n'
        '   CustomProperties Pin (PinId=BBB,PinName="P2",LinkedTo=(X Y,),)\n'
        '   CustomProperties Pin (PinId=CCC,PinName="P3",)\n'
        'End Object\n'
    )
    objs = parse_objects(src)
    assert len(objs) == 1
    assert objs[0].properties == {}


def test_custom_properties_other_subtypes_skipped() -> None:
    """`CustomProperties Foo (...)` 형도 동일 패턴이면 skip."""
    src = (
        'Begin Object Class=X Name="N"\n'
        '   CustomProperties Foo (Something=1)\n'
        '   ModelNodePath="N"\n'
        'End Object\n'
    )
    objs = parse_objects(src)
    assert objs[0].properties.get("ModelNodePath") is not None
    assert "CustomProperties Foo" not in objs[0].properties


@pytest.mark.skipif(
    not Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").exists(),
    reason="repro file 미존재 환경 — smoke test skip",
)
def test_simple_face_ctrlrig_file_parses() -> None:
    """실제 repro 파일이 폭발 없이 parse_document 통과."""
    raw = Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").read_text(
        encoding="utf-16",
    )
    doc = parse_document(raw)
    assert doc is not None
