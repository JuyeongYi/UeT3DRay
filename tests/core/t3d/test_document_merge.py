"""g6 — parse_document 재귀 머지 (T3D 2-패스 직렬화 단일 부모 내부)."""
from __future__ import annotations

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.values import Scalar


def test_nested_dedupe_same_parent() -> None:
    """단일 부모 안에 같은 name이 두 번 나타나면 머지."""
    src = (
        'Begin Object Class=/Script/X.Node Name="N"\n'
        '   Begin Object Class=/Script/X.Pin Name="P"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="Q"\n'
        '   End Object\n'
        '   Begin Object Name="P"\n'
        '      Direction=Output\n'
        '   End Object\n'
        '   Begin Object Name="Q"\n'
        '      Direction=Input\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    assert len(doc.objects) == 1
    n = doc.objects[0]
    # 중복 머지 — 자식 2개, 각각 cls + Direction 모두 설정됨
    assert len(n.children) == 2
    p = next(c for c in n.children if c.name == "P")
    assert p.cls == "/Script/X.Pin"
    assert isinstance(p.properties.get("Direction"), Scalar)
    assert p.properties["Direction"].text == "Output"
    q = next(c for c in n.children if c.name == "Q")
    assert q.cls == "/Script/X.Pin"
    assert q.properties["Direction"].text == "Input"


def test_deeply_nested_dedupe() -> None:
    """다중 깊이 nesting에서도 머지."""
    src = (
        'Begin Object Name="A"\n'
        '   Begin Object Name="B"\n'
        '      Begin Object Class=/Script/X.Pin Name="P"\n'
        '      End Object\n'
        '      Begin Object Name="P"\n'
        '         Direction=Hidden\n'
        '      End Object\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    a = doc.objects[0]
    b = a.children[0]
    assert len(b.children) == 1
    p = b.children[0]
    assert p.cls == "/Script/X.Pin"
    assert p.properties["Direction"].text == "Hidden"


def test_no_duplicate_no_change() -> None:
    """중복 없는 경우 변화 없음."""
    src = (
        'Begin Object Name="N"\n'
        '   Begin Object Class=/Script/X.Pin Name="A"\n'
        '      Direction=Input\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="B"\n'
        '      Direction=Output\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    n = doc.objects[0]
    assert len(n.children) == 2


def test_top_level_dedupe_unchanged() -> None:
    """최상위 머지(기존 동작) 회귀 없음."""
    src = (
        'Begin Object Class=/Script/X.Node Name="N"\n'
        'End Object\n'
        'Begin Object Name="N"\n'
        '   Direction=Output\n'
        'End Object\n'
    )
    doc = parse_document(src)
    assert len(doc.objects) == 1
    n = doc.objects[0]
    assert n.cls == "/Script/X.Node"
    assert n.properties["Direction"].text == "Output"


def test_link_with_paths_merged() -> None:
    """RigVMLink 선언 + 정의 머지 — SourcePinPath/TargetPinPath 보존."""
    src = (
        'Begin Object Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L_1"\n'
        '   End Object\n'
        '   Begin Object Name="L_1"\n'
        '      SourcePinPath="X.Out"\n'
        '      TargetPinPath="Y.In"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    n = doc.objects[0]
    assert len(n.children) == 1
    link = n.children[0]
    assert link.cls == "/Script/RigVMDeveloper.RigVMLink"
    assert link.properties["SourcePinPath"].text == "X.Out"
    assert link.properties["TargetPinPath"].text == "Y.In"


def test_three_siblings_with_two_duplicates() -> None:
    """A·B·A·C → A 머지 후 3 children (A·B·C)."""
    src = (
        'Begin Object Name="P"\n'
        '   Begin Object Class=/Script/X.Pin Name="A"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="B"\n'
        '   End Object\n'
        '   Begin Object Name="A"\n'
        '      Direction=Input\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="C"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    p = doc.objects[0]
    assert len(p.children) == 3
    assert {c.name for c in p.children} == {"A", "B", "C"}
    a = next(c for c in p.children if c.name == "A")
    assert a.cls == "/Script/X.Pin"
    assert a.properties["Direction"].text == "Input"
