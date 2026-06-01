"""DroppedObject·InterpreterDiagnostics 자료구조 단위."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import (
    DroppedObject, InterpreterDiagnostics, GraphModel,
)


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
