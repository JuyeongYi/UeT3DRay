from pathlib import Path
import pytest
from t3dgraph._cli.load import strict_load, lenient_load


def test_strict_load_returns_graph_for_valid(tmp_path):
    p = tmp_path / 'x.t3d.txt'
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="X"\nEnd Object\n',
        encoding='utf-8')
    graph, warnings = strict_load(p)
    assert graph is not None
    assert any(n.name == 'X' for n in graph.nodes)


def test_strict_load_raises_on_parse_error(tmp_path):
    from t3dgraph.core.t3d.objects import T3DParseError
    p = tmp_path / 'bad.t3d.txt'
    p.write_text('Begin Object Class=X Name="Y"\n', encoding='utf-8')
    with pytest.raises(T3DParseError):
        strict_load(p)


def test_lenient_load_returns_none_on_parse_error(tmp_path):
    p = tmp_path / 'bad.t3d.txt'
    p.write_text('Begin Object Class=X Name="Y"\n', encoding='utf-8')
    graph, warnings = lenient_load(p)
    assert graph is None
    assert any('parse' in w.lower() for w in warnings)


def test_lenient_load_captures_interpreter_warnings(tmp_path):
    p = tmp_path / 'x.t3d.txt'
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.WeirdUnknownNode Name="W"\nEnd Object\n',
        encoding='utf-8')
    graph, warnings = lenient_load(p)
    assert graph is not None
    assert any('알 수 없는 클래스' in w for w in warnings)
