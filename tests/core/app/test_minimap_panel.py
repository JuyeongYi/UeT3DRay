import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.minimap_panel import MinimapPanel
from t3dgraph.core.app.graph_stack import GraphStack
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope='module')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_minimap_renders_root_label(qapp):
    s = GraphStack()
    s.open_root(GraphModel(label='root.t3d', nodes=[Node(name='A', cls=None)]))
    p = MinimapPanel()
    p.show_stack(s)
    assert 'root.t3d' in p.all_labels()


def test_minimap_renders_subgraph_children(qapp):
    inner = GraphModel(label='inner', nodes=[Node(name='I', cls=None)])
    g = GraphModel(label='root.t3d', nodes=[Node(name='P', cls=None, subgraph=inner)])
    s = GraphStack()
    s.open_root(g)
    p = MinimapPanel()
    p.show_stack(s)
    labels = p.all_labels()
    assert 'root.t3d' in labels
    assert 'P' in ' '.join(labels) or 'inner' in ' '.join(labels)


def test_click_jumps_to_segment(qapp):
    inner = GraphModel(label='inner', nodes=[Node(name='I', cls=None)])
    g = GraphModel(label='root.t3d', nodes=[Node(name='P', cls=None, subgraph=inner)])
    s = GraphStack()
    s.open_root(g)
    s.push(inner)
    p = MinimapPanel()
    p.show_stack(s)
    received = []
    p.location_clicked.connect(lambda ri, d: received.append((ri, d)))
    p._click_for_test(root_index=0, depth=0)
    assert received == [(0, 0)]
