"""ω/h1 — PersistentState 단위 (라운드트립·폴백·atomic·v2 multi-key)."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from t3dgraph.core.app.persistent_state import (
    PersistentState, GraphState, _state_path, load_state, save_state,
)


@pytest.fixture(autouse=True)
def _state_dir_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    return tmp_path


def test_state_path_uses_sha256_of_abs_path(tmp_path) -> None:
    p1 = _state_path("/some/path/a.t3d.txt")
    p2 = _state_path("/some/path/b.t3d.txt")
    assert p1 != p2
    assert p1.suffix == ".json"
    assert len(p1.stem) == 64  # sha256 hex


def test_save_then_load_round_trip() -> None:
    state = PersistentState(
        schema_version=2,
        per_graph={
            "root/": GraphState(
                node_positions={"N1": (10.0, 20.0), "N2": (-5.5, 3.3)},
                expanded_pin_paths=["N1.P", "N1.P.X"],
                connected_pins_only=True,
                fan_in_highlight=False,
                hidden_node_types=["RigVMUnitNode"],
            )
        },
    )
    save_state("/test/file.t3d.txt", state)
    loaded, error = load_state("/test/file.t3d.txt")
    assert error is None
    assert loaded.schema_version == 2
    assert "root/" in loaded.per_graph
    gs = loaded.per_graph["root/"]
    assert gs.node_positions == {"N1": (10.0, 20.0), "N2": (-5.5, 3.3)}
    assert gs.connected_pins_only is True


def test_load_missing_returns_empty() -> None:
    loaded, error = load_state("/non/existent/file.t3d.txt")
    assert error is None
    assert loaded.per_graph == {}
    assert loaded.schema_version == 2


def test_load_corrupted_json_returns_empty() -> None:
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ broken", encoding="utf-8")
    state, error = load_state("/test/x.t3d.txt")
    assert state == PersistentState()
    assert error is not None and "JSON" in error
    assert p.with_suffix(p.suffix + ".bak").exists()


def test_future_schema_version_returns_empty() -> None:
    """미래 버전은 사용자 데이터 손실 차단을 위해 빈 상태."""
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 999}', encoding="utf-8")
    state, error = load_state("/test/x.t3d.txt")
    assert state == PersistentState()
    assert error is not None and "schema_version" in error
    assert not p.with_suffix(p.suffix + ".bak").exists()


def test_load_state_returns_tuple_normal() -> None:
    save_state("/test/x.t3d.txt", PersistentState(schema_version=2, per_graph={}))
    state, error = load_state("/test/x.t3d.txt")
    assert error is None
    assert state.schema_version == 2


def test_load_state_missing_returns_empty_no_error() -> None:
    state, error = load_state("/non/existent/file2.t3d.txt")
    assert state == PersistentState()
    assert error is None


def test_save_is_atomic() -> None:
    """save 후 .tmp 파일 잔존 없음."""
    save_state("/test/x.t3d.txt", PersistentState(connected_pins_only=True))
    p = _state_path("/test/x.t3d.txt")
    assert p.exists()
    assert not p.with_suffix(p.suffix + ".tmp").exists()


def test_save_creates_parent_dir() -> None:
    save_state("/deep/path/file.t3d.txt", PersistentState())
    p = _state_path("/deep/path/file.t3d.txt")
    assert p.parent.exists()


def test_round_trip_preserves_position_floats() -> None:
    state = PersistentState(
        schema_version=2,
        per_graph={"root/": GraphState(node_positions={"N1": (-1.5, 2.7e3)})},
    )
    save_state("/test/f.t3d.txt", state)
    loaded, error = load_state("/test/f.t3d.txt")
    assert error is None
    assert loaded.per_graph["root/"].node_positions == {"N1": (-1.5, 2700.0)}


def test_per_graph_round_trip() -> None:
    """multi-key 라운드트립 — h1 ω-A1."""
    state = PersistentState(
        schema_version=2,
        per_graph={
            "rootA/": GraphState(
                node_positions={"N1": (1.0, 2.0)},
                expanded_pin_paths=["N1.P"],
                connected_pins_only=True,
            ),
            "rootA/SubB": GraphState(
                node_positions={"M1": (3.0, 4.0)},
                fan_in_highlight=True,
            ),
        },
    )
    save_state("/test/f.t3d.txt", state)
    loaded, error = load_state("/test/f.t3d.txt")
    assert error is None
    assert loaded.schema_version == 2
    assert "rootA/" in loaded.per_graph
    assert loaded.per_graph["rootA/"].node_positions == {"N1": (1.0, 2.0)}
    assert loaded.per_graph["rootA/SubB"].fan_in_highlight is True


def test_schema_v1_absorbed() -> None:
    """schema_version=1 로드 시 v2로 정규화 — per_graph[""]에 flat 필드 흡수."""
    p = _state_path("/test/legacy.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "schema_version": 1,
        "node_positions": [{"node": "N1", "x": 10.0, "y": 20.0}],
        "expanded_pin_paths": ["N1.P"],
        "connected_pins_only": True,
        "fan_in_highlight": False,
        "hidden_node_types": [],
    }), encoding="utf-8")
    loaded, error = load_state("/test/legacy.t3d.txt")
    assert error is None
    assert loaded.schema_version == 2
    assert loaded.migrated_from_v1 is True
    assert "" in loaded.per_graph
    gs = loaded.per_graph[""]
    assert gs.node_positions == {"N1": (10.0, 20.0)}
    assert gs.connected_pins_only is True
    assert gs.expanded_pin_paths == ["N1.P"]


def test_from_dict_v1_normalizes_to_v2() -> None:
    data = {
        "schema_version": 1,
        "node_positions": [{"node": "A", "x": 1.0, "y": 2.0}],
        "expanded_pin_paths": ["A.p"],
        "connected_pins_only": False,
        "fan_in_highlight": True,
        "hidden_node_types": ["loop"],
    }
    state = PersistentState.from_dict(data)
    assert state.schema_version == 2
    assert state.migrated_from_v1 is True
    assert "" in state.per_graph
    gs = state.per_graph[""]
    assert gs.node_positions == {"A": (1.0, 2.0)}
    assert gs.fan_in_highlight is True
    assert gs.hidden_node_types == ["loop"]


def test_from_dict_v2_no_migration_flag() -> None:
    data = {
        "schema_version": 2,
        "per_graph": {"k/": {"node_positions": [], "expanded_pin_paths": [],
                              "connected_pins_only": False, "fan_in_highlight": False,
                              "hidden_node_types": []}},
    }
    state = PersistentState.from_dict(data)
    assert state.migrated_from_v1 is False


def test_migrated_flag_excluded_from_equality() -> None:
    a = PersistentState()
    b = PersistentState()
    b.migrated_from_v1 = True
    assert a == b
