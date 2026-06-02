# batch ⑬ g12 — 다중 선택 / 동시 이동 (F33) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 빈 영역 드래그로 사각 선택(rubber band) → 다중 노드 동시 이동. 인스펙터는 2+ 선택 시 "다중 선택" 표시.

**Pre-condition:** master `6c7b2b3` 이상. 다른 슬라이스와 파일 충돌 적음 (graph_view·main_window·inspector_panel).

---

## Task 1: RubberBand 선택 + 다중 이동 + 인스펙터 표시

**Files:**
- Modify: `src/t3dgraph/core/app/graph_view.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `src/t3dgraph/core/app/inspector_panel.py`
- Create: `tests/app/test_multi_select.py`

- [ ] **Step 1: 테스트**

```python
"""g12 (F33) — 다중 선택 + 인스펙터 표시."""
from PySide6.QtWidgets import QGraphicsView

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow


def test_graph_view_rubber_band_mode(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.view.dragMode() == QGraphicsView.RubberBandDrag


def test_inspector_shows_multi_selection_label(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(nodes=[
        Node(name="A", cls="T"),
        Node(name="B", cls="T"),
        Node(name="C", cls="T"),
    ])
    w.open_graph(g)
    # 두 NodeItem 선택
    a = w.scene.node_item("A")
    b = w.scene.node_item("B")
    a.setSelected(True)
    b.setSelected(True)
    w._on_scene_selection()
    # InspectorPanel 타이틀이 "다중 선택"
    assert "다중 선택" in w.inspector._title.text()
    assert "2" in w.inspector._title.text()


def test_inspector_single_selection_unchanged(qtbot) -> None:
    """1개 선택은 기존 show_node 동작."""
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(nodes=[Node(name="OnlyOne", cls="T")])
    w.open_graph(g)
    item = w.scene.node_item("OnlyOne")
    item.setSelected(True)
    w._on_scene_selection()
    assert "다중 선택" not in w.inspector._title.text()
    assert "OnlyOne" in w.inspector._title.text()
```

- [ ] **Step 2: GraphView rubber band 모드**

`src/t3dgraph/core/app/graph_view.py`의 GraphView `__init__`에 추가:

```python
from PySide6.QtWidgets import QGraphicsView

class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()
        ...
        self.setDragMode(QGraphicsView.RubberBandDrag)
```

(기존 모드가 있으면 RubberBandDrag로 변경. ScrollHandDrag 같은 모드가 필요하면 Modifier로 전환 가능 — 본 슬라이스에선 단순 RubberBand만.)

- [ ] **Step 3: InspectorPanel 다중 선택 표시**

`src/t3dgraph/core/app/inspector_panel.py`:

```python
def show_multi_selection(self, count: int) -> None:
    """N개 선택 시 타이틀만 — tree clear."""
    self._tree.clear()
    self._items = {}
    self._set_title(f"(다중 선택 — {count}개 노드)")
```

(`_set_title`이 elide 적용해 길이 한정.)

- [ ] **Step 4: MainWindow 선택 핸들러 분기**

`_on_scene_selection`:

```python
def _on_scene_selection(self) -> None:
    selected = [n for n in self.scene._nodes.values() if n.isSelected()]
    if len(selected) > 1:
        names = [item.node.name for item in selected]
        self.view_state.select(None)
        self.inspector.show_multi_selection(len(selected))
        # analysis 패널은 마지막 선택만 강조(혹은 클리어)
        last = selected[-1].node.name
        self.analysis_panel.highlight_node(last)
        self.exec_order_panel.highlight_node(last)
        self.data_flow_panel.highlight_node(last)
        return
    # 1개 또는 0개 — 기존 동작
    name = selected[0].node.name if selected else None
    self.view_state.select(name)
    if self.graph is not None:
        node = self.graph.node_by_name(name) if name else None
        self.inspector.show_node(node, self.graph)
    self.analysis_panel.highlight_node(name)
    self.exec_order_panel.highlight_node(name)
    self.data_flow_panel.highlight_node(name)
```

- [ ] **Step 5: 다중 이동 — Qt 자동 동기**

`ItemIsMovable` + `ItemIsSelectable`이 이미 NodeItem에 설정돼 있어 Qt가 자동으로 selected items를 함께 이동. 추가 코드 불필요. 단 `itemChange`는 각 NodeItem이 개별 fire하므로 `position_changed` 신호 다수 발사 — `_on_node_moved`가 각 호출에서 layout_overrides 갱신. 정상.

- [ ] **Step 6: 실행 + 회귀**

Run: `pytest tests/app/test_multi_select.py -v`
Expected: 3 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 7: 수동 검증**

```bash
uv run t3dgraph-gui
```

- 빈 영역 드래그 → 사각 선택 박스 → 노드 다수 선택
- 그 중 하나 드래그 → 모두 함께 이동
- 인스펙터에 "(다중 선택 — N개 노드)"

- [ ] **Step 8: 커밋**

```bash
git add tests/app/test_multi_select.py src/t3dgraph/core/app/graph_view.py src/t3dgraph/core/app/main_window.py src/t3dgraph/core/app/inspector_panel.py
git commit -m "feat(app): rubber-band multi-select + multi-move + inspector multi label (F33)"
```

## 완료 후

F33 해소. 사용자가 빈 영역 드래그로 다중 선택, 함께 이동 가능. 인스펙터 다중 선택 표시.
