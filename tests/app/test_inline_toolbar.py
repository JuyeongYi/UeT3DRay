"""u9 — 인라인 그래프 toolbar."""
from PySide6.QtWidgets import QToolBar, QToolButton

from t3dgraph.core.app.main_window import MainWindow


def test_inline_toolbar_exists(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    # 인라인 toolbar 객체 존재
    assert hasattr(w, "_inline_toolbar")
    assert isinstance(w._inline_toolbar, QToolBar)


def test_inline_toolbar_contains_toggles(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    texts = [a.text() for a in w._inline_toolbar.actions()]
    assert "수정된 핀만" in texts
    assert "fan-in 강조" in texts
    assert "전체 펼침" in texts
    assert "전체 접기" in texts


def test_inline_toolbar_contains_layout_actions(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    texts = [a.text() for a in w._inline_toolbar.actions()]
    assert "자동 정렬" in texts
    assert "위상 정렬" in texts


def test_top_toolbar_no_longer_has_toggles(qtbot) -> None:
    """기존 QMainWindow 상단 toolbar에는 4 토글 더 이상 없음."""
    w = MainWindow()
    qtbot.addWidget(w)
    # _view_mode_toolbar(상단 ToolBar)가 없거나 빈 상태 — 인라인으로 이동
    if hasattr(w, "_view_mode_toolbar"):
        texts = [a.text() for a in w._view_mode_toolbar.actions()]
        assert "수정된 핀만" not in texts


def test_inline_toolbar_position_above_view(qtbot) -> None:
    """central widget 안에 tab_bar/breadcrumb 다음·view 위에 위치."""
    w = MainWindow()
    qtbot.addWidget(w)
    central = w.centralWidget()
    layout = central.layout()
    # widget 순서 검사
    items = [layout.itemAt(i).widget() for i in range(layout.count())
             if layout.itemAt(i).widget() is not None]
    inline_idx = items.index(w._inline_toolbar)
    view_idx = items.index(w.view)
    assert inline_idx < view_idx
