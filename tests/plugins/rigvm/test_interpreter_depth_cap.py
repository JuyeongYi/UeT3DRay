"""_interpret_objects 깊이 cap — 재귀 폭발 방지 (C-A2)."""
from __future__ import annotations
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.base.graph_model import InterpreterDiagnostics
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _t3d(name: str, cls: str, children: list[T3DObject] | None = None) -> T3DObject:
    return T3DObject(
        name=name, cls=cls,
        export_path=None, header_raw="",
        properties={}, children=children or [],
    )


def _unit(name: str) -> T3DObject:
    return _t3d(name, "/Script/RigVMDeveloper.RigVMUnitNode")


def _nest(depth: int) -> T3DObject:
    """depth 단계로 중첩된 CollapseNode 트리."""
    inner = _unit("Leaf")
    obj = inner
    for i in range(depth):
        graph = _t3d(f"g{i}", "/Script/RigVMDeveloper.RigVMGraph", [obj])
        obj = _t3d(f"c{i}", "/Script/RigVMDeveloper.RigVMCollapseNode", [graph])
    return obj


def test_normal_depth_no_depth_warning():
    obj = _nest(5)
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    assert all("깊이" not in w for w in g.warnings)


def test_excessive_depth_caps_with_warning():
    obj = _nest(100)
    g = RigVMGraphInterpreter().interpret(T3DDocument(objects=[obj]))
    assert len(g.nodes) == 1
    assert any("깊이" in w for w in g.warnings)


def test_custom_max_depth():
    obj = _nest(10)
    interp = RigVMGraphInterpreter()
    diag = InterpreterDiagnostics()
    g = interp._interpret_objects(
        [obj], label=None, parent_node=None, diagnostics=diag, depth=0, max_depth=3
    )
    assert any("깊이" in w for w in g.warnings)
