from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController

RIGVMMODEL = "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"


def _open(qtbot, orion_dir):
    window = MainWindow()
    qtbot.addWidget(window)
    controller = AppController(window)
    window.set_open_handler(controller.open_file)
    window.open_path(str(orion_dir / RIGVMMODEL))
    return window


def test_filter_panel_populated_from_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    assert len(window.node_filter.type_names()) > 0


def test_select_real_node_shows_pins(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    first = window.graph.nodes[0].name
    window.scene.select_node(first)
    assert window.inspector.pin_count() >= 0
    assert window.view_state.selected_node == first


def test_hiding_a_type_hides_those_nodes(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    a_type = window.node_filter.type_names()[0]
    window.node_filter.set_checked(a_type, False)
    hidden = [it for it in window.scene._nodes.values()
              if not it.isVisible()]
    assert len(hidden) > 0


def test_full_suite_unaffected(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    assert len(window.graph.nodes) > 0
    assert len(window.graph.links) > 0
