# batch ⑮ u2 — 미니맵 트리 항목 직접 진입 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 미니맵 트리에서 서브그래프/함수 항목 클릭 시 해당 그래프로 즉시 진입. 현재 path 외 형제 subgraph도 진입 가능.

**현재 동작 (문제)**:
- `MinimapPanel.location_clicked(root_index, depth)` — depth만 emit
- `MainWindow._on_minimap_click`이 `graph_stack.jump_to(depth)` — 현재 path의 depth로만 이동
- 다른 path의 subgraph 클릭 시 잘못된 그래프로 이동 (또는 무반응)

**수정**:
- 트리 항목에 GraphModel 참조 저장
- 시그널이 GraphModel 객체 자체를 emit (또는 navigation path)
- MainWindow가 해당 subgraph로 graph_stack path 직접 설정

**Pre-condition:** master 최신.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/minimap_panel.py` | 수정 (`_SUBGRAPH_ROLE` 저장, 시그널 시그니처) |
| `src/t3dgraph/core/app/graph_stack.py` | 수정 (`jump_to_subgraph(target: GraphModel)` 메서드) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`_on_minimap_click` 갱신) |
| `tests/app/test_minimap_deep_nav.py` | 신규 |

---

## Task 1: GraphStack에 jump_to_subgraph

**Files:**
- Modify: `src/t3dgraph/core/app/graph_stack.py`
- Create: `tests/app/test_graph_stack_jump_subgraph.py`

- [ ] **Step 1: 테스트**

```python
"""u2 — GraphStack.jump_to_subgraph로 임의 subgraph 활성화."""
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.graph_stack import GraphStack


def test_jump_to_subgraph_at_root() -> None:
    root = GraphModel(label="root")
    stack = GraphStack()
    stack.open_root(root)
    ok = stack.jump_to_subgraph(root)
    assert ok is True
    assert stack.current() is root


def test_jump_to_nested_subgraph() -> None:
    leaf = GraphModel(label="leaf")
    mid = GraphModel(label="mid",
                     nodes=[Node(name="LeafContainer", cls="X", subgraph=leaf)])
    root = GraphModel(label="root",
                      nodes=[Node(name="MidContainer", cls="X", subgraph=mid)])
    stack = GraphStack()
    stack.open_root(root)
    assert stack.jump_to_subgraph(leaf) is True
    assert stack.current() is leaf
    # 경로 확인
    segments = stack.segments()
    assert len(segments) == 3  # root → mid → leaf


def test_jump_to_extra_subgraph() -> None:
    extra = GraphModel(label="extra")
    main = GraphModel(label="main")
    container = Node(name="C", cls="X", subgraph=main, extra_subgraphs=[extra])
    root = GraphModel(label="root", nodes=[container])
    stack = GraphStack()
    stack.open_root(root)
    assert stack.jump_to_subgraph(extra) is True
    assert stack.current() is extra


def test_jump_to_unknown_returns_false() -> None:
    root = GraphModel(label="root")
    stranger = GraphModel(label="stranger")
    stack = GraphStack()
    stack.open_root(root)
    assert stack.jump_to_subgraph(stranger) is False
    assert stack.current() is root   # 변화 없음


def test_jump_to_sibling_subgraph() -> None:
    """다른 path의 형제 subgraph로 이동."""
    leaf_a = GraphModel(label="A")
    leaf_b = GraphModel(label="B")
    root = GraphModel(
        label="root",
        nodes=[
            Node(name="ContainerA", cls="X", subgraph=leaf_a),
            Node(name="ContainerB", cls="X", subgraph=leaf_b),
        ],
    )
    stack = GraphStack()
    stack.open_root(root)
    # leaf_a로 이동 후 leaf_b로 직접 이동
    assert stack.jump_to_subgraph(leaf_a) is True
    assert stack.current() is leaf_a
    assert stack.jump_to_subgraph(leaf_b) is True
    assert stack.current() is leaf_b
```

- [ ] **Step 2: 구현**

`src/t3dgraph/core/app/graph_stack.py`에 메서드 추가:

```python
def jump_to_subgraph(self, target: GraphModel) -> bool:
    """현재 root 트리에서 target subgraph 찾아 활성 path로 설정.

    반환: 찾으면 True (current path 갱신), 못 찾으면 False (변화 없음).
    """
    if not self.roots() or self._cur_root < 0:
        return False
    root = self.roots()[self._cur_root]
    path = self._find_path_to(root, target)
    if path is None:
        return False
    self._paths[self._cur_root] = path
    return True

def _find_path_to(self, graph: GraphModel,
                  target: GraphModel,
                  visited: set | None = None) -> list[GraphModel] | None:
    """DFS — graph로부터 target까지의 경로(graph, ..., target).
    
    cycle 방지를 위해 visited 추적. graph is target이면 [graph]."""
    if visited is None:
        visited = set()
    if id(graph) in visited:
        return None
    visited.add(id(graph))
    if graph is target:
        return [graph]
    for n in graph.nodes:
        for sub in self._iter_subgraphs(n):
            found = self._find_path_to(sub, target, visited)
            if found is not None:
                return [graph] + found
    return None

@staticmethod
def _iter_subgraphs(node):
    if node.subgraph is not None:
        yield node.subgraph
    for extra in node.extra_subgraphs:
        yield extra
```

- [ ] **Step 3: 실행 — 통과**

Run: `pytest tests/app/test_graph_stack_jump_subgraph.py -v`
Expected: 5 passed.

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_graph_stack_jump_subgraph.py src/t3dgraph/core/app/graph_stack.py
git commit -m "feat(app): GraphStack.jump_to_subgraph for arbitrary subgraph activation (u2 prep)"
```

---

## Task 2: 미니맵 트리에 subgraph 참조 저장 + MainWindow 연결

**Files:**
- Modify: `src/t3dgraph/core/app/minimap_panel.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_minimap_deep_nav.py`

- [ ] **Step 1: MinimapPanel — `_SUBGRAPH_ROLE` 저장**

`src/t3dgraph/core/app/minimap_panel.py`:

```python
_ROOT_ROLE = Qt.UserRole + 1
_DEPTH_ROLE = Qt.UserRole + 2
_SUBGRAPH_ROLE = Qt.UserRole + 3   # 신규 — GraphModel 객체


class MinimapPanel(NavigablePanel):
    location_clicked = Signal(int, object)   # (root_index, GraphModel)

    def show_stack(self, stack: GraphStack) -> None:
        self._tree.clear()
        current_root = stack._cur_root if stack.roots() else -1
        current_path = stack._paths[current_root] if current_root >= 0 else []
        current_depth = len(current_path) - 1
        for ri, root in enumerate(stack.roots()):
            root_item = QTreeWidgetItem([root.label or '(이름 없음)'])
            root_item.setData(0, _ROOT_ROLE, ri)
            root_item.setData(0, _DEPTH_ROLE, 0)
            root_item.setData(0, _SUBGRAPH_ROLE, root)   # root 자신
            self._tree.addTopLevelItem(root_item)
            if ri == current_root and current_depth == 0:
                root_item.setSelected(True)
            self._render_children(
                root, root_item, ri, depth=1,
                active_path=current_path if ri == current_root else None,
                current_depth=current_depth,
            )
            root_item.setExpanded(True)

    def _render_children(self, graph, parent_item, root_index, depth,
                         active_path, current_depth):
        for n in graph.nodes:
            subs = []
            if n.subgraph is not None:
                subs.append(n.subgraph)
            subs.extend(n.extra_subgraphs)
            for sub in subs:
                label = n.display_name or n.name
                if len(subs) > 1:
                    label = f"{label} ({sub.label or 'graph'})"
                item = QTreeWidgetItem([label])
                item.setData(0, _ROOT_ROLE, root_index)
                item.setData(0, _DEPTH_ROLE, depth)
                item.setData(0, _SUBGRAPH_ROLE, sub)   # subgraph 객체
                parent_item.addChild(item)
                if active_path is not None and depth <= current_depth:
                    if active_path[depth] is sub:
                        item.setSelected(True)
                        item.setExpanded(True)
                        self._render_children(sub, item, root_index, depth + 1,
                                              active_path, current_depth)
                        continue
                self._render_children(sub, item, root_index, depth + 1,
                                      None, current_depth)

    def _on_activated(self, item, _col):
        ri = item.data(0, _ROOT_ROLE)
        sub = item.data(0, _SUBGRAPH_ROLE)
        if ri is not None and sub is not None:
            self.location_clicked.emit(ri, sub)

    def _click_for_test(self, root_index: int, subgraph) -> None:
        self.location_clicked.emit(root_index, subgraph)
```

- [ ] **Step 2: MainWindow `_on_minimap_click` 갱신**

`src/t3dgraph/core/app/main_window.py`:

```python
def _on_minimap_click(self, root_index: int, subgraph) -> None:
    if root_index != self._tab_bar.currentIndex():
        self._tab_bar.setCurrentIndex(root_index)
    # 현재 root에서 target subgraph로 jump
    if self.graph_stack.jump_to_subgraph(subgraph):
        self._render_current()
```

- [ ] **Step 3: 통합 테스트**

`tests/app/test_minimap_deep_nav.py`:

```python
"""u2 통합 — 미니맵에서 임의 subgraph 진입."""
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow


def test_minimap_click_enters_subgraph(qtbot) -> None:
    leaf = GraphModel(label="leaf")
    root = GraphModel(
        label="root",
        nodes=[Node(name="Container", cls="X", subgraph=leaf)],
    )
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(root)
    # 미니맵에 leaf 항목 클릭
    w.minimap._click_for_test(0, leaf)
    assert w.graph_stack.current() is leaf


def test_minimap_click_sibling_subgraph(qtbot) -> None:
    """현재 path 아닌 형제 subgraph 클릭."""
    leaf_a = GraphModel(label="A")
    leaf_b = GraphModel(label="B")
    root = GraphModel(
        label="root",
        nodes=[
            Node(name="CA", cls="X", subgraph=leaf_a),
            Node(name="CB", cls="X", subgraph=leaf_b),
        ],
    )
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(root)
    w.minimap._click_for_test(0, leaf_a)
    assert w.graph_stack.current() is leaf_a
    # leaf_b로 직접 클릭 (다른 path)
    w.minimap._click_for_test(0, leaf_b)
    assert w.graph_stack.current() is leaf_b
```

- [ ] **Step 4: 실행 + 회귀**

Run: `pytest tests -v`
Expected: 전체 통과. 기존 미니맵 테스트가 `(int, int)` 시그니처 가정 시 갱신 필요.

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 폴더 열어 그래프 안 서브그래프/함수 노드 있는 케이스에서 미니맵 트리 항목 클릭 → 즉시 그 그래프 진입.

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_minimap_deep_nav.py src/t3dgraph/core/app/minimap_panel.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): minimap click navigates to subgraph directly (u2)"
```

## 완료 후

미니맵 진입 정상화. 이전 batch ⑬ deferred 항목 해소.
