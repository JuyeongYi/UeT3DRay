"""RigVMGraphInterpreter — 다중 ContainedGraph 자식 보존 (C-A1)."""
from __future__ import annotations
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _t3d(name: str, cls: str, children: list[T3DObject] | None = None) -> T3DObject:
    return T3DObject(
        name=name, cls=cls,
        export_path=None, header_raw="",
        properties={}, children=children or [],
    )


def _unit(name: str) -> T3DObject:
    return _t3d(name, "/Script/RigVMDeveloper.RigVMUnitNode")


def _graph_child(name: str, inner_nodes: list[T3DObject]) -> T3DObject:
    return _t3d(name, "/Script/RigVMDeveloper.RigVMGraph", inner_nodes)


def _collapse(name: str, graph_children: list[T3DObject]) -> T3DObject:
    return _t3d(name, "/Script/RigVMDeveloper.RigVMCollapseNode", graph_children)


def test_single_subgraph_unchanged():
    obj = _collapse("Solo", [_graph_child("Solo_ContainedGraph", [_unit("Inner")])])
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    parent = g.nodes[0]
    assert parent.subgraph is not None
    assert parent.extra_subgraphs == []


def test_two_subgraph_children_both_preserved():
    obj = _collapse("P", [
        _graph_child("P_ContainedGraph", [_unit("A")]),
        _graph_child("P_ContainedGraph_2", [_unit("B")]),
    ])
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    parent = g.nodes[0]
    assert parent.subgraph is not None
    assert [n.name for n in parent.subgraph.nodes] == ["A"]
    assert len(parent.extra_subgraphs) == 1
    assert [n.name for n in parent.extra_subgraphs[0].nodes] == ["B"]


def test_two_subgraph_warning_emitted():
    obj = _collapse("P", [
        _graph_child("c1", [_unit("X")]),
        _graph_child("c2", [_unit("Y")]),
    ])
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    assert any("RigVMGraph 자식" in w and "P" in w for w in g.warnings)


def test_three_subgraph_children_all_preserved():
    obj = _collapse("P", [
        _graph_child(f"c{i}", [_unit(f"N{i}")]) for i in range(3)
    ])
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    parent = g.nodes[0]
    assert parent.subgraph is not None
    assert len(parent.extra_subgraphs) == 2
