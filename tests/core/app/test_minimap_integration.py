import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_minimap_updates_on_open_graph(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label='r', nodes=[Node(name='A', cls=None)]))
    assert 'r' in ' '.join(win.minimap.all_labels())
