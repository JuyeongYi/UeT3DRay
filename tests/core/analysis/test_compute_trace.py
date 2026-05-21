from t3dgraph.core.analysis.compute_trace import compute_trace, TraceLevel


def test_compute_trace_levels_in_simple_chain():
    incoming = {'S': ['B'], 'B': ['A'], 'A': []}
    levels = compute_trace('S', incoming)
    assert levels == [
        TraceLevel(depth=0, nodes=['S']),
        TraceLevel(depth=1, nodes=['B']),
        TraceLevel(depth=2, nodes=['A']),
    ]


def test_compute_trace_fan_in_groups_at_same_depth():
    incoming = {'S': ['A', 'B'], 'A': [], 'B': []}
    levels = compute_trace('S', incoming)
    assert levels[0] == TraceLevel(depth=0, nodes=['S'])
    assert sorted(levels[1].nodes) == ['A', 'B']


def test_compute_trace_dedup_across_paths():
    incoming = {'S': ['A', 'B'], 'A': ['C'], 'B': ['C'], 'C': []}
    levels = compute_trace('S', incoming)
    flat = [n for lv in levels for n in lv.nodes]
    assert flat.count('C') == 1


def test_compute_trace_cycle_safe():
    incoming = {'A': ['B'], 'B': ['A']}
    levels = compute_trace('A', incoming, max_depth=5)
    flat = [n for lv in levels for n in lv.nodes]
    assert flat.count('A') == 1
