"""ω — MainWindow 영속 상태 통합 (열기·변경·닫기·재오픈)."""
from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF

from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController


@pytest.fixture
def synth_t3d_file(tmp_path: Path) -> str:
    src = (
        'Begin Object Name="N1" Class=/Script/RigVMDeveloper.RigVMUnitNode\n'
        'End Object\n'
        'Begin Object Name="N2" Class=/Script/RigVMDeveloper.RigVMUnitNode\n'
        'End Object\n'
    )
    f = tmp_path / "sample.t3d.txt"
    f.write_text(src, encoding="utf-8")
    return str(f)


@pytest.fixture(autouse=True)
def _state_dir_isolation(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: state_dir)


def _make_window(qtbot) -> MainWindow:
    w = MainWindow()
    qtbot.addWidget(w)
    ctrl = AppController(w)
    w.set_open_handler(ctrl.open_file)
    return w


def test_view_mode_persists_across_reopen(qtbot, synth_t3d_file) -> None:
    """connected_only 토글 → 닫기 → 재오픈 → 토글 ON 복원."""
    w1 = _make_window(qtbot)
    w1.open_path(synth_t3d_file)
    w1.set_view_mode("connected_only", True)
    w1._save_persistent_state()   # 디바운스 우회
    w1.close()

    w2 = _make_window(qtbot)
    w2.open_path(synth_t3d_file)
    assert w2.current_view_state().connected_pins_only is True
    assert w2._view_mode_actions["connected_only"].isChecked() is True


def test_node_position_persists_across_reopen(qtbot, synth_t3d_file) -> None:
    """노드 드래그 위치 → 재오픈 → 같은 위치."""
    w1 = _make_window(qtbot)
    w1.open_path(synth_t3d_file)
    key = w1._current_graph_key()
    w1.layout_overrides.set(key, "N1", 123.0, 45.0)
    w1._save_persistent_state()
    w1.close()

    w2 = _make_window(qtbot)
    w2.open_path(synth_t3d_file)
    key2 = w2._current_graph_key()
    pos = w2.layout_overrides.get(key2, "N1")
    assert pos == (123.0, 45.0)


def test_expanded_pin_paths_persist(qtbot, synth_t3d_file) -> None:
    """expanded set 라운드트립."""
    w1 = _make_window(qtbot)
    w1.open_path(synth_t3d_file)
    w1.current_view_state().expanded_pin_paths.add("N1.SomePin")
    w1._save_persistent_state()
    w1.close()

    w2 = _make_window(qtbot)
    w2.open_path(synth_t3d_file)
    assert "N1.SomePin" in w2.current_view_state().expanded_pin_paths


def test_no_state_file_yields_empty_defaults(qtbot, synth_t3d_file) -> None:
    """저장된 state 없으면 디폴트 — 기존 흐름."""
    w = _make_window(qtbot)
    w.open_path(synth_t3d_file)
    vs = w.current_view_state()
    assert vs.connected_pins_only is False
    assert vs.expanded_pin_paths == set()


def test_multi_subgraph_state_persists(qtbot, synth_t3d_file) -> None:
    """두 graph_key에 다른 토글 → 모두 복원 — h1 ω-A1."""
    from t3dgraph.core.app.view_state import ViewState
    w1 = _make_window(qtbot)
    w1.open_path(synth_t3d_file)
    w1._view_states["keyA/"] = ViewState(connected_pins_only=True)
    w1._view_states["keyB/Sub"] = ViewState(fan_in_highlight=True)
    w1._save_persistent_state()
    w1.close()

    w2 = _make_window(qtbot)
    w2.open_path(synth_t3d_file)
    assert w2._view_states.get("keyA/") is not None
    assert w2._view_states["keyA/"].connected_pins_only is True
    assert w2._view_states.get("keyB/Sub") is not None
    assert w2._view_states["keyB/Sub"].fan_in_highlight is True
