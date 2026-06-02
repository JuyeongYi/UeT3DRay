"""g3 (F24) — InspectorPanel 헤더 elide."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QSizePolicy

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.inspector_panel import InspectorPanel


def test_title_word_wrap_disabled(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    assert panel._title.wordWrap() is False


def test_title_height_capped(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    fm = QFontMetrics(panel._title.font())
    assert panel._title.maximumHeight() <= fm.lineSpacing() + 8


def test_long_title_elided_with_tooltip(qtbot) -> None:
    node = Node(name="N1", cls="A" * 100,
                role_summary="B" * 100, role_category="C" * 100)
    g = GraphModel(nodes=[node])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.resize(300, 200)
    panel.show_node(node, g)
    assert "…" in panel._title.text() or "..." in panel._title.text()
    assert len(panel._title.toolTip()) > len(panel._title.text())


def test_short_title_not_elided(qtbot) -> None:
    node = Node(name="Short", cls="Foo")
    g = GraphModel(nodes=[node])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.resize(400, 200)
    panel.show_node(node, g)
    assert "…" not in panel._title.text()
