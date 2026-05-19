from t3dgraph.core.analysis.execution_order import ExecutionStep
from t3dgraph.core.app.execution_order_panel import ExecutionOrderPanel


def _steps():
    return [ExecutionStep("A", 0), ExecutionStep("B", 1), ExecutionStep("C", 1)]


def test_show_order_lists_steps(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    assert panel.step_count() == 3


def test_depth_rendered_as_indent(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    assert panel.row_text(0) == "A"
    assert panel.row_text(1).startswith("    ") and panel.row_text(1).strip() == "B"


def test_activate_row_emits_navigate(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    with qtbot.waitSignal(panel.navigate_requested, timeout=1000) as sig:
        panel.activate_row(2)
    assert sig.args == ["C"]


def test_highlight_node_selects_row(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order(_steps())
    panel.highlight_node("B")
    assert panel.highlighted_node() == "B"


def test_empty_order(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    panel.show_order([])
    assert panel.step_count() == 0
