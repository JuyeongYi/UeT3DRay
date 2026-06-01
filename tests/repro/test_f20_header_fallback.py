"""α (ρ-A3) — ReferencedFunctionHeader 구조 폴백 + 명시 등재."""
from __future__ import annotations
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter

def test_header_parse_failure_recorded_as_unresolved() -> None:
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    unresolved = g.diagnostics.external_refs_unresolved
    assert any("header parse failed" in r and "FR1" in r for r in unresolved), (
        f"FR1 미등재 — silent miss (ρ-A3 회귀). unresolved={unresolved}"
    )

def test_header_with_referenced_node_uses_extracted_path() -> None:
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        '   ReferencedNode="Class\'/Game/Lib.Lib:RigVMModel.Func\'"\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    unresolved = g.diagnostics.external_refs_unresolved
    assert not any("header parse failed" in r for r in unresolved)
