"""ContainedGraph 재귀 추출 단위 테스트 (F6 — internal subgraph)."""
from __future__ import annotations

from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


UNIT = "/Script/RigVMDeveloper.RigVMUnitNode"
COLLAPSE = "/Script/RigVMDeveloper.RigVMCollapseNode"
GRAPH = "/Script/RigVMDeveloper.RigVMGraph"


def _obj(name: str, cls: str, children: list[T3DObject] | None = None) -> T3DObject:
    return T3DObject(
        cls=cls,
        name=name,
        export_path=None,
        header_raw="",
        properties={},
        children=children or [],
    )


def test_collapse_node_subgraph_extracted():
    inner_node = _obj("Inner1", UNIT)
    contained = _obj("CollapseNode_ContainedGraph", GRAPH, children=[inner_node])
    collapse = _obj("MyCollapse", COLLAPSE, children=[contained])
    doc = T3DDocument(objects=[collapse])

    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1, "부모 그래프엔 collapse 노드 1개만"
    parent = g.nodes[0]
    assert parent.name == "MyCollapse"
    assert parent.subgraph is not None
    assert [n.name for n in parent.subgraph.nodes] == ["Inner1"]
    assert parent.subgraph.parent_node == "MyCollapse"
    assert parent.subgraph.label  # 비어 있지 않음


def test_preserves_parent_node_when_subgraph_extracted():
    """PRESERVE-ALL: 자식 추출이 부모를 절대 사라지게 하지 않음."""
    inner_node = _obj("Inner1", UNIT)
    contained = _obj("X_ContainedGraph", GRAPH, children=[inner_node])
    collapse = _obj("P", COLLAPSE, children=[contained])
    doc = T3DDocument(objects=[collapse])

    g = RigVMGraphInterpreter().interpret(doc)
    parent_names = {n.name for n in g.nodes}
    assert "P" in parent_names                   # 부모는 그대로
    assert "Inner1" not in parent_names          # 자식은 부모 그래프에 들어가지 않음
    # 자식은 subgraph에만 존재
    assert "Inner1" in {n.name for n in g.nodes[0].subgraph.nodes}


def test_subgraph_recursion_depth():
    """N단계 중첩 — 폭주 없이 추출."""
    leaf = _obj("Leaf", UNIT)
    level3 = _obj("L3_ContainedGraph", GRAPH, children=[leaf])
    mid_collapse = _obj("Mid", COLLAPSE, children=[level3])
    level2 = _obj("L2_ContainedGraph", GRAPH, children=[mid_collapse])
    outer_collapse = _obj("Outer", COLLAPSE, children=[level2])
    doc = T3DDocument(objects=[outer_collapse])

    g = RigVMGraphInterpreter().interpret(doc)
    outer = g.nodes[0]
    mid = outer.subgraph.nodes[0]
    assert mid.name == "Mid"
    assert mid.subgraph.nodes[0].name == "Leaf"


def test_top_level_graph_unchanged_when_no_subgraph():
    """기존 동작 회귀 — collapse 없는 일반 노드는 subgraph None."""
    plain = _obj("Plain", UNIT)
    doc = T3DDocument(objects=[plain])
    g = RigVMGraphInterpreter().interpret(doc)
    assert len(g.nodes) == 1
    assert g.nodes[0].subgraph is None
