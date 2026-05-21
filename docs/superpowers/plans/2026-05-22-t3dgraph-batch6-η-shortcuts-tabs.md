# Slice η: 단축키 + 멀티 탭 (FEAT-9 + FEAT-10) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 브레드크럼 위/뒤로 단축키(FEAT-9)와 멀티 파일 탭(FEAT-10) 추가.

**Architecture:** MainWindow에 `QShortcut` 등록 + `QTabBar` 추가. `GraphStack`에 `close_root(index)` + `forward()` 보강.

**Tech Stack:** PySide6, pytest-qt.

**Spec ref:** `docs/superpowers/specs/2026-05-22-t3dgraph-batch-6-ui-shortcuts-tabs-design.md`.

---

## 파일 구조

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/graph_stack.py` | `close_root(index)` 추가; 인덱스 조정 | 수정 |
| `src/t3dgraph/core/app/main_window.py` | shortcut 4종 + QTabBar | 수정 |
| `tests/core/app/test_graph_stack.py` | close_root | 수정 |
| `tests/core/app/test_main_window_shortcuts.py` | 단축키 → 동작 | 신규 |
| `tests/core/app/test_multi_file_tabs.py` | 탭 추가·전환·닫기 | 신규 |

---

### Task 1: `GraphStack.close_root`

**Files:**
- Modify: `src/t3dgraph/core/app/graph_stack.py`
- Modify: `tests/core/app/test_graph_stack.py`

- [ ] **Step 1: Tests**

```python
def test_close_root_removes_and_adjusts_index():
    s = GraphStack()
    s.open_root(GraphModel(label="A"))
    s.open_root(GraphModel(label="B"))
    s.open_root(GraphModel(label="C"))
    s.select_root(1)         # B 현재
    s.close_root(0)          # A 제거 → B는 인덱스 0이 됨
    assert [r.label for r in s.roots()] == ["B", "C"]
    assert s.current().label == "B"


def test_close_current_root_falls_back_to_neighbor():
    s = GraphStack()
    s.open_root(GraphModel(label="A"))
    s.open_root(GraphModel(label="B"))
    s.close_root(1)         # B 제거 → A 현재
    assert s.current().label == "A"


def test_close_last_root_makes_current_none():
    s = GraphStack()
    s.open_root(GraphModel(label="A"))
    s.close_root(0)
    assert s.current() is None
    assert s.roots() == []
```

- [ ] **Step 2: Implement**

```python
def close_root(self, index: int) -> None:
    if not (0 <= index < len(self._roots)):
        return
    del self._roots[index]
    del self._paths[index]
    if not self._roots:
        self._cur_root = -1
        return
    if self._cur_root >= len(self._roots):
        self._cur_root = len(self._roots) - 1
    elif index < self._cur_root:
        self._cur_root -= 1
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/graph_stack.py tests/core/app/test_graph_stack.py
git commit -m "feat(graph_stack): close_root with index adjust (FEAT-10 prep)"
```

---

### Task 2: 단축키 등록 (FEAT-9)

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/core/app/test_main_window_shortcuts.py`

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_alt_left_pops_subgraph(qapp):
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    g = GraphModel(label="root", nodes=[Node(name="P", cls=None, subgraph=inner)])
    win = MainWindow()
    win.open_graph(g)
    win._on_enter_subgraph("P")
    assert win.breadcrumb.segment_labels() == ["root", "P/graph"] or \
           len(win.breadcrumb.segment_labels()) == 2

    QTest.keyClick(win, Qt.Key_Left, Qt.AltModifier)
    assert len(win.breadcrumb.segment_labels()) == 1


def test_backspace_also_pops(qapp):
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    g = GraphModel(label="root", nodes=[Node(name="P", cls=None, subgraph=inner)])
    win = MainWindow()
    win.open_graph(g)
    win._on_enter_subgraph("P")
    QTest.keyClick(win, Qt.Key_Backspace)
    assert len(win.breadcrumb.segment_labels()) == 1
```

- [ ] **Step 2: Implement**

`main_window.py`에 `_build_shortcuts` 추가, `__init__` 끝에서 호출:

```python
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt


def _build_shortcuts(self) -> None:
    QShortcut(QKeySequence("Alt+Left"), self,
              activated=self._on_shortcut_back)
    QShortcut(QKeySequence(Qt.Key_Backspace), self,
              activated=self._on_shortcut_back)
    QShortcut(QKeySequence("Alt+Up"), self,
              activated=self._on_shortcut_up)

def _on_shortcut_back(self) -> None:
    self.graph_stack.pop()
    self._render_current()

def _on_shortcut_up(self) -> None:
    # 한 단계 위 — segments 길이 - 2
    segs = self.graph_stack.segments()
    if len(segs) >= 2:
        self.graph_stack.jump_to(len(segs) - 2)
        self._render_current()
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window_shortcuts.py
git commit -m "feat(main_window): shortcuts Alt+Left/Backspace/Alt+Up (FEAT-9)"
```

---

### Task 3: 멀티 파일 탭 (FEAT-10)

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/core/app/test_multi_file_tabs.py`

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtWidgets import QApplication, QTabBar
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_open_two_graphs_shows_two_tabs(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label="a.t3d", nodes=[Node(name="A", cls=None)]))
    win.open_graph(GraphModel(label="b.t3d", nodes=[Node(name="B", cls=None)]))
    assert win._tab_bar.count() == 2
    assert win._tab_bar.tabText(0) == "a.t3d"
    assert win._tab_bar.tabText(1) == "b.t3d"


def test_tab_click_switches_graph(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label="a.t3d", nodes=[Node(name="A", cls=None)]))
    win.open_graph(GraphModel(label="b.t3d", nodes=[Node(name="B", cls=None)]))
    assert win.scene.node_item("B") is not None
    win._tab_bar.setCurrentIndex(0)
    assert win.scene.node_item("A") is not None


def test_close_tab_removes_root(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label="a.t3d", nodes=[Node(name="A", cls=None)]))
    win.open_graph(GraphModel(label="b.t3d", nodes=[Node(name="B", cls=None)]))
    win._on_tab_close(0)
    assert win._tab_bar.count() == 1
    assert win.scene.node_item("B") is not None
```

- [ ] **Step 2: Implement**

`main_window.py`:

```python
from PySide6.QtWidgets import QTabBar

# __init__ — central layout 안에 추가
self._tab_bar = QTabBar()
self._tab_bar.setTabsClosable(True)
self._tab_bar.setExpanding(False)
self._tab_bar.currentChanged.connect(self._on_tab_changed)
self._tab_bar.tabCloseRequested.connect(self._on_tab_close)
vlay.insertWidget(0, self._tab_bar)   # 브레드크럼 위

# open_graph 보강
def open_graph(self, graph: GraphModel, *, label: str | None = None) -> None:
    if label and not graph.label:
        graph.label = label
    self.graph_stack.open_root(graph)
    self._tab_bar.addTab(graph.label or "(이름 없음)")
    self._tab_bar.setCurrentIndex(self._tab_bar.count() - 1)
    self._render_current()


def _on_tab_changed(self, index: int) -> None:
    if index < 0 or index >= len(self.graph_stack.roots()):
        return
    self.graph_stack.select_root(index)
    self._render_current()


def _on_tab_close(self, index: int) -> None:
    self._tab_bar.blockSignals(True)
    self._tab_bar.removeTab(index)
    self._tab_bar.blockSignals(False)
    self.graph_stack.close_root(index)
    if self.graph_stack.current() is None:
        self.scene.clear()
        self.breadcrumb.set_segments([])
    else:
        self._render_current()
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_multi_file_tabs.py
git commit -m "feat(main_window): multi-file QTabBar (FEAT-10)"
```

---

### Task 4: 회귀

```
pytest tests/ -v
```

---

## 완료 정의

- [ ] Task 1-4 PASS
- [ ] Alt+←, Backspace, Alt+↑ 단축키 동작
- [ ] 멀티 파일 탭 — 추가/전환/닫기
- [ ] 닫힌 탭의 GraphModel은 GraphStack 제거 (참조 해제)
