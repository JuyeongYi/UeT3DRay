import pytest
from t3dgraph.core.registry import Registry
from t3dgraph.core.base.plugin import GraphTypePlugin
from t3dgraph.core.t3d.document import parse_document


def _plugin(pid, prefixes):
    return GraphTypePlugin(id=pid, class_prefixes=prefixes, interpreter_factory=lambda: None)


def test_register_and_detect():
    reg = Registry()
    reg.register(_plugin("rigvm", ["/Script/RigVMDeveloper."]))
    doc = parse_document('Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="N"\nEnd Object\n')
    assert reg.detect(doc).id == "rigvm"


def test_detect_no_match_raises():
    reg = Registry()
    doc = parse_document('Begin Object Class=/Script/Other.Thing Name="N"\nEnd Object\n')
    with pytest.raises(LookupError):
        reg.detect(doc)


def test_duplicate_id_raises():
    reg = Registry()
    reg.register(_plugin("x", ["/A."]))
    with pytest.raises(ValueError):
        reg.register(_plugin("x", ["/B."]))
