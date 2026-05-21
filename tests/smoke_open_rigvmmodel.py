"""smoke — 샘플 파일을 로드해 노드 수가 보존되는지 확인."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.registry import default_registry
from pathlib import Path

ORION = Path(__file__).parent / "fixtures" / "orion"
target = next(ORION.glob("*RigVMModel*.t3d.txt"), None)
assert target is not None, f"RigVMModel fixture not found in {ORION}"

doc = parse_document(target.read_text(encoding="utf-8"))
plugin = default_registry().detect(doc)
graph = plugin.interpreter_factory().interpret(doc)
print(f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}")
assert len(graph.nodes) > 0
