"""smoke — AnalysisBundle on Orion data (D-B3)."""
from pathlib import Path
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.encoding import read_t3d_text
from t3dgraph.core.registry import default_registry
from t3dgraph.core.analysis.bundle import run as run_analyses

ORION = Path(__file__).parent / "fixtures" / "orion"
target = next(ORION.glob("*RigVMModel*.t3d.txt"), None)
assert target is not None, f"RigVMModel fixture not found in {ORION}"

doc = parse_document(read_t3d_text(target))
g = default_registry().detect(doc).interpreter_factory().interpret(doc)
b = run_analyses(g)

print(f"flow exec edges {len(b.flow.execution_edges)} · steps {len(b.execution_order)} · data edges {len(b.data_flow.data_edges)}")
assert b.data_flow.all_nodes, "PRESERVE-ALL: all_nodes 비어 있음"
