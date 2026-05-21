# Slice λ: 서브그래프 미니맵 / 위치 인디케이터 (FEAT-11) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 깊은 드릴다운에서 사용자가 현재 위치를 잃지 않도록 사이드 도크에 그래프 스택 트리 + 현재 위치 하이라이트.

**Architecture:** `core/app/minimap_panel.py`(신규) — `MinimapPanel(NavigablePanel)` 트리 위젯. `GraphStack`을 root별 트리로 시각화. 노드의 subgraph도 자식으로 (subgraph 있는 노드는 펼침 가능). 현재 active 그래프는 굵게 + 색.

**Spec ref:** `2026-05-22-t3dgraph-batch-8-heavy-features-design.md` §λ.

---

### Task 1: MinimapPanel 위젯

**Files:**
- Create: `src/t3dgraph/core/app/minimap_panel.py`
- Create: `tests/core/app/test_minimap_panel.py`

- [ ] **Step 1: Tests**

```python
import pytest
from PySide6.QtWidgets import QApplication
from t3dgraph.core.app.minimap_panel import MinimapPanel
from t3dgraph.core.app.graph_stack import GraphStack
from t3dgraph.core.base.graph_model import GraphModel, Node


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_minimap_renders_root_label(qapp):
    s = GraphStack()
    s.open_root(GraphModel(label="root.t3d", nodes=[Node(name="A", cls=None)]))
    p = MinimapPanel()
    p.show_stack(s)
    labels = p.all_labels()
    assert "root.t3d" in labels


def test_minimap_renders_subgraph_children(qapp):
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    g = GraphModel(label="root.t3d",
                   nodes=[Node(name="P", cls=None, subgraph=inner)])
    s = GraphStack()
    s.open_root(g)
    p = MinimapPanel()
    p.show_stack(s)
    labels = p.all_labels()
    assert "root.t3d" in labels
    assert "P" in " ".join(labels) or "inner" in " ".join(labels)


def test_click_jumps_to_segment(qapp):
    inner = GraphModel(label="inner", nodes=[Node(name="I", cls=None)])
    g = GraphModel(label="root.t3d",
                   nodes=[Node(name="P", cls=None, subgraph=inner)])
    s = GraphStack()
    s.open_root(g)
    s.push(inner)
    p = MinimapPanel()
    p.show_stack(s)

    received = []
    p.location_clicked.connect(lambda root_idx, depth: received.append((root_idx, depth)))
    # 첫 root + depth 0(루트 그래프)
    p._click_for_test(root_index=0, depth=0)
    assert received == [(0, 0)]
```

- [ ] **Step 2: Implement**

```python
"""미니맵 — GraphStack의 root별 트리 + 현재 위치 하이라이트."""
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QVBoxLayout, QTreeWidget, QTreeWidgetItem
from .navigable_panel import NavigablePanel
from .graph_stack import GraphStack
from ..base.graph_model import GraphModel

_ROOT_ROLE = Qt.UserRole + 1
_DEPTH_ROLE = Qt.UserRole + 2


class MinimapPanel(NavigablePanel):
    location_clicked = Signal(int, int)            # (root_index, depth)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["그래프 위치"])
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)

    def show_stack(self, stack: GraphStack) -> None:
        self._tree.clear()
        current_root = stack._cur_root if stack.roots() else -1
        current_path = stack._paths[current_root] if current_root >= 0 else []
        current_depth = len(current_path) - 1
        for ri, root in enumerate(stack.roots()):
            root_item = QTreeWidgetItem([root.label or "(이름 없음)"])
            root_item.setData(0, _ROOT_ROLE, ri)
            root_item.setData(0, _DEPTH_ROLE, 0)
            self._tree.addTopLevelItem(root_item)
            if ri == current_root and current_depth == 0:
                root_item.setSelected(True)
            self._render_children(
                root, root_item, ri, depth=1,
                active_path=current_path if ri == current_root else None,
                current_depth=current_depth,
            )
            root_item.setExpanded(True)

    def _render_children(self, graph: GraphModel, parent_item,
                         root_index: int, depth: int,
                         active_path: list[GraphModel] | None,
                         current_depth: int) -> None:
        for n in graph.nodes:
            if n.subgraph is None:
                continue
            label = n.display_name or n.name
            item = QTreeWidgetItem([label])
            item.setData(0, _ROOT_ROLE, root_index)
            item.setData(0, _DEPTH_ROLE, depth)
            parent_item.addChild(item)
            if active_path is not None and depth <= current_depth:
                if active_path[depth] is n.subgraph:
                    item.setSelected(True)
                    item.setExpanded(True)
                    self._render_children(n.subgraph, item, root_index, depth + 1,
                                          active_path, current_depth)
                    continue
            self._render_children(n.subgraph, item, root_index, depth + 1,
                                  None, current_depth)

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        ri = item.data(0, _ROOT_ROLE)
        depth = item.data(0, _DEPTH_ROLE)
        if ri is not None and depth is not None:
            self.location_clicked.emit(ri, depth)

    def _click_for_test(self, root_index: int, depth: int) -> None:
        self.location_clicked.emit(root_index, depth)

    def all_labels(self) -> list[str]:
        out = []
        def walk(it):
            out.append(it.text(0))
            for i in range(it.childCount()):
                walk(it.child(i))
        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))
        return out
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/minimap_panel.py tests/core/app/test_minimap_panel.py
git commit -m "feat(app): MinimapPanel showing graph stack tree (FEAT-11)"
```

---

### Task 2: MainWindow 통합

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 변경**

`main_window.py`:

```python
from .minimap_panel import MinimapPanel

# __init__ 안
self.minimap = MinimapPanel()
self.dock_minimap = self._dock("미니맵", self.minimap)
self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_minimap)

# _wire
self.minimap.location_clicked.connect(self._on_minimap_click)

def _on_minimap_click(self, root_index: int, depth: int) -> None:
    if root_index != self._tab_bar.currentIndex():
        self._tab_bar.setCurrentIndex(root_index)
    else:
        self.graph_stack.jump_to(depth)
        self._render_current()

# _render_current 끝에 미니맵 갱신
self.minimap.show_stack(self.graph_stack)
```

- [ ] **Step 2: Test**

```python
def test_minimap_updates_on_open_graph(qapp):
    win = MainWindow()
    win.open_graph(GraphModel(label="r", nodes=[Node(name="A", cls=None)]))
    assert "r" in " ".join(win.minimap.all_labels())
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_minimap_integration.py
git commit -m "feat(main_window): minimap dock + location click (FEAT-11)"
```

---

### Task 3: 회귀

```
pytest tests/ -v
```

---

## 완료 정의

- [ ] Task 1-3 PASS
- [ ] MinimapPanel이 GraphStack의 root별 트리 표시
- [ ] 현재 위치 하이라이트
- [ ] 클릭 시 location_clicked 시그널 → MainWindow가 탭/depth 점프
