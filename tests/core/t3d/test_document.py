from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.values import Scalar

TWO_PHASE = (
    'Begin Object Class=/Script/X.Node Name="N"\n'
    '   Begin Object Class=/Script/X.Pin Name="P"\n'
    '   End Object\n'
    'End Object\n'
    'Begin Object Name="N"\n'
    '   Begin Object Name="P"\n'
    '      Direction=Output\n'
    '   End Object\n'
    '   Position=(X=1)\n'
    'End Object\n'
)


def test_two_phase_merge_unifies_object():
    doc = parse_document(TWO_PHASE)
    assert len(doc.objects) == 1
    n = doc.objects[0]
    assert n.cls == "/Script/X.Node"
    assert n.properties["Position"] is not None


def test_two_phase_merge_recurses_into_children():
    doc = parse_document(TWO_PHASE)
    pin = doc.objects[0].children[0]
    assert pin.cls == "/Script/X.Pin"
    assert pin.properties["Direction"] == Scalar("Output")


def test_real_file_parses(orion_dir):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    doc = parse_document(f.read_text(encoding="utf-8"))
    assert len(doc.objects) > 0
