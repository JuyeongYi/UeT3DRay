"""F17 재현 — 배열 subpin 순서가 T3D 원본 객체 순서와 일치.

σ 슬라이스가 본 어서션을 통과시켜야 한다.
"""
from __future__ import annotations

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _build_array_doc_text(item_names: list[str]) -> str:
    """RigVMPin 배열을 자식으로 가진 노드 1개짜리 T3D 텍스트 생성."""
    items_block = "\n".join(
        f'Begin Object Name="{name}" Class=/Script/RigVMDeveloper.RigVMPin\nEnd Object'
        for name in item_names
    )
    return f"""Begin Object Name="N1" Class=/Script/RigVMDeveloper.RigVMUnitNode
   Begin Object Name="Items" Class=/Script/RigVMDeveloper.RigVMPin
{items_block}
   End Object
End Object
"""


def test_array_subpin_order_preserved_synth() -> None:
    """합성 T3D — subpin 순서 == 원본 순서."""
    names = ["0", "1", "2", "3"]
    text = _build_array_doc_text(names)
    doc = parse_document(text)
    graph = RigVMGraphInterpreter().interpret(doc)
    assert len(graph.nodes) == 1
    items_pin = next(p for p in graph.nodes[0].pins if p.name == "Items")
    actual = [sp.name for sp in items_pin.subpins]
    assert actual == names, (
        f"배열 subpin 순서 역전 — expected={names}, actual={actual}"
    )


def test_array_subpin_order_preserved_orion(orion_doc) -> None:
    """Orion 샘플 — 배열 핀이 있는 경우 모두 단조 검사."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    violations: list[tuple[str, str, list[str]]] = []

    def walk(g) -> None:
        for node in g.nodes:
            for pin in node.pins:
                _check_pin(node.name, pin)
            if node.subgraph is not None:
                walk(node.subgraph)
            for extra in node.extra_subgraphs:
                walk(extra)

    def _check_pin(node_name: str, pin) -> None:
        names = [sp.name for sp in pin.subpins]
        if names and all(n.isdigit() for n in names):
            indices = [int(n) for n in names]
            if indices != sorted(indices):
                violations.append((node_name, pin.name, names))
        for sp in pin.subpins:
            _check_pin(node_name, sp)

    walk(graph)
    assert not violations, (
        f"F17 회귀 — 배열 subpin 순서 역전 {len(violations)}건 "
        f"(첫 5건): {violations[:5]}"
    )
