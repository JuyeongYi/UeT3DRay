from t3dgraph.core.analysis.data_flow import DataFlowResult
from t3dgraph.core.analysis.data_flow_diff import diff_data_flow, DataFlowDiff


def _result(sinks, incoming):
    return DataFlowResult(
        sinks=sinks, sources=[], isolated=[],
        incoming_nodes=incoming, outgoing_nodes={},
        all_nodes=list({n for ns in incoming.values() for n in ns} | set(sinks)),
        data_edges=[], inputs_of={}, outputs_of={},
    )


def test_sinks_only_in_a():
    a = _result(['X', 'Y'], {'X': ['A'], 'Y': ['B']})
    b = _result(['X'], {'X': ['A']})
    d = diff_data_flow(a, b)
    assert d.sinks_only_in_a == ['Y']
    assert d.sinks_only_in_b == []
    assert d.sinks_common == ['X']


def test_per_sink_added_ancestor():
    a = _result(['S'], {'S': ['A']})
    b = _result(['S'], {'S': ['A', 'B'], 'B': []})
    d = diff_data_flow(a, b)
    assert 'B' in d.per_sink['S'].added_ancestors


def test_per_sink_removed_ancestor():
    a = _result(['S'], {'S': ['A', 'B']})
    b = _result(['S'], {'S': ['A']})
    d = diff_data_flow(a, b)
    assert 'B' in d.per_sink['S'].removed_ancestors


def test_per_sink_depth_change():
    a = _result(['S'], {'S': ['A'], 'A': []})
    b = _result(['S'], {'S': ['B'], 'B': ['A'], 'A': []})
    d = diff_data_flow(a, b)
    assert 'A' in d.per_sink['S'].depth_changes
    da, db = d.per_sink['S'].depth_changes['A']
    assert da == 1 and db == 2
