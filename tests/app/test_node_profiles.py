"""k1 (batch ⑭) — NodeStyleProfile + NodeProfileTable 단위."""
from pathlib import Path

import pytest

from t3dgraph.core.app.node_profiles import NodeStyleProfile, NodeProfileTable


def test_default_profile() -> None:
    p = NodeStyleProfile()
    assert p.show_var_badge is False
    assert p.always_show_chevron is False
    assert p.chevron_state_aware is False
    assert p.tooltip_when_no_subgraph is None
    assert p.layout_hint == "default"


@pytest.fixture
def bundled_table(tmp_path: Path, monkeypatch) -> NodeProfileTable:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    return NodeProfileTable.load()


def test_variable_node_has_var_badge(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMVariableNode")
    assert p.show_var_badge is True


def test_collapse_node_chevron_state_aware(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMCollapseNode")
    assert p.always_show_chevron is True
    assert p.chevron_state_aware is True


def test_function_reference_has_tooltip(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMFunctionReferenceNode")
    assert p.tooltip_when_no_subgraph is not None
    assert "함수" in p.tooltip_when_no_subgraph


def test_function_entry_outputs_only(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMFunctionEntryNode")
    assert p.layout_hint == "outputs_only"


def test_function_return_inputs_only(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMFunctionReturnNode")
    assert p.layout_hint == "inputs_only"


def test_reroute_passthrough(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMRerouteNode")
    assert p.layout_hint == "passthrough"


def test_unknown_class_returns_default(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("UnknownCustomNodeClass")
    assert p == NodeStyleProfile()


def test_first_load_copies_bundle_to_user_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "node_profiles.toml"
    assert not user_file.exists()
    NodeProfileTable.load()
    assert user_file.exists()
    bundle = NodeProfileTable._bundle_path()
    assert user_file.read_bytes() == bundle.read_bytes()


def test_user_file_overrides_bundle(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "node_profiles.toml"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text(
        '[profile.MyCustomNode]\nshow_var_badge = true\n',
        encoding="utf-8",
    )
    table = NodeProfileTable.load()
    custom = table.resolve("MyCustomNode")
    assert custom.show_var_badge is True


def test_user_file_partial_uses_default_for_unset(tmp_path, monkeypatch) -> None:
    """사용자 TOML에 일부 필드만 있으면 나머지는 디폴트."""
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "node_profiles.toml"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text(
        '[profile.Minimal]\nshow_var_badge = true\n',
        encoding="utf-8",
    )
    table = NodeProfileTable.load()
    p = table.resolve("Minimal")
    assert p.show_var_badge is True
    assert p.always_show_chevron is False
    assert p.layout_hint == "default"
