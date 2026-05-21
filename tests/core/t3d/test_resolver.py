from pathlib import Path
from t3dgraph.core.t3d.resolver import AssetResolver
from t3dgraph.core.t3d.document import parse_document


def test_resolve_external_ref_by_name(tmp_path):
    a_src = 'Begin Object Class=/Script/Foo.Func Name="MyFunc"\nEnd Object\n'
    pa = tmp_path / 'a.t3d.txt'
    pa.write_text(a_src, encoding='utf-8')
    r = AssetResolver()
    r.register(pa, parse_document(a_src))
    found = r.resolve_node_name('MyFunc')
    assert found is not None
    assert found[0] == pa
    assert found[1].name == 'MyFunc'


def test_load_folder_registers_all_t3d_files(tmp_path):
    for name in ('a.t3d.txt', 'b.t3d.txt'):
        (tmp_path / name).write_text(
            f'Begin Object Class=/Script/Foo.Bar Name="X_{name[0]}"\nEnd Object\n', encoding='utf-8')
    r = AssetResolver()
    r.load_folder(tmp_path)
    assert r.resolve_node_name('X_a') is not None
    assert r.resolve_node_name('X_b') is not None


def test_resolve_external_refs_returns_resolved_map():
    from t3dgraph.core.base.graph_model import GraphModel
    g = GraphModel(external_refs=['MyFunc.OutPin', 'Unknown.Ref'])
    r = AssetResolver()
    r._index['MyFunc'] = ('fake_path', 'fake_obj')
    resolved = r.resolve_external_refs(g)
    assert 'MyFunc.OutPin' in resolved
    assert 'Unknown.Ref' not in resolved
