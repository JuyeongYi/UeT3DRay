"""smoke — Orion RigVMModel 로드 후 data flow PRESERVE-ALL 검증."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from t3dgraph.core.analysis.data_flow import analyze_data_flow
from pathlib import Path

ORION = Path(__file__).parent / "fixtures" / "orion"
target = next(ORION.glob("*RigVMModel*.t3d.txt"), None)
assert target is not None, f"RigVMModel fixture not found in {ORION}"

doc = parse_document(read_t3d_text(target))
plugin = default_registry().detect(doc)
graph = plugin.interpreter_factory().interpret(doc)
r = analyze_data_flow(graph)

print(f"data edges {len(r.data_edges)} · sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")
assert set(r.all_nodes) == {n.name for n in graph.nodes}, "PRESERVE-ALL 위반"
