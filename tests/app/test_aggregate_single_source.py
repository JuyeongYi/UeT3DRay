"""v1-A1 — InspectorPanel은 외부 changed/connected set만 신뢰 (단일 진실원)."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.inspector_panel import InspectorPanel


def test_inspector_uses_external_changed_set_only(qtbot) -> None:
    """외부 changed_paths set이 자식 path 누락 — InspectorPanel은 부모를 '원소 변경됨'으로 표시 안 함."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")   # 실제 changed (is_changed_from_default True)
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    # 외부에서 빈 set 전달 — scene이 "이 그래프는 변경 없다"고 판정한 상황 시뮬
    panel.show_node(n, g, changed_paths=set(), connected_paths=set())
    parent_item = panel._items["N.Pos"]
    # InspectorPanel이 자체 walk를 안 하므로 "원소 변경됨" 표시 없음
    assert "원소 변경됨" not in parent_item.text(4)
    # 자식도 외부 set이 빈 이상 changed 표시 없음
    sub_item = panel._items["N.Pos.X"]
    assert "변경됨" not in sub_item.text(4)


def test_inspector_uses_external_connected_set_only(qtbot) -> None:
    """외부 connected_paths set이 자식 path 만 — 부모는 '원소 연결됨'."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    target = Node(name="T", cls="X", pins=[parent])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Pos.X")],
    )
    # scene이 prefix까지 포함한 set 전달 (실제 _connected_paths_by_node 동작)
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g,
                    changed_paths=set(),
                    connected_paths={"T.Pos", "T.Pos.X"})
    parent_item = panel._items["T.Pos"]
    assert "원소 연결됨" in parent_item.text(4)


def test_inspector_default_falls_back_to_module_fn(qtbot) -> None:
    """set 전달 없으면 모듈 함수로 직접 계산 (호환)."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(n, g)   # set 안 넘김
    parent_item = panel._items["N.Pos"]
    assert "원소 변경됨" in parent_item.text(4)
