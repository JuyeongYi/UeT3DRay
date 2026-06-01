"""h2 (α-A2) — _extract_target_path 실패 시 raw ref_path 보존."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.resolver import AssetResolver
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_ref_path_preserved_when_extract_fails() -> None:
    """비표준 ref_path → unresolved에 원본 + 사유 메타."""
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        '   ReferencedNode="ThisIsAnUnparseableRef"\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter(resolver=AssetResolver()).interpret(doc)
    assert g.diagnostics is not None
    unresolved = g.diagnostics.external_refs_unresolved
    assert any(
        "ThisIsAnUnparseableRef" in r for r in unresolved
    ), f"ref_path 정보 손실 — unresolved={unresolved}"


def test_normal_ref_path_listed_as_is_without_resolver() -> None:
    """resolver 미주입 시 정상 ref도 그대로 등재."""
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
    assert any("Class'/Game/Lib.Lib:RigVMModel.Func'" in r for r in unresolved), (
        f"정상 ref 등재 실패 — {unresolved}"
    )
