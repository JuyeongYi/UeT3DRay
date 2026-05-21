"""smoke — Orion RigVMModel 로드 후 display_name != name 인 노드 존재 확인."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.registry import default_registry
from pathlib import Path

ORION = Path(__file__).parent / "fixtures" / "orion"
target = next(ORION.glob("*RigVMModel*.t3d.txt"), None)
assert target is not None, f"RigVMModel fixture not found in {ORION}"

doc = parse_document(target.read_text(encoding="utf-8"))
plugin = default_registry().detect(doc)
graph = plugin.interpreter_factory().interpret(doc)
filled = sum(1 for n in graph.nodes if n.display_name and n.display_name != n.name)
print(f"전체 {len(graph.nodes)} 중 {filled} 노드가 표시명 별도 부여")
assert filled > 0
