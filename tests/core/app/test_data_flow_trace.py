import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.data_flow_panel import DataFlowPanel
from t3dgraph.core.analysis.data_flow import DataFlowResult, DataFlowEdge
from t3dgraph.core.base.pin_ref import PinRef


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_panel_shows_trace_on_sink_activate(qapp):
    edges = [DataFlowEdge(PinRef('A', 'O'), PinRef('S', 'I'))]
    r = DataFlowResult(
        data_edges=edges,
        inputs_of={'S': edges}, outputs_of={'A': edges},
        incoming_nodes={'S': ['A']}, outgoing_nodes={'A': ['S']},
        sinks=['S'], sources=['A'], isolated=[], all_nodes=['A', 'S'],
    )
    panel = DataFlowPanel()
    panel.show_result(r)
    items = panel.items_for('S')
    panel._on_activated(items[0], 0)
    trace_text = panel.trace_text()
    assert 'S' in trace_text
    assert 'A' in trace_text
    assert ('level' in trace_text.lower() or 'depth' in trace_text.lower()
            or '단계' in trace_text)
