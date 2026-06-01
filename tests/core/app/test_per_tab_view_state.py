"""F11 per-tab ViewState — 탭별 토글 상태 분리."""
from __future__ import annotations
from urllib.parse import quote

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.view_state import ViewState


def _graph(label: str, parent: str | None = None) -> GraphModel:
    return GraphModel(
        nodes=[Node(name=f"{label}_N", cls="T", pins=[])],
        label=label, parent_node=parent,
    )


def test_view_state_per_tab_isolation(qtbot) -> None:
    """탭1의 connected_only 토글이 탭2 ViewState에 영향 없음."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    # 탭2(B) 활성 상태에서 토글
    vs_b = w.current_view_state()
    vs_b.connected_pins_only = True
    # 탭1로 전환
    w._tab_bar.setCurrentIndex(0)
    vs_a = w.current_view_state()
    assert vs_a.connected_pins_only is False, "탭 간 ViewState 공유 — F11 회귀"


def test_view_state_persists_across_tab_switch(qtbot) -> None:
    """탭1 토글 → 탭2로 갔다 다시 탭1 복귀 시 토글 상태 유지."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    w._tab_bar.setCurrentIndex(0)
    w.current_view_state().connected_pins_only = True
    w._tab_bar.setCurrentIndex(1)
    w._tab_bar.setCurrentIndex(0)
    assert w.current_view_state().connected_pins_only is True


def test_view_state_cleared_on_tab_close(qtbot) -> None:
    """탭 닫으면 해당 ViewState 항목 제거 — 메모리 누수 방지."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    key_b = w._current_graph_key()
    assert key_b in w._view_states
    w._tab_bar.setCurrentIndex(1)
    w._on_tab_close(1)
    assert key_b not in w._view_states


def test_graph_key_escapes_slash_in_label(qtbot) -> None:
    """label에 '/' 들어가도 키 충돌 없음 — ν-B3."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A/with/slash"))
    w.open_graph(_graph("A"))
    keys = list(w._view_states.keys())
    assert len(keys) == 2 and len(set(keys)) == 2, (
        f"label에 '/' 들어가 키 충돌: {keys}"
    )


def test_view_mode_toggle_affects_current_tab_only(qtbot) -> None:
    """toolbar 액션이 활성 탭만 변경."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    w._tab_bar.setCurrentIndex(0)
    w.set_view_mode("connected_only", True)
    # 탭2로 전환
    w._tab_bar.setCurrentIndex(1)
    assert w.current_view_state().connected_pins_only is False, (
        "set_view_mode가 모든 탭에 적용됨 — F11 회귀"
    )
