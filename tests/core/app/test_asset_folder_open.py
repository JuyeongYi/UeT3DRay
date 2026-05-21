import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.t3d.resolver import AssetResolver


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_load_resolver(qapp, tmp_path):
    for n in ('a.t3d.txt', 'b.t3d.txt'):
        (tmp_path / n).write_text(
            f'Begin Object Class=/Script/Foo.Bar Name="X_{n[0]}"\nEnd Object\n', encoding='utf-8')
    win = MainWindow()
    win._resolver = AssetResolver()
    win._resolver.load_folder(tmp_path)
    assert win._resolver.resolve_node_name('X_a') is not None
