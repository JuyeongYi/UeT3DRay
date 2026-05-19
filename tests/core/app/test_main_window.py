from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.contracts import AbstractGraphView
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_main_window_is_graph_view(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert isinstance(w, AbstractGraphView)


def test_show_graph_populates_scene(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(
        nodes=[Node(name="A", cls="X", position=(0.0, 0.0),
                    pins=[Pin("O", "exec", "Output")]),
               Node(name="B", cls="X", position=(300.0, 0.0),
                    pins=[Pin("I", "exec", "Input")])],
        links=[Link("A.O", "B.I")],
    )
    w.show_graph(g)
    assert w.scene.node_item("A") is not None
    assert w.scene.node_item("B") is not None


def test_open_callback_invoked(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    captured = []
    w.set_open_handler(lambda path: captured.append(path))
    w.open_path("C:/some/file.t3d.txt")
    assert captured == ["C:/some/file.t3d.txt"]


def test_has_three_docks(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert {w.dock_left.windowTitle(), w.dock_right.windowTitle(),
            w.dock_bottom.windowTitle()} == {"노드 타입 필터", "속성 인스펙터", "분석"}


def _wired_graph():
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
    a = Node(name="A", cls="/X.RigVMUnitNode", position=(0.0, 0.0),
             pins=[Pin("Out", "FRigVMExecuteContext", "Output", is_execution=True)])
    b = Node(name="B", cls="/X.RigVMDispatchNode", position=(400.0, 0.0),
             pins=[Pin("In", "FRigVMExecuteContext", "Input", is_execution=True)])
    return GraphModel(nodes=[a, b], links=[Link("A.Out", "B.In")])


def test_docks_hold_real_panels(qtbot):
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    from t3dgraph.core.app.node_filter_panel import NodeFilterPanel
    w = MainWindow()
    qtbot.addWidget(w)
    assert isinstance(w.dock_right.widget(), InspectorPanel)
    assert isinstance(w.dock_left.widget(), NodeFilterPanel)


def test_selecting_node_updates_inspector(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.scene.select_node("A")
    assert w.inspector.pin_count() == 1


def test_filter_hides_node_in_scene(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.node_filter.set_checked("RigVMUnitNode", False)
    assert w.scene.node_item("A").isVisible() is False


def test_navigate_request_selects_peer(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.scene.select_node("A")
    w.inspector.activate_pin("Out")
    assert w.scene.selected_node_name() == "B"


def test_bottom_dock_has_analysis_tabs(qtbot):
    from PySide6.QtWidgets import QTabWidget
    w = MainWindow()
    qtbot.addWidget(w)
    tabs = w.dock_bottom.widget()
    assert isinstance(tabs, QTabWidget)
    titles = {tabs.tabText(i) for i in range(tabs.count())}
    assert titles == {"수렴점", "실행 순서"}


def test_show_graph_populates_execution_order(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    assert w.exec_order_panel.step_count() == 2


def test_analysis_panel_navigate_moves_canvas(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.exec_order_panel.activate_row(1)
    assert w.scene.selected_node_name() == "B"


def test_canvas_selection_highlights_exec_panel(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.scene.select_node("A")
    assert w.exec_order_panel.highlighted_node() == "A"


def test_view_mode_toolbar_has_three_toggles(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    labels = {a.text() for a in w.view_mode_actions}
    assert labels == {"연결된 핀만", "깊이 펼침", "fan-in 강조"}
    assert all(a.isCheckable() for a in w.view_mode_actions)


def test_toggle_connected_only_rebuilds_scene(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.set_view_mode("연결된 핀만", True)
    assert w.view_state.connected_pins_only is True
    assert w.scene.node_item("A") is not None


def test_toggle_expand_subpins_updates_state(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    w.set_view_mode("깊이 펼침", True)
    assert w.view_state.expand_subpins is True
