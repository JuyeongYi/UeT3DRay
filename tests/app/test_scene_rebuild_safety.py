"""w1-A — populate 재호출 시 selection 슬롯이 옛 NodeItem 참조로 폭발하지 않는다."""
import pytest
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene


@pytest.fixture
def two_node_graph() -> GraphModel:
    a = Node(name="A", cls="X",
             pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    b = Node(name="B", cls="X",
             pins=[Pin(name="In", cpp_type="float", direction="Input")])
    return GraphModel(
        nodes=[a, b],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )


def test_populate_twice_no_runtime_error(qtbot, two_node_graph) -> None:
    """populate 두 번 호출 — selectionChanged 슬롯이 옛 참조에서 isSelected() 못 한다."""
    scene = GraphScene()
    scene.populate(two_node_graph)
    a_item = scene._nodes["A"]
    a_item.setSelected(True)
    # 이 시점에 selectionChanged 슬롯이 _nodes를 순회하면 옛 a_item이 들어있음
    scene.populate(two_node_graph)   # 옛 a_item 파괴 → 시그널 발화
    # 새 _nodes만 남고, 옛 a_item에 isSelected 호출 시도 없어야 함
    assert len(scene._nodes) == 2
    # 새 객체로 갈아끼움 확인
    assert scene._nodes["A"] is not a_item


def test_main_window_pin_toggle_no_crash(qtbot) -> None:
    """w1-A 재현 — 구조체 핀 토글이 _on_scene_selection 폭발 없이 끝난다."""
    from t3dgraph.core.app.main_window import MainWindow
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin

    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])

    w = MainWindow()
    qtbot.addWidget(w)
    # graph 직접 설정 + scene 초기 populate (_rebuild_scene 경로와 동일)
    w.graph = g
    w.scene.populate(g)
    # 노드 선택 상태에서 populate 재호출 — 옛 NodeItem이 파괴되면서 selectionChanged 발화
    w.scene._nodes["N"].setSelected(True)
    # 핀 토글 → _rebuild_scene → populate 재호출 → 폭발 없으면 통과
    w._on_pin_toggle("N.Pos")
