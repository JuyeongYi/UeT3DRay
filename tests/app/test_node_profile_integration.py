"""k2 통합 — MainWindow가 NodeProfileTable 사용."""
from PySide6.QtWidgets import QGraphicsSimpleTextItem

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow


def test_main_window_loads_node_profiles(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.node_profiles is not None


def test_variable_node_renders_with_badge(qtbot) -> None:
    """RigVMVariableNode 노드를 그래프에 추가 → var 배지 표시."""
    w = MainWindow()
    qtbot.addWidget(w)
    var_node = Node(name="V1",
                    cls="/Script/RigVMDeveloper.RigVMVariableNode")
    g = GraphModel(nodes=[var_node])
    w.open_graph(g)
    item = w.scene.node_item("V1")
    assert item is not None
    texts = [c.text() for c in item.childItems()
             if isinstance(c, QGraphicsSimpleTextItem)]
    assert "var" in texts
