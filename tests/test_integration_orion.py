import pytest
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.registry import default_registry
from t3dgraph.core.analysis.flow import analyze_flow


def _all_files(orion_dir):
    return sorted(orion_dir.glob("*.t3d.txt"))


def test_eleven_fixture_files_present(orion_dir):
    assert len(_all_files(orion_dir)) == 11


def test_every_file_parses_and_interprets(orion_dir):
    reg = default_registry()
    for f in _all_files(orion_dir):
        doc = parse_document(f.read_text(encoding="utf-8"))
        plugin = reg.detect(doc)
        assert plugin.id == "rigvm"
        graph = plugin.interpreter_factory().interpret(doc)
        assert len(graph.nodes) > 0
        analyze_flow(graph)


def test_rigvmmodel_has_known_link(orion_dir):
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    doc = parse_document(f.read_text(encoding="utf-8"))
    graph = default_registry().detect(doc).interpreter_factory().interpret(doc)
    pairs = {(l.source_path, l.target_path) for l in graph.links}
    assert ("IK_Rig.ExecuteContext", "StepPhysicsSolver.ExecutePin") in pairs


def test_samples_have_no_fan_in(orion_dir):
    reg = default_registry()
    for f in _all_files(orion_dir):
        doc = parse_document(f.read_text(encoding="utf-8"))
        graph = reg.detect(doc).interpreter_factory().interpret(doc)
        assert analyze_flow(graph).convergence_points == []
