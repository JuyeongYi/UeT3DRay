"""u10 — 상위 핀 aggregate 상태."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import (
    _changed_paths_by_node, _connected_paths_by_node,
)


def test_changed_descendant_includes_parent_path() -> None:
    """struct의 자식이 default 변경 시 부모 path도 changed set에 포함."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")   # changed
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    result = _changed_paths_by_node(g)
    assert "N.Pos" in result.get("N", set())   # 부모 포함
    assert "N.Pos.X" in result.get("N", set())


def test_connected_descendant_includes_parent_path() -> None:
    """struct 자식 핀이 link target이면 부모 path도 connected set에 포함."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n_target = Node(name="T", cls="X", pins=[parent])
    n_src = Node(name="S", cls="X",
                 pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[n_src, n_target],
        links=[Link(source_path="S.Out", target_path="T.Pos.X")],
    )
    result = _connected_paths_by_node(g)
    # 부모 path도 connected set에
    assert "T.Pos" in result.get("T", set())
    assert "T.Pos.X" in result.get("T", set())


def test_unchanged_parent_no_changed_subpin() -> None:
    """자식 변경 없으면 부모도 changed set에 없음."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="0.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    result = _changed_paths_by_node(g)
    assert "N.Pos" not in result.get("N", set())


def test_inspector_shows_element_changed(qtbot) -> None:
    """struct 자식이 변경 + 부모 직접 변경 없음 → status에 '원소 변경됨'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(n, g)
    parent_item = panel._items["N.Pos"]
    assert "원소 변경됨" in parent_item.text(4)
    # 자식은 자기 자신 "변경됨"
    sub_item = panel._items["N.Pos.X"]
    assert "변경됨" in sub_item.text(4)
    assert "원소" not in sub_item.text(4)   # 자기 자신


def test_inspector_shows_element_connected(qtbot) -> None:
    """배열 자식 핀이 link target → 부모는 '원소 연결됨'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub_0 = Pin(name="0", cpp_type="float", direction="Input")
    array_pin = Pin(name="Items", cpp_type="TArray<float>",
                    direction="Input", subpins=[sub_0])
    target = Node(name="T", cls="X", pins=[array_pin])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Items.0")],
    )
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g)
    parent_item = panel._items["T.Items"]
    assert "원소 연결됨" in parent_item.text(4)


def test_inspector_array_self_connected_shows_connected(qtbot) -> None:
    """배열 자체가 link target이면 그냥 '연결됨' (자기 우선)."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    array_pin = Pin(name="Items", cpp_type="TArray<float>",
                    direction="Input")
    target = Node(name="T", cls="X", pins=[array_pin])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="TArray<float>",
                         direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Items")],
    )
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g)
    parent_item = panel._items["T.Items"]
    assert "연결됨" in parent_item.text(4)
    assert "원소" not in parent_item.text(4)


def test_inspector_self_and_descendant_connected_combined(qtbot) -> None:
    """배열 자체 연결 + 자식 핀도 따로 연결 → '연결됨 (원소 포함)'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub_0 = Pin(name="0", cpp_type="float", direction="Input")
    array_pin = Pin(name="Items", cpp_type="TArray<float>",
                    direction="Input", subpins=[sub_0])
    target = Node(name="T", cls="X", pins=[array_pin])
    src1 = Node(name="S1", cls="X",
                pins=[Pin(name="Out", cpp_type="TArray<float>",
                          direction="Output")])
    src2 = Node(name="S2", cls="X",
                pins=[Pin(name="Out", cpp_type="float",
                          direction="Output")])
    g = GraphModel(
        nodes=[src1, src2, target],
        links=[
            Link(source_path="S1.Out", target_path="T.Items"),    # self
            Link(source_path="S2.Out", target_path="T.Items.0"),  # desc
        ],
    )
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g)
    parent_item = panel._items["T.Items"]
    assert "연결됨 (원소 포함)" in parent_item.text(4)


def test_inspector_self_and_descendant_changed_combined(qtbot) -> None:
    """struct 자체 default + 자식도 default → '변경됨(추정) (원소 포함)'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 default_value="(X=1,Y=2,Z=3)", subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(n, g)
    parent_item = panel._items["N.Pos"]
    assert "변경됨(추정) (원소 포함)" in parent_item.text(4)
