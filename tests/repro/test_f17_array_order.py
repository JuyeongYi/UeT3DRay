"""F17 repro — UE array subpin reverse-serialization fix.

UE serializes RigVMPin array children in reverse index order (10,9,...,0).
After the fix, subpins with digit-only names must appear in ascending int order.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.registry import default_registry


FIXTURES = Path(__file__).parent.parent / "fixtures" / "orion"
ORION_RIGVMMODEL = (
    FIXTURES
    / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
)


@pytest.fixture
def orion_doc():
    text = ORION_RIGVMMODEL.read_text(encoding="utf-8")
    doc = parse_document(text)
    reg = default_registry()
    return reg.detect(doc).interpreter_factory().interpret(doc)


def test_array_subpin_order_preserved_orion(orion_doc) -> None:
    """ItemArray.Value subpins should be in ascending int order (0,1,...,10)."""
    graph = orion_doc
    item_array_node = next(
        (n for n in graph.nodes if n.name == "ItemArray"), None
    )
    assert item_array_node is not None, "ItemArray node not found in graph"

    value_pin = next(
        (p for p in item_array_node.pins if p.name == "Value"), None
    )
    assert value_pin is not None, "Value pin not found on ItemArray node"

    subpin_names = [p.name for p in value_pin.subpins]
    assert subpin_names == [str(i) for i in range(len(subpin_names))], (
        f"Expected ascending order 0..{len(subpin_names)-1}, got: {subpin_names}"
    )


def test_array_subpin_count_orion(orion_doc) -> None:
    """ItemArray.Value should have 11 subpins (0 through 10)."""
    graph = orion_doc
    item_array_node = next(
        (n for n in graph.nodes if n.name == "ItemArray"), None
    )
    assert item_array_node is not None

    value_pin = next(
        (p for p in item_array_node.pins if p.name == "Value"), None
    )
    assert value_pin is not None
    assert len(value_pin.subpins) == 11
