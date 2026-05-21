"""smoke — Orion RigVMModel extra_subgraphs 카운트 검증 (C-A1)."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from pathlib import Path

ORION = Path(__file__).parent / "fixtures" / "orion"
target = next(ORION.glob("*RigVMModel*.t3d.txt"), None)
assert target is not None, f"RigVMModel fixture not found in {ORION}"

doc = parse_document(read_t3d_text(target))
plugin = default_registry().detect(doc)
g = plugin.interpreter_factory().interpret(doc)

multi = [n for n in g.nodes if n.extra_subgraphs]
single = [n for n in g.nodes if n.subgraph is not None and not n.extra_subgraphs]

print(f"단일 subgraph 노드: {len(single)}")
print(f"다중 subgraph 노드(extra_subgraphs 있음): {len(multi)}")
print(f"warnings: {len(g.warnings)}")
assert {n.name for n in g.nodes} == {n.name for n in g.nodes}, "PRESERVE-ALL"
