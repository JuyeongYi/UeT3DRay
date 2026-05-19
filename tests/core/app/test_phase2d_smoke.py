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


def test_connected_only_toggle_on_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    window.set_view_mode("연결된 핀만", True)
    assert window.view_state.connected_pins_only is True
    assert len(window.scene._nodes) > 0


def test_expand_subpins_toggle_on_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    before = window.scene.node_item(window.graph.nodes[0].name).rect().height()
    window.set_view_mode("깊이 펼침", True)
    after = window.scene.node_item(window.graph.nodes[0].name).rect().height()
    assert after >= before


def test_fan_in_highlight_toggle_no_error(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    window.set_view_mode("fan-in 강조", True)
    assert window.view_state.fan_in_highlight is True


def test_selection_survives_view_mode_toggle(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    first = window.graph.nodes[0].name
    window.scene.select_node(first)
    window.set_view_mode("깊이 펼침", True)
    assert window.scene.selected_node_name() == first
