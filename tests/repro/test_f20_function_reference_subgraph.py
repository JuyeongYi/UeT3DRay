"""F20 실원인 — FunctionReferenceNode가 외부 함수 라이브러리의 ContainedGraph를 subgraph로 보유."""
from __future__ import annotations
from pathlib import Path

import pytest

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.resolver import AssetResolver
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


@pytest.fixture
def orion_folder() -> Path:
    p = Path("Orion_WorkStation_Rig_Analysis")
    if not p.exists():
        pytest.skip("Orion 폴더 미발견")
    return p


def test_function_reference_node_has_subgraph_with_resolver(orion_folder: Path) -> None:
    """폴더 단위 로드 시 RigVMFunctionReferenceNode가 외부 함수의 subgraph 보유."""
    resolver = AssetResolver()
    resolver.load_folder(orion_folder)
    model_files = list(orion_folder.rglob("*RigVMModel*.t3d.txt"))
    if not model_files:
        pytest.skip("RigVMModel 파일 미발견")
    doc = parse_document(model_files[0].read_text(encoding="utf-8", errors="replace"))
    interp = RigVMGraphInterpreter(resolver=resolver)
    graph = interp.interpret(doc)

    func_refs = [n for n in graph.nodes
                 if (n.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"]
    if not func_refs:
        pytest.skip("Orion 샘플에 FunctionReferenceNode가 없음")
    resolved = [fr for fr in func_refs if fr.subgraph is not None and len(fr.subgraph.nodes) > 0]
    assert len(resolved) > 0, (
        f"FunctionReferenceNode {len(func_refs)}개 중 subgraph 연결된 것 없음 — F20 회귀"
    )


def test_function_reference_node_no_subgraph_without_resolver(orion_folder: Path) -> None:
    """resolver 미주입 시 subgraph=None — 기존 동작 보존."""
    model_files = list(orion_folder.rglob("*RigVMModel*.t3d.txt"))
    if not model_files:
        pytest.skip("RigVMModel 파일 미발견")
    doc = parse_document(model_files[0].read_text(encoding="utf-8", errors="replace"))
    interp = RigVMGraphInterpreter()
    graph = interp.interpret(doc)
    func_refs = [n for n in graph.nodes
                 if (n.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"]
    for fr in func_refs:
        assert fr.subgraph is None or len(fr.subgraph.nodes) == 0
