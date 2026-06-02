"""u5 — '수정된 핀만' 토글 (연결 OR 변경 합집합)."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.view_state import ViewState


def _data_pin(name, default_value=None, direction="Input"):
    return Pin(name=name, cpp_type="float", direction=direction,
               default_value=default_value)


def test_changed_pin_visible_in_modified_only_mode(qtbot) -> None:
    """default value에서 변경된 핀은 보임."""
    node = Node(name="N", cls="X",
                pins=[
                    _data_pin("UnchangedDefault", default_value="0.0"),
                    _data_pin("ChangedFromDefault", default_value="42.5"),
                ])
    g = GraphModel(nodes=[node], links=[])
    scene = GraphScene()
    vs = ViewState(connected_pins_only=True)   # 토글 ON
    scene.populate(g, view_state=vs)
    item = scene.node_item("N")
    # ChangedFromDefault 행은 존재
    assert any(p.endswith(".ChangedFromDefault") for p in item._row_paths)
    # default 값 그대로인 핀은 숨김
    assert not any(p.endswith(".UnchangedDefault") for p in item._row_paths)


def test_connected_pin_visible_in_modified_only_mode(qtbot) -> None:
    """연결된 핀도 여전히 보임."""
    a = Node(name="A", cls="X",
             pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    b = Node(name="B", cls="X",
             pins=[Pin(name="In", cpp_type="float", direction="Input")])
    g = GraphModel(nodes=[a, b],
                   links=[Link(source_path="A.Out", target_path="B.In")])
    scene = GraphScene()
    vs = ViewState(connected_pins_only=True)
    scene.populate(g, view_state=vs)
    a_item = scene.node_item("A")
    b_item = scene.node_item("B")
    assert any(p.endswith(".Out") for p in a_item._row_paths)
    assert any(p.endswith(".In") for p in b_item._row_paths)


def test_off_mode_shows_all_pins(qtbot) -> None:
    """토글 OFF면 모든 핀 표시 (기존 동작 회귀 없음)."""
    node = Node(name="N", cls="X",
                pins=[_data_pin("A"), _data_pin("B")])
    g = GraphModel(nodes=[node])
    scene = GraphScene()
    vs = ViewState(connected_pins_only=False)
    scene.populate(g, view_state=vs)
    item = scene.node_item("N")
    assert len(item._row_paths) == 2
