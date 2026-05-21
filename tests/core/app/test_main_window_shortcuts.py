import pytest
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _graph_with_subgraph():
    inner = GraphModel(label='inner', nodes=[Node(name='I', cls=None)])
    return GraphModel(label='root', nodes=[Node(name='P', cls=None, subgraph=inner)])


def test_shortcut_back_pops_subgraph(qapp):
    g = _graph_with_subgraph()
    win = MainWindow()
    win.open_graph(g)
    win._on_enter_subgraph('P')
    assert len(win.breadcrumb.segment_labels()) == 2
    win._on_shortcut_back()
    assert len(win.breadcrumb.segment_labels()) == 1


def test_shortcut_back_noop_at_root(qapp):
    g = _graph_with_subgraph()
    win = MainWindow()
    win.open_graph(g)
    win._on_shortcut_back()
    assert len(win.breadcrumb.segment_labels()) == 1


def test_shortcut_up_jumps_to_root(qapp):
    g = _graph_with_subgraph()
    win = MainWindow()
    win.open_graph(g)
    win._on_enter_subgraph('P')
    assert len(win.breadcrumb.segment_labels()) == 2
    win._on_shortcut_up()
    assert len(win.breadcrumb.segment_labels()) == 1


def test_shortcuts_are_registered(qapp):
    win = MainWindow()
    shortcuts = win.findChildren(QShortcut)
    seqs = {sc.key().toString() for sc in shortcuts}
    assert 'Alt+Left' in seqs
    assert 'Backspace' in seqs
    assert 'Alt+Up' in seqs
