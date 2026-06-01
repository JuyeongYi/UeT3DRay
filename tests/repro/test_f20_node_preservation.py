"""F20 재현 — 인터프리터가 모든 노드 후보를 추출 또는 dropped로 기록.

ρ 슬라이스가 본 파일의 어서션을 통과시켜야 한다.
"""
from __future__ import annotations

import pytest

from t3dgraph.core.base.graph_model import GraphModel
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


_NODE_EXCLUDED_SUFFIXES = ("RigVMPin", "RigVMLink", "RigVMGraph")


def _count_node_candidates(objects: list[T3DObject]) -> int:
    """T3D 객체 트리(중첩 포함)에서 노드 후보 수."""
    n = 0
    for o in objects:
        cls = o.cls or ""
        if cls.startswith("/Script/RigVM") and not any(
                cls.endswith(s) for s in _NODE_EXCLUDED_SUFFIXES):
            n += 1
        n += _count_node_candidates(o.children)
    return n


def _count_extracted_nodes(g: GraphModel) -> int:
    """GraphModel 트리(subgraph·extra_subgraphs 포함)에서 추출된 노드 수."""
    total = len(g.nodes)
    for node in g.nodes:
        if node.subgraph is not None:
            total += _count_extracted_nodes(node.subgraph)
        for extra in node.extra_subgraphs:
            total += _count_extracted_nodes(extra)
    return total


def test_orion_sample_node_preservation(orion_doc: T3DDocument) -> None:
    """모든 노드 후보가 추출 또는 dropped 목록에 들어간다 — 잠적 0."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    expected = _count_node_candidates(orion_doc.objects)
    extracted = _count_extracted_nodes(graph)
    dropped = len(graph.diagnostics.objects_dropped)
    assert extracted + dropped >= expected, (
        f"노드 잠적: expected={expected}, extracted={extracted}, dropped={dropped}, "
        f"dropped_classes={ {d.cls for d in graph.diagnostics.objects_dropped} }"
    )


def test_extracted_per_class_snapshot(orion_doc: T3DDocument) -> None:
    """핵심 클래스는 0이 아니어야 함 — extractor 동작 sanity."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    units = graph.diagnostics.extracted_per_class.get("RigVMUnitNode", 0)
    dispatch = graph.diagnostics.extracted_per_class.get("RigVMDispatchNode", 0)
    assert units + dispatch > 0, (
        f"노드 추출 0 — extractor 동작 의심. 분포: "
        f"{graph.diagnostics.extracted_per_class}"
    )


def test_no_unknown_classes_after_fix(orion_doc: T3DDocument) -> None:
    """ρ 머지 충족 조건 — unknown class dropped 0."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    unknown = [d for d in graph.diagnostics.objects_dropped
               if d.reason == "unknown class"]
    assert unknown == [], (
        f"미알 클래스 {len(unknown)}개 — NODE_CLASS_SUFFIXES 확장 필요: "
        f"{ {d.cls for d in unknown} }"
    )


def test_no_unresolved_external_refs_after_fix(orion_doc: T3DDocument) -> None:
    """ρ 머지 충족 조건 — AssetResolver가 모든 external_ref 해결."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    assert graph.diagnostics is not None
    assert graph.diagnostics.external_refs_unresolved == [], (
        f"미해결 external_refs: {graph.diagnostics.external_refs_unresolved}"
    )
