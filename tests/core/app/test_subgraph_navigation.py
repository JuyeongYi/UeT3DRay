"""서브그래프 진입 시그널 + MainWindow/Controller 통합 (F5/F6)."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _graph_with_subgraph() -> GraphModel:
    inner = GraphModel(label="P/inner", parent_node="P",
                       nodes=[Node(name="I", cls=None)])
    return GraphModel(label="root",
                      nodes=[Node(name="P", cls=None, subgraph=inner)])


def test_double_click_header_emits_enter_subgraph(qapp):
    g = _graph_with_subgraph()
    scene = GraphScene()
    scene.populate(g)
    received: list[str] = []
    scene.enter_subgraph_requested.connect(received.append)
    item = scene.node_item("P")
    assert item is not None
    item._emit_enter_subgraph_for_test()
    assert received == ["P"]


def test_header_double_click_noop_when_no_subgraph(qapp):
    """M3: subgraph 없는 노드의 헤더 더블클릭은 시그널을 발사하지 않는다."""
    g = GraphModel(nodes=[Node(name="X", cls=None)])   # subgraph 없음
    scene = GraphScene()
    scene.populate(g)
    received: list[str] = []
    scene.enter_subgraph_requested.connect(received.append)
    item = scene.node_item("X")
    emitted = item._try_emit_enter_subgraph(y=5.0)      # 헤더 영역
    assert emitted is False
    assert received == []


def test_header_double_click_emits_when_subgraph_present(qapp):
    """M3 대칭 케이스: subgraph 보유 노드의 헤더 더블클릭은 emit."""
    g = _graph_with_subgraph()
    scene = GraphScene()
    scene.populate(g)
    received: list[str] = []
    scene.enter_subgraph_requested.connect(received.append)
    item = scene.node_item("P")
    emitted = item._try_emit_enter_subgraph(y=5.0)
    assert emitted is True
    assert received == ["P"]


def test_enter_and_exit_subgraph(qapp):
    g = _graph_with_subgraph()
    win = MainWindow()
    win.open_graph(g, label="root")
    assert win.scene.node_item("P") is not None

    # 헤더 더블클릭 → 진입
    win.scene.node_item("P")._emit_enter_subgraph_for_test()
    # inner 그래프 노드가 보여야
    assert win.scene.node_item("I") is not None
    # P 노드는 inner 그래프에 없으므로 캔버스에서 사라짐
    assert win.scene.node_item("P") is None

    # 브레드크럼 segments
    assert win.breadcrumb.segment_labels() == ["root", "P/inner"]

    # 첫 세그먼트 클릭 → 루트 복귀
    win.breadcrumb._click_for_test(0)
    assert win.scene.node_item("P") is not None
    assert win.scene.node_item("I") is None


def test_multi_file_multi_root(qapp):
    g1 = GraphModel(label="file1.t3d", nodes=[Node(name="A", cls=None)])
    g2 = GraphModel(label="file2.t3d", nodes=[Node(name="B", cls=None)])
    win = MainWindow()
    win.open_graph(g1, label="file1.t3d")
    win.open_graph(g2, label="file2.t3d")
    assert win.scene.node_item("B") is not None
    assert len(win.graph_stack.roots()) == 2


def test_preserve_all_nodes_after_drilldown(qapp):
    """PRESERVE-ALL: 자식 진입·복귀 후에도 부모 그래프 모델은 변경되지 않음."""
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    parent_g = GraphModel(label="root",
                          nodes=[Node(name="P", cls=None, subgraph=inner)])
    parent_node_count_before = len(parent_g.nodes)
    win = MainWindow()
    win.open_graph(parent_g, label="root")
    win.scene.node_item("P")._emit_enter_subgraph_for_test()
    win.breadcrumb._click_for_test(0)         # 루트 복귀
    assert len(parent_g.nodes) == parent_node_count_before
    assert parent_g.nodes[0].subgraph is inner   # 자식 참조 유지
