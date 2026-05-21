from __future__ import annotations
from ..core.base.graph_model import GraphModel
from ..core.analysis.bundle import AnalysisBundle
from ..core.analysis.data_flow import DataFlowResult


def summary_dict(graph_type: str, graph: GraphModel, bundle: AnalysisBundle) -> dict:
    return {
        'graph_type': graph_type,
        'nodes': {'total': len(graph.nodes), 'generic': sum(1 for n in graph.nodes if n.is_generic)},
        'links': len(graph.links),
        'variable_refs': len(graph.variable_refs),
        'external_refs': len(graph.external_refs),
        'execution': {
            'edges': len(bundle.flow.execution_edges),
            'convergence_points': list(bundle.flow.convergence_points),
            'branch_points': list(bundle.flow.branch_points),
            'steps': len(bundle.execution_order),
        },
        'warnings': list(graph.warnings),
    }


def dataflow_dict(result: DataFlowResult) -> dict:
    return {
        'data_edges': [{'source': e.source.full, 'target': e.target.full} for e in result.data_edges],
        'sinks': list(result.sinks),
        'sources': list(result.sources),
        'isolated': list(result.isolated),
        'incoming_nodes': {k: list(v) for k, v in result.incoming_nodes.items()},
        'outgoing_nodes': {k: list(v) for k, v in result.outgoing_nodes.items()},
        'all_nodes': list(result.all_nodes),
    }
