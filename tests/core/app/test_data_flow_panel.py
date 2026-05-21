import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.analysis.data_flow import DataFlowResult, DepNode
from t3dgraph.core.app.data_flow_panel import DataFlowPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _result_with_two_sinks():
    return DataFlowResult(
        data_edges=[("A", "S1"), ("B", "S1"), ("C", "S2")],
        inputs_of={"S1": ["A", "B"], "S2": ["C"]},
        outputs_of={"A": ["S1"], "B": ["S1"], "C": ["S2"]},
        sinks=["S1", "S2"],
        sources=["A", "B", "C"],
        isolated=["X"],
        all_nodes=["A", "B", "C", "S1", "S2", "X"],
    )


def test_panel_shows_each_sink_and_isolated_group(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    labels = panel.top_level_labels()
    assert any("S1" in l for l in labels)
    assert any("S2" in l for l in labels)
    assert any("고립" in l or "isolated" in l.lower() for l in labels)


def test_panel_emits_navigate_on_double_click(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    received = []
    panel.navigate_requested.connect(received.append)
    panel.activate_node("A")
    assert "A" in received


def test_panel_preserves_all_nodes(qapp):
    """PRESERVE-ALL: 패널이 표시하는 노드 = 그래프의 모든 노드."""
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    shown = panel.shown_node_names()
    assert shown == {"A", "B", "C", "S1", "S2", "X"}
