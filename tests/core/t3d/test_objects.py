from t3dgraph.core.t3d.objects import parse_objects
from t3dgraph.core.t3d.values import Scalar, QuotedString

SAMPLE = (
    'Begin Object Class=/Script/X.Node Name="N1"\n'
    '   Begin Object Class=/Script/X.Pin Name="P1"\n'
    '   End Object\n'
    '   Direction=Output\n'
    '   Pins(0)="/Script/X.Pin\'P1\'"\n'
    'End Object\n'
)


def test_top_level_object():
    objs = parse_objects(SAMPLE)
    assert len(objs) == 1
    assert objs[0].cls == "/Script/X.Node"
    assert objs[0].name == "N1"


def test_nested_child():
    objs = parse_objects(SAMPLE)
    assert len(objs[0].children) == 1
    assert objs[0].children[0].name == "P1"


def test_properties_indexed_key_preserved():
    obj = parse_objects(SAMPLE)[0]
    assert obj.properties["Direction"] == Scalar("Output")
    assert isinstance(obj.properties["Pins(0)"], QuotedString)


def test_declaration_block_has_no_class_optional():
    src = 'Begin Object Name="N1"\n   Direction=Input\nEnd Object\n'
    obj = parse_objects(src)[0]
    assert obj.cls is None
    assert obj.name == "N1"


def test_unbalanced_raises():
    import pytest
    from t3dgraph.core.t3d.objects import T3DParseError
    with pytest.raises(T3DParseError):
        parse_objects('Begin Object Name="N1"\n')


def test_bad_value_wrapped_with_file_line():
    import pytest
    from t3dgraph.core.t3d.objects import T3DParseError
    src = 'Begin Object Name="N"\n   Bad=(X=1\nEnd Object\n'
    with pytest.raises(T3DParseError) as ei:
        parse_objects(src)
    assert ei.value.line == 2
    assert ei.value.col > 0
