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


def test_execution_order_populated_from_real_file(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    assert window.exec_order_panel.step_count() > 0


def test_convergence_panel_reports_no_fan_in(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    assert window.analysis_panel.convergence_count() == 0
    assert "없음" in window.analysis_panel.summary_text()


def test_exec_order_navigation_selects_node(qtbot, orion_dir):
    window = _open(qtbot, orion_dir)
    window.exec_order_panel.activate_row(0)
    assert window.scene.selected_node_name() is not None
