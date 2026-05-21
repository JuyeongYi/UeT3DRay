import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_open_two_graphs_shows_two_tabs(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label='a.t3d', nodes=[Node(name='A', cls=None)]))
    win.open_graph(GraphModel(label='b.t3d', nodes=[Node(name='B', cls=None)]))
    assert win._tab_bar.count() == 2
    assert win._tab_bar.tabText(0) == 'a.t3d'
    assert win._tab_bar.tabText(1) == 'b.t3d'


def test_tab_click_switches_graph(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label='a.t3d', nodes=[Node(name='A', cls=None)]))
    win.open_graph(GraphModel(label='b.t3d', nodes=[Node(name='B', cls=None)]))
    win._tab_bar.setCurrentIndex(0)
    assert win.scene.node_item('A') is not None


def test_close_tab_removes_root(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label='a.t3d', nodes=[Node(name='A', cls=None)]))
    win.open_graph(GraphModel(label='b.t3d', nodes=[Node(name='B', cls=None)]))
    win._on_tab_close(0)
    assert win._tab_bar.count() == 1
    assert win.scene.node_item('B') is not None
