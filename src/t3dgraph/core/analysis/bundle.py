"""분석 3종을 단일 출처로 묶는 AnalysisBundle (D-B3)."""
from __future__ import annotations
from dataclasses import dataclass
from ..base.graph_model import GraphModel
from .flow import FlowResult, analyze_flow
from .execution_order import ExecutionStep, compute_execution_order
from .data_flow import DataFlowResult, analyze_data_flow


@dataclass
class AnalysisBundle:
    flow: FlowResult
    execution_order: list[ExecutionStep]
    data_flow: DataFlowResult


def run(graph: GraphModel) -> AnalysisBundle:
    f = analyze_flow(graph)
    return AnalysisBundle(
        flow=f,
        execution_order=compute_execution_order(graph, f),
        data_flow=analyze_data_flow(graph),
    )
