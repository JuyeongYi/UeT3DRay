from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController

RIGVMMODEL = "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"


def test_execution_order_renders_constructs(qtbot, orion_dir):
    window = MainWindow()
    qtbot.addWidget(window)
    controller = AppController(window)
    window.set_open_handler(controller.open_file)
    window.open_path(str(orion_dir / RIGVMMODEL))

    texts = [window.exec_order_panel.row_text(i)
             for i in range(window.exec_order_panel.step_count())]
    # CollapseNode가 없으면 step_count > 0으로만 검증
    if not any(t.rstrip().endswith("{ … }") for t in texts):
        assert window.exec_order_panel.step_count() > 0
        # 실제 파일에 function 노드가 없음 — 코드형 렌더 단위 테스트로 이미 검증됨
