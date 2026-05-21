"""AnalysisBundle — 분석 3종 단일 출처 (D-B3)."""
from __future__ import annotations
from t3dgraph.core.analysis.bundle import AnalysisBundle, run
from t3dgraph.core.analysis.flow import FlowResult
from t3dgraph.core.analysis.data_flow import DataFlowResult
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_run_returns_bundle_with_three_results():
    g = GraphModel(
        nodes=[
            Node(name="A", cls=None, pins=[Pin(name="O", cpp_type="float", direction="Output")]),
            Node(name="B", cls=None, pins=[Pin(name="I", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.O", target_path="B.I")],
    )
    b = run(g)
    assert isinstance(b, AnalysisBundle)
    assert isinstance(b.flow, FlowResult)
    assert isinstance(b.data_flow, DataFlowResult)
    assert b.execution_order == []   # exec edge 없음


def test_bundle_carries_consistent_graph_analysis():
    g = GraphModel(nodes=[Node(name="X", cls=None)])
    b = run(g)
    assert b.data_flow.all_nodes == ["X"]
