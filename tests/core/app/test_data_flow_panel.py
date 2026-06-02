import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.analysis.data_flow import DataFlowResult, DataFlowEdge, dependency_tree
from t3dgraph.core.base.pin_ref import PinRef
from t3dgraph.core.app.data_flow_panel import DataFlowPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _result_with_two_sinks():
    edges = [
        DataFlowEdge(PinRef("A", "O"), PinRef("S1", "I1")),
        DataFlowEdge(PinRef("B", "O"), PinRef("S1", "I2")),
        DataFlowEdge(PinRef("C", "O"), PinRef("S2", "I")),
    ]
    return DataFlowResult(
        data_edges=edges,
        inputs_of={"S1": edges[:2], "S2": [edges[2]]},
        outputs_of={"A": [edges[0]], "B": [edges[1]], "C": [edges[2]]},
        incoming_nodes={"S1": ["A", "B"], "S2": ["C"]},
        outgoing_nodes={"A": ["S1"], "B": ["S1"], "C": ["S2"]},
        sinks=["S1", "S2"],
        sources=["A", "B", "C"],
        isolated=["X"],
        all_nodes=["A", "B", "C", "S1", "S2", "X"],
    )


def test_panel_shows_each_sink_and_isolated_group(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    labels = panel.top_level_labels()
    assert any("S1" in l for l in labels)
    assert any("S2" in l for l in labels)
    assert any("고립" in l or "isolated" in l.lower() for l in labels)


def test_panel_emits_navigate_on_double_click(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    received = []
    panel.navigate_requested.connect(received.append)
    panel.activate_node("A")
    assert "A" in received


def test_panel_preserves_all_nodes(qapp):
    """PRESERVE-ALL: 패널이 표시하는 노드 = 그래프의 모든 노드."""
    panel = DataFlowPanel()
    panel.show_result(_result_with_two_sinks())
    shown = panel.shown_node_names()
    assert shown == {"A", "B", "C", "S1", "S2", "X"}


# ---- 신규: 핀 라벨 + 다중 인덱싱 (D-A2) ----

def _result_fan_in():
    edges = [
        DataFlowEdge(PinRef("A", "O"), PinRef("Mid", "I1")),
        DataFlowEdge(PinRef("B", "O"), PinRef("Mid", "I2")),
        DataFlowEdge(PinRef("Mid", "O"), PinRef("S1", "I")),
        DataFlowEdge(PinRef("Mid", "O"), PinRef("S2", "I")),
    ]
    incoming_nodes = {"Mid": ["A", "B"], "S1": ["Mid"], "S2": ["Mid"]}
    outgoing_nodes = {"A": ["Mid"], "B": ["Mid"], "Mid": ["S1", "S2"]}
    return DataFlowResult(
        data_edges=edges,
        inputs_of={"Mid": edges[:2], "S1": [edges[2]], "S2": [edges[3]]},
        outputs_of={"A": [edges[0]], "B": [edges[1]], "Mid": edges[2:]},
        incoming_nodes=incoming_nodes,
        outgoing_nodes=outgoing_nodes,
        sinks=["S1", "S2"],
        sources=["A", "B"],
        isolated=[],
        all_nodes=["A", "B", "Mid", "S1", "S2"],
    )


def test_panel_pin_label_rendered(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    labels = panel.all_labels()
    assert any("Mid" in l and ("I1" in l or "I2" in l) for l in labels)


def test_panel_indexes_all_occurrences(qapp):
    """D-A2: Mid가 S1·S2 두 트리에 등장 — 두 위치 모두 인덱싱."""
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    items_for_mid = panel.items_for("Mid")
    assert len(items_for_mid) >= 2


def test_panel_marks_subsequent_occurrences_as_back_reference(qapp):
    """두 번째 등장 행은 '[위 참조]' 표식이 라벨에 포함."""
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    items_for_mid = panel.items_for("Mid")
    second_text = items_for_mid[1].text(0)
    assert "위 참조" in second_text


def test_activate_works_on_any_occurrence(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    received: list[str] = []
    panel.navigate_requested.connect(received.append)
    items_for_mid = panel.items_for("Mid")
    panel._on_activated(items_for_mid[1], 0)
    assert received == ["Mid"]


def test_panel_preserves_all_nodes_fan_in(qapp):
    panel = DataFlowPanel()
    panel.show_result(_result_fan_in())
    assert panel.shown_node_names() == {"A", "B", "Mid", "S1", "S2"}


# ---- g15: r.isolated 직접 사용 테스트 ----

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.data_flow import analyze_data_flow


def _exec_pin(name: str, direction: str) -> Pin:
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def _data_pin(name: str, direction: str) -> Pin:
    return Pin(name=name, cpp_type="float", direction=direction)


def test_exec_only_connected_node_not_in_isolated_group(qtbot) -> None:
    """exec link로만 연결된 노드는 '고립/미연결'에 표시되지 않음."""
    entry = Node(name="Entry", cls="X",
                 pins=[_exec_pin("ExecOut", "Output")])
    body = Node(name="Body", cls="X",
                pins=[_exec_pin("ExecIn", "Input"),
                      _data_pin("Out", "Output")])
    consumer = Node(name="Consumer", cls="X",
                    pins=[_data_pin("In", "Input")])
    g = GraphModel(
        nodes=[entry, body, consumer],
        links=[
            Link(source_path="Entry.ExecOut", target_path="Body.ExecIn"),
            Link(source_path="Body.Out", target_path="Consumer.In"),
        ],
    )
    result = analyze_data_flow(g)
    panel = DataFlowPanel()
    qtbot.addWidget(panel)
    panel.show_result(result)

    isolated_group = None
    for i in range(panel._tree.topLevelItemCount()):
        item = panel._tree.topLevelItem(i)
        if item.text(0) == "고립/미연결":
            isolated_group = item
            break
    if isolated_group is None:
        return
    isolated_names = {isolated_group.child(i).text(0)
                      for i in range(isolated_group.childCount())}
    assert "Entry" not in isolated_names


def test_truly_isolated_node_still_in_group(qtbot) -> None:
    """진짜 어떤 link도 없는 노드는 그룹에 표시."""
    lonely = Node(name="Lonely", cls="X",
                  pins=[_data_pin("A", "Input")])
    connected_a = Node(name="CA", cls="X", pins=[_data_pin("Out", "Output")])
    connected_b = Node(name="CB", cls="X", pins=[_data_pin("In", "Input")])
    g = GraphModel(
        nodes=[lonely, connected_a, connected_b],
        links=[Link(source_path="CA.Out", target_path="CB.In")],
    )
    result = analyze_data_flow(g)
    panel = DataFlowPanel()
    qtbot.addWidget(panel)
    panel.show_result(result)

    isolated_group = None
    for i in range(panel._tree.topLevelItemCount()):
        item = panel._tree.topLevelItem(i)
        if item.text(0) == "고립/미연결":
            isolated_group = item
            break
    assert isolated_group is not None
    names = {isolated_group.child(i).text(0)
             for i in range(isolated_group.childCount())}
    assert "Lonely" in names
    assert "CA" not in names and "CB" not in names
