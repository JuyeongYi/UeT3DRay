import pytest
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController
from t3dgraph.core.app.items import NodeItem, LinkItem


ALL = [
    "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt",
    "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__IK_Rig.t3d.txt",
    "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__Physics.t3d.txt",
]


@pytest.mark.parametrize("fname", ALL)
def test_viewer_opens_real_file(qtbot, orion_dir, fname):
    window = MainWindow()
    qtbot.addWidget(window)
    controller = AppController(window)
    window.set_open_handler(controller.open_file)

    window.open_path(str(orion_dir / fname))

    node_items = [i for i in window.scene.items() if isinstance(i, NodeItem)]
    link_items = [i for i in window.scene.items() if isinstance(i, LinkItem)]
    assert len(node_items) > 0
    if "RigVMModel" in fname:
        assert len(link_items) > 0


def test_viewer_window_shows(qtbot, orion_dir):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
