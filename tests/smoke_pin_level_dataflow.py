"""smoke — Orion RigVMModel 데이터 엣지 PRESERVE-INFO 검증."""
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

edges_with_pin_info = sum(1 for e in r.data_edges
                          if e.source.pin_path and e.target.pin_path)
print(f"data edges {len(r.data_edges)} · pin info 포함 {edges_with_pin_info}")
assert edges_with_pin_info == len(r.data_edges), "모든 데이터 엣지는 핀 정보를 가져야 함"
assert set(r.all_nodes) == {n.name for n in graph.nodes}, "PRESERVE-ALL 위반"
print(f"sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")
