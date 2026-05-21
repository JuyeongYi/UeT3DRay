import json
from t3dgraph._cli.serialize import summary_dict, dataflow_dict
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.bundle import run as run_analyses


def _simple_graph():
    return GraphModel(
        nodes=[
            Node(name='A', cls='X', pins=[Pin(name='O', cpp_type='float', direction='Output')]),
            Node(name='B', cls='X', pins=[Pin(name='I', cpp_type='float', direction='Input')]),
        ],
        links=[Link(source_path='A.O', target_path='B.I')],
    )


def test_summary_dict_has_expected_keys():
    g = _simple_graph()
    b = run_analyses(g)
    d = summary_dict('rigvm', g, b)
    assert d['graph_type'] == 'rigvm'
    assert d['nodes']['total'] == 2
    assert d['links'] == 1
    assert 'execution' in d
    assert 'warnings' in d


def test_summary_dict_is_json_serializable():
    g = _simple_graph()
    b = run_analyses(g)
    s = json.dumps(summary_dict('rigvm', g, b))
    assert json.loads(s)['graph_type'] == 'rigvm'


def test_dataflow_dict_emits_pin_paths():
    g = _simple_graph()
    b = run_analyses(g)
    d = dataflow_dict(b.data_flow)
    assert d['data_edges'] == [{'source': 'A.O', 'target': 'B.I'}]
    assert d['incoming_nodes'] == {'B': ['A']}
    assert d['outgoing_nodes'] == {'A': ['B']}
