"""Slice C 스모크 — Orion RigVMModel의 ContainedGraph 추출 검증.

PRESERVE-ALL 불변식 확인:
- 부모 그래프의 nodes 리스트는 자식 추출 시 변경되지 않음.
- 자식은 별도 GraphModel 인스턴스(node.subgraph)에만 존재.
"""
from __future__ import annotations

from t3dgraph.core.registry import default_registry
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text


def test_orion_rigvm_model_extracts_at_least_one_subgraph(orion_dir):
    p = orion_dir / (
        "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR"
        "__RigVMModel.t3d.txt"
    )
    doc = parse_document(read_t3d_text(p))
    plugin = default_registry().detect(doc)
    g = plugin.interpreter_factory().interpret(doc)

    subgraph_holders = [n for n in g.nodes if n.subgraph is not None]
    assert subgraph_holders, "최소 1개 CollapseNode/FunctionRef가 서브그래프를 가져야 함"

    # PRESERVE-ALL: 자식 노드 이름이 부모 nodes 리스트에 섞이지 않음을 확인.
    parent_names = {n.name for n in g.nodes}
    for holder in subgraph_holders:
        for inner in holder.subgraph.nodes:
            assert inner.name not in parent_names or inner.name == holder.name, (
                f"자식 노드 '{inner.name}'가 부모 그래프에도 존재 — PRESERVE-ALL 위반"
            )
        assert holder.subgraph.parent_node == holder.name
        assert holder.subgraph.label, "subgraph label은 비어 있지 않아야 함"


def test_orion_subgraph_holder_count_recorded(orion_dir, capsys):
    p = orion_dir / (
        "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR"
        "__RigVMModel.t3d.txt"
    )
    doc = parse_document(read_t3d_text(p))
    g = default_registry().detect(doc).interpreter_factory().interpret(doc)
    holders = [n for n in g.nodes if n.subgraph is not None]
    print(f"전체 {len(g.nodes)} 중 {len(holders)} 노드가 서브그래프 보유")
    for h in holders:
        print(f"  - {h.name}: 내부 노드 {len(h.subgraph.nodes)} · 링크 {len(h.subgraph.links)}")
    captured = capsys.readouterr()
    assert "서브그래프 보유" in captured.out
