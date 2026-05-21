"""AppController — bundle.run 단일 출처 확인 (D-B3, P2c-B2)."""
from __future__ import annotations
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.controller import AppController
from t3dgraph.core.app.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_open_file_routes_to_open_graph_when_available(qapp, tmp_path):
    sample = tmp_path / "x.t3d.txt"
    sample.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="X"\nEnd Object\n',
        encoding="utf-8",
    )
    win = MainWindow()
    ctl = AppController(win)
    ctl.open_file(str(sample))
    assert win.graph is not None
    assert any(n.name == "X" for n in win.graph.nodes)
