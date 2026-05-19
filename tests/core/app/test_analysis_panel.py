from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.flow import analyze_flow
from t3dgraph.core.app.analysis_panel import AnalysisPanel


def _ep(name, d):
    return Pin(name=name, cpp_type="FRigVMExecuteContext", direction=d, is_execution=True)


def _fan_in_graph():
    a = Node(name="A", cls="X", pins=[_ep("O", "Output")])
    b = Node(name="B", cls="X", pins=[_ep("O", "Output")])
    c = Node(name="C", cls="X", pins=[_ep("I", "Input"), _ep("O", "Output")])
    d = Node(name="D", cls="X", pins=[_ep("I", "Input")])
    links = [Link("A.O", "C.I"), Link("B.O", "C.I"), Link("C.O", "D.I")]
    return GraphModel(nodes=[a, b, c, d], links=links)


def test_no_convergence_shows_message(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    a = Node(name="A", cls="X", pins=[_ep("O", "Output")])
    b = Node(name="B", cls="X", pins=[_ep("I", "Input")])
    panel.show_flow(analyze_flow(GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")])))
    assert panel.convergence_count() == 0
    assert "없음" in panel.summary_text()


def test_convergence_listed(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show_flow(analyze_flow(_fan_in_graph()))
    assert panel.convergence_count() == 1
    assert panel.has_convergence("C")


def test_activate_convergence_emits_navigate(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show_flow(analyze_flow(_fan_in_graph()))
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_convergence("C")
    assert sig.args == ["C"]


def test_highlight_node_selects_row(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show_flow(analyze_flow(_fan_in_graph()))
    panel.highlight_node("C")
    assert panel.highlighted_node() == "C"
