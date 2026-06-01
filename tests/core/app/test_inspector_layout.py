"""F15 InspectorPanel 폭 안정 — 컬럼 디폴트·Interactive·가로 스크롤·툴팁."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin
from t3dgraph.core.app.inspector_panel import InspectorPanel


_EXPECTED_WIDTHS = (140, 160, 70, 120, 90)


def _graph_with_long_default() -> GraphModel:
    long_default = "x" * 200
    pin = Pin(name="P", cpp_type="FRigVMRedirectorTargetsExtremelyLongTypeName",
              direction="Input", default_value=long_default)
    n = Node(name="N1", cls="T", pins=[pin])
    return GraphModel(nodes=[n], label="root")


def test_columns_have_default_widths(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    for i, w in enumerate(_EXPECTED_WIDTHS):
        assert panel._tree.columnWidth(i) == w


def test_header_mode_is_interactive(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    header = panel._tree.header()
    for i in range(panel._tree.columnCount()):
        assert header.sectionResizeMode(i) == QHeaderView.Interactive


def test_stretch_last_section_off(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    assert panel._tree.header().stretchLastSection() is False


def test_horizontal_scroll_as_needed(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    assert panel._tree.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded


def test_long_default_gets_tooltip(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    graph = _graph_with_long_default()
    panel.show_node(graph.nodes[0], graph)
    item = panel._items["N1.P"]
    # 기본값 컬럼(3)이 잘림 → 풀 텍스트 툴팁
    assert "x" * 200 in item.toolTip(3)


def test_long_cpp_type_gets_tooltip(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    graph = _graph_with_long_default()
    panel.show_node(graph.nodes[0], graph)
    item = panel._items["N1.P"]
    assert "FRigVMRedirectorTargetsExtremelyLongTypeName" in item.toolTip(1)


def test_short_value_no_tooltip(qtbot) -> None:
    pin = Pin(name="P", cpp_type="bool", direction="Input", default_value="False")
    graph = GraphModel(nodes=[Node(name="N1", cls="T", pins=[pin])], label="root")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(graph.nodes[0], graph)
    item = panel._items["N1.P"]
    assert item.toolTip(3) == ""
