"""DroppedObject·InterpreterDiagnostics 자료구조 단위."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import (
    DroppedObject, InterpreterDiagnostics, GraphModel,
)
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_dropped_object_fields() -> None:
    d = DroppedObject(name="N1", cls="/Script/X.Foo",
                      reason="unknown class", parent_obj=None)
    assert d.name == "N1"
    assert d.cls == "/Script/X.Foo"
    assert d.reason == "unknown class"
    assert d.parent_obj is None


def test_diagnostics_defaults_empty() -> None:
    diag = InterpreterDiagnostics()
    assert diag.objects_dropped == []
    assert diag.extracted_per_class == {}
    assert diag.max_depth_seen == 0
    assert diag.contained_graph_count == 0
    assert diag.external_refs_unresolved == []


def test_graph_model_diagnostics_default_none() -> None:
    g = GraphModel()
    assert g.diagnostics is None


def test_graph_model_diagnostics_attach() -> None:
    g = GraphModel()
    diag = InterpreterDiagnostics()
    diag.objects_dropped.append(DroppedObject("N1", "X", "unknown", None))
    diag.extracted_per_class["RigVMUnitNode"] = 5
    g.diagnostics = diag
    assert g.diagnostics is not None
    assert g.diagnostics.extracted_per_class["RigVMUnitNode"] == 5
    assert len(g.diagnostics.objects_dropped) == 1


def test_interpret_always_attaches_diagnostics() -> None:
    doc = T3DDocument(objects=[])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    assert isinstance(g.diagnostics.extracted_per_class, dict)
    assert g.diagnostics.max_depth_seen == 0


def test_unknown_class_recorded_as_dropped() -> None:
    obj = T3DObject(cls="/Script/X.Foo", name="N1", export_path=None,
                    header_raw="", properties={}, children=[])
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    dropped_classes = [d.cls for d in g.diagnostics.objects_dropped]
    # _add_generic 는 노드를 생성하지만 진단에도 "unknown class"로 기록
    assert "/Script/X.Foo" in dropped_classes
    reasons = [d.reason for d in g.diagnostics.objects_dropped]
    assert "unknown class" in reasons


def test_extracted_per_class_counts_node_suffixes() -> None:
    # RigVMUnitNode 두 개
    u1 = T3DObject(cls="/Script/RigVMDeveloper.RigVMUnitNode", name="U1",
                   export_path=None, header_raw="", properties={}, children=[])
    u2 = T3DObject(cls="/Script/RigVMDeveloper.RigVMUnitNode", name="U2",
                   export_path=None, header_raw="", properties={}, children=[])
    doc = T3DDocument(objects=[u1, u2])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    assert g.diagnostics.extracted_per_class.get("RigVMUnitNode") == 2
