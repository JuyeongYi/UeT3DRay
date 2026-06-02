# batch ⑮ u9 — 인라인 그래프 툴바 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 그래프 뷰 영역 위에 인라인 toolbar 신설 — 기존 상단 toolbar의 4 토글(수정된 핀만 / fan-in 강조 / 전체 펼침 / 전체 접기)과 레이아웃 액션(자동 정렬 / 위상 정렬)을 모두 그쪽으로 이동.

**배치**:
```
[ 탭바 ]
[ 브레드크럼 ]
[ 인라인 toolbar — 수정된 핀만 · fan-in · 전체 펼침/접기 · 자동 정렬 · 위상 정렬 ]
[ 그래프 뷰 ]
```

기존 QMainWindow top toolbar에 있던 4 액션 제거. 메뉴(보기) 항목들은 보조 진입점으로 유지.

**Pre-condition:** master 최신.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/main_window.py` | 수정 (toolbar 위치·구성 재배치) |
| `tests/app/test_inline_toolbar.py` | 신규 |

---

## Task 1: 인라인 toolbar 신설 + 기존 toolbar 제거

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_inline_toolbar.py`

- [ ] **Step 1: 테스트**

```python
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
```

- [ ] **Step 2: MainWindow 변경**

`src/t3dgraph/core/app/main_window.py`:

```python
def __init__(self):
    QMainWindow.__init__(self)
    ...
    self._inline_toolbar = QToolBar("그래프 액션")
    self._inline_toolbar.setMovable(False)
    self._inline_toolbar.setFloatable(False)

    central = QWidget()
    vlay = QVBoxLayout(central)
    vlay.setContentsMargins(0, 0, 0, 0)
    vlay.setSpacing(0)
    vlay.addWidget(self._tab_bar)
    vlay.addWidget(self.breadcrumb)
    vlay.addWidget(self._inline_toolbar)   # 신규 위치
    vlay.addWidget(self.view)
    self.setCentralWidget(central)
    ...
    # 기존 _build_view_mode_toolbar는 인라인으로 변경
    self._build_inline_toolbar()
    ...


def _build_inline_toolbar(self) -> None:
    from PySide6.QtGui import QAction
    self._view_mode_actions: dict[str, QAction] = {}

    toggles = (
        ("connected_only", "수정된 핀만",
         lambda v: self.current_view_state().set_connected_pins_only(v), False),
        ("fan_in_highlight", "fan-in 강조",
         lambda v: self.current_view_state().set_fan_in_highlight(v), True),
    )
    for mode_id, label, setter, in_place in toggles:
        action = QAction(label, self)
        action.setCheckable(True)
        action.toggled.connect(
            lambda checked, s=setter, ip=in_place:
                self._on_view_mode(s, checked, ip))
        self._inline_toolbar.addAction(action)
        self._view_mode_actions[mode_id] = action

    expand_all = QAction("전체 펼침", self)
    expand_all.triggered.connect(self._on_expand_all_pins)
    self._inline_toolbar.addAction(expand_all)
    self._view_mode_actions["expand_all"] = expand_all

    collapse_all = QAction("전체 접기", self)
    collapse_all.triggered.connect(self._on_collapse_all_pins)
    self._inline_toolbar.addAction(collapse_all)
    self._view_mode_actions["collapse_all"] = collapse_all

    self._inline_toolbar.addSeparator()

    auto_arrange = QAction("자동 정렬", self)
    auto_arrange.triggered.connect(self._on_auto_arrange)
    self._inline_toolbar.addAction(auto_arrange)

    hierarchical = QAction("위상 정렬", self)
    hierarchical.triggered.connect(self._on_hierarchical_arrange)
    self._inline_toolbar.addAction(hierarchical)
```

기존 `_build_view_mode_toolbar` 호출 제거(또는 `_build_inline_toolbar` 호출로 교체). 기존 `self.addToolBar("뷰 모드")` 호출 제거.

보기 메뉴의 "자동 정렬"·"위상 정렬" 항목은 보조 진입점으로 그대로 유지.

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_inline_toolbar.py -v`
Expected: 5 passed.

Run: `pytest tests -v`
Expected: 전체 통과. 기존 test가 `_view_mode_toolbar` 객체 참조하면 갱신(이름 그대로 두면 OK — 인라인 toolbar로 가리킴).

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

t3d 파일 열어 — 탭바 아래에 인라인 toolbar (수정된 핀만 · fan-in · 전체 펼침/접기 · 자동 정렬 · 위상 정렬). 메인 toolbar 영역에는 없음.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_inline_toolbar.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): inline graph toolbar — toggles + layout actions above view (u9)"
```

## 완료 후

그래프 액션이 사용자 시선 안에. 메인 toolbar 영역 비움 (필요 시 다른 글로벌 액션용으로 활용).
