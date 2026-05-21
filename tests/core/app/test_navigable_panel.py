from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout
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


class _FakePanel(NavigablePanel):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        layout.addWidget(self._list)
        self._items: dict[str, QListWidgetItem] = {}

    def _lookup_item(self, name: str):
        return self._items.get(name)

    def _clear_highlight(self) -> None:
        self._list.clearSelection()


def test_highlight_node_selects_item(qtbot):
    panel = _FakePanel()
    qtbot.addWidget(panel)
    a = QListWidgetItem("A")
    panel._list.addItem(a)
    panel._items["A"] = a

    panel.highlight_node("A")
    assert panel._list.currentItem() is a


def test_highlight_node_missing_calls_clear(qtbot):
    panel = _FakePanel()
    qtbot.addWidget(panel)
    a = QListWidgetItem("A")
    panel._list.addItem(a)
    panel._items["A"] = a
    panel._list.setCurrentItem(a)

    panel.highlight_node("Z")
    assert panel._list.selectedItems() == []


def test_highlight_node_none_calls_clear(qtbot):
    panel = _FakePanel()
    qtbot.addWidget(panel)
    a = QListWidgetItem("A")
    panel._list.addItem(a)
    panel._items["A"] = a
    panel._list.setCurrentItem(a)

    panel.highlight_node(None)
    assert panel._list.selectedItems() == []
