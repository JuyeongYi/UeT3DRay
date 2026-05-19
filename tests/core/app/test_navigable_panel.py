from t3dgraph.core.app.navigable_panel import NavigablePanel
from t3dgraph.core.app.inspector_panel import InspectorPanel
from t3dgraph.core.app.analysis_panel import AnalysisPanel
from t3dgraph.core.app.execution_order_panel import ExecutionOrderPanel


def test_panels_share_navigable_base(qtbot):
    for cls in (InspectorPanel, AnalysisPanel, ExecutionOrderPanel):
        panel = cls()
        qtbot.addWidget(panel)
        assert isinstance(panel, NavigablePanel)
        assert hasattr(panel, "navigate_requested")
