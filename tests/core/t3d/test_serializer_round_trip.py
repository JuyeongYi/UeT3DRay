from pathlib import Path
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.serializer import serialize_document


def test_round_trip_simple():
    src = (
        'Begin Object Class=/Script/Foo.Bar Name="X"\n'
        '   Prop=1\n'
        '   Begin Object Class=/Script/Foo.Sub Name="Y"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    s = serialize_document(doc)
    doc2 = parse_document(s)
    assert len(doc.objects) == len(doc2.objects)
    a = doc.objects[0]; b = doc2.objects[0]
    assert a.name == b.name and a.cls == b.cls
    assert len(a.children) == len(b.children)


def test_round_trip_orion_sample():
    p = Path(__file__).parent.parent.parent / 'fixtures' / 'orion' / 'Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt'
    doc = parse_document(p.read_text(encoding='utf-8-sig'))
    s = serialize_document(doc)
    doc2 = parse_document(s)
    assert len(doc.objects) == len(doc2.objects)
