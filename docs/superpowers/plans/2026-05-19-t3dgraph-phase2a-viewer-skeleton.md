# t3dgraph Phase 2a — 뷰어 골격 & 그래프 렌더링 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `.t3d` 파일을 열어 RigVM 노드 그래프를 PySide6 `QGraphicsView`에 — 데이터의 `Position` 좌표대로 — 표시하는 동작하는 최소 뷰어를 만든다.

**Architecture:** spec §4·§5.6·§7. `core/app/`에 그래프 종류 무관 뷰어 기반(아이템·씬·뷰·윈도우·컨트롤러)을 두고, Model 레이어(Phase 1/1.5 완성)를 그대로 소비한다. 플러그인별 view/controller 오버라이드 seam(`plugin.view_ref`/`controller_ref`)은 `app.py`가 fallback과 함께 처리한다. Phase 2a는 base 사용.

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt. Model 레이어는 여전히 stdlib only — Qt는 `core/app/` 와 플러그인 view/controller에만.

**선행 조건:** Phase 1.5 완료(master, 63 테스트 통과). 리포: `C:/Users/jylee/source/UeT3DRay`.

**Spec:** `docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md`

**범위 밖 (Phase 2b):** 노드 타입 필터, 속성 인스펙터(연결됨/변경됨), 분석 도크(수렴점·실행 순서), 뷰 모드(연결된 핀만·깊이·fan-in 강조). Phase 2a는 도크를 빈 placeholder로만 둔다.

---

## File Structure (Phase 2a)

| 파일 | 책임 |
| --- | --- |
| `pyproject.toml` | `[gui]` extra(PySide6), dev += pytest-qt, gui 스크립트 entry |
| `src/t3dgraph/core/app/__init__.py` | 패키지 |
| `src/t3dgraph/core/app/contracts.py` | `AbstractGraphView`/`AbstractGraphController` ABC |
| `src/t3dgraph/core/app/items.py` | `NodeItem`/`PinItem`/`LinkItem` (QGraphicsItem) |
| `src/t3dgraph/core/app/scene.py` | `GraphScene` — GraphModel → 아이템 (Position 좌표) |
| `src/t3dgraph/core/app/graph_view.py` | `GraphView` — QGraphicsView pan/zoom |
| `src/t3dgraph/core/app/main_window.py` | `MainWindow` — 메뉴·도크 레이아웃·중앙 GraphView |
| `src/t3dgraph/core/app/controller.py` | `AppController` — 파일 열기 → Model 파이프라인 → 씬 |
| `src/t3dgraph/core/app/app.py` | `main()` — QApplication, M/V/C 조립, 플러그인 view/controller fallback |
| `tests/core/app/...` | pytest-qt 단위·스모크 테스트 |

---

## Task 1: 의존성 & `core/app/` 스캐폴딩

**Files:**
- Modify: `pyproject.toml`
- Create: `src/t3dgraph/core/app/__init__.py`
- Create: `tests/core/app/__init__.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: `pyproject.toml` 갱신**

`[project.optional-dependencies]` 와 `[project.scripts]` 를 다음으로 교체:

```toml
[project.optional-dependencies]
gui = ["PySide6>=6.6"]
dev = ["pytest>=8", "pytest-qt>=4.4", "PySide6>=6.6"]

[project.scripts]
t3dgraph = "t3dgraph.cli:main"
t3dgraph-gui = "t3dgraph.core.app.app:main"
```

- [ ] **Step 2: 패키지 파일 생성**

`src/t3dgraph/core/app/__init__.py` — 빈 파일.
`tests/core/app/__init__.py` — 빈 파일.

- [ ] **Step 3: `tests/conftest.py` 에 headless Qt 설정 추가**

기존 `tests/conftest.py` 맨 위(다른 import보다 먼저)에 추가:

```python
import os
# pytest-qt 테스트를 디스플레이 없이 실행
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

- [ ] **Step 4: 설치 및 확인**

Run:
```bash
pip install -e ".[dev]"
python -c "import PySide6; from PySide6.QtWidgets import QApplication; print('PySide6 OK')"
python -m pytest -q
```
Expected: `PySide6 OK`, 기존 63개 테스트 전부 PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/t3dgraph/core/app/__init__.py tests/core/app/__init__.py tests/conftest.py
git commit -m "chore(app): add PySide6/pytest-qt deps and core/app scaffolding"
```

---

## Task 2: 추상 계약 — `core/app/contracts.py`

플러그인이 view/controller를 오버라이드할 수 있는 seam. Phase 2a는 base가 이를 구현, RigVM은 base 사용.

**Files:**
- Create: `src/t3dgraph/core/app/contracts.py`
- Test: `tests/core/app/test_contracts.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_contracts.py
import pytest
from t3dgraph.core.app.contracts import AbstractGraphView, AbstractGraphController


def test_view_is_abstract():
    with pytest.raises(TypeError):
        AbstractGraphView()


def test_controller_is_abstract():
    with pytest.raises(TypeError):
        AbstractGraphController()


def test_concrete_subclasses_instantiable():
    class V(AbstractGraphView):
        def show_graph(self, graph): return None

    class C(AbstractGraphController):
        def open_file(self, path): return None

    assert V().show_graph(None) is None
    assert C().open_file("x") is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_contracts.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/contracts.py
"""뷰어 view/controller 추상 계약 — 플러그인 오버라이드 seam."""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..base.graph_model import GraphModel


class AbstractGraphView(ABC):
    @abstractmethod
    def show_graph(self, graph: GraphModel) -> None:
        """주어진 GraphModel을 화면에 렌더링한다."""
        raise NotImplementedError


class AbstractGraphController(ABC):
    @abstractmethod
    def open_file(self, path: str) -> None:
        """.t3d 파일을 열어 파싱·해석한 뒤 view에 렌더링을 지시한다."""
        raise NotImplementedError
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_contracts.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/contracts.py tests/core/app/test_contracts.py
git commit -m "feat(app): AbstractGraphView/Controller contracts"
```

---

## Task 3: 그래프 아이템 — `core/app/items.py`

`NodeItem`(헤더 + 핀 행), `PinItem`(핀 행 마커), `LinkItem`(핀 앵커 간 선). 노드 크기는 핀 수로 결정. 핀 경로 `"Node.Pin"` / `"Node.Pin.Sub"` 의 두 번째 세그먼트가 핀 행.

**Files:**
- Create: `src/t3dgraph/core/app/items.py`
- Test: `tests/core/app/test_items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_items.py
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem, LinkItem, NODE_WIDTH, ROW_HEIGHT, HEADER_HEIGHT


def _node():
    return Node(
        name="N", cls="X", position=(100.0, 50.0),
        pins=[
            Pin(name="In", cpp_type="exec", direction="Input"),
            Pin(name="Out", cpp_type="exec", direction="Output"),
        ],
    )


def test_node_item_positioned_by_data(qtbot):
    item = NodeItem(_node())
    assert item.pos().x() == 100.0
    assert item.pos().y() == 50.0


def test_node_item_height_scales_with_pins(qtbot):
    item = NodeItem(_node())
    expected = HEADER_HEIGHT + 2 * ROW_HEIGHT
    assert item.rect().height() == expected
    assert item.rect().width() == NODE_WIDTH


def test_node_item_pin_anchor_input_on_left(qtbot):
    item = NodeItem(_node())
    anchor = item.pin_anchor("In", "Input")          # 씬 좌표
    assert anchor.x() == 100.0                        # 노드 좌측 변
    assert anchor.y() == 50.0 + HEADER_HEIGHT + ROW_HEIGHT / 2


def test_node_item_pin_anchor_output_on_right(qtbot):
    item = NodeItem(_node())
    anchor = item.pin_anchor("Out", "Output")
    assert anchor.x() == 100.0 + NODE_WIDTH           # 노드 우측 변


def test_node_item_unknown_pin_anchor_falls_back_to_center(qtbot):
    item = NodeItem(_node())
    anchor = item.pin_anchor("Missing", "Input")
    assert anchor.x() == 100.0 + NODE_WIDTH / 2       # 폴백: 노드 중앙
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_items.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/items.py
"""QGraphicsItem 기반 노드/핀/링크 렌더링 요소."""
from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsLineItem,
)
from ..base.graph_model import Node, Pin

NODE_WIDTH = 200.0
ROW_HEIGHT = 20.0
HEADER_HEIGHT = 26.0
PIN_RADIUS = 4.0


class NodeItem(QGraphicsRectItem):
    """노드 1개 — 헤더 텍스트 + 핀 행 목록. 데이터 Position에 배치."""

    def __init__(self, node: Node):
        self.node = node
        pin_count = max(len(node.pins), 1)
        height = HEADER_HEIGHT + pin_count * ROW_HEIGHT
        super().__init__(QRectF(0, 0, NODE_WIDTH, height))
        x, y = node.position if node.position else (0.0, 0.0)
        self.setPos(x, y)
        self.setPen(QPen(QColor(40, 40, 40)))
        self.setBrush(QBrush(QColor(70, 70, 80) if not node.is_generic
                              else QColor(90, 60, 60)))
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

        title = QGraphicsSimpleTextItem(node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)

        # 핀 행 — 입력은 좌측, 출력은 우측 마커
        self._rows: dict[str, float] = {}             # pin_name → 행 중심 y(로컬)
        for i, pin in enumerate(node.pins):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[pin.name] = cy
            is_input = (pin.direction or "").lower() != "output"
            mx = 0.0 if is_input else NODE_WIDTH
            dot = QGraphicsEllipseItem(
                mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
            dot.setBrush(QBrush(QColor(200, 200, 120)))
            dot.setPen(QPen(Qt.NoPen))
            label = QGraphicsSimpleTextItem(pin.name, self)
            label.setBrush(QBrush(QColor(210, 210, 210)))
            lx = 8 if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
            label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)

    def pin_anchor(self, pin_name: str, direction: str) -> QPointF:
        """핀의 씬 좌표 앵커. 알 수 없는 핀은 노드 중앙으로 폴백."""
        cy = self._rows.get(pin_name)
        if cy is None:
            return self.mapToScene(QPointF(NODE_WIDTH / 2, self.rect().height() / 2))
        lx = NODE_WIDTH if (direction or "").lower() == "output" else 0.0
        return self.mapToScene(QPointF(lx, cy))


class LinkItem(QGraphicsLineItem):
    """두 핀 앵커를 잇는 선."""

    def __init__(self, p1: QPointF, p2: QPointF):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y())
        self.setPen(QPen(QColor(170, 170, 170), 1.5))
        self.setZValue(-1)                            # 노드 뒤에
```

> 주: `PinItem`은 Phase 2a에서 `NodeItem` 내부의 `QGraphicsEllipseItem`/`QGraphicsSimpleTextItem` 자식으로 충분하다. 독립 선택 가능한 `PinItem` 클래스는 Phase 2b(인스펙터 연동) 때 도입한다 — YAGNI.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_items.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/items.py tests/core/app/test_items.py
git commit -m "feat(app): NodeItem/LinkItem graphics items"
```

---

## Task 4: 씬 — `core/app/scene.py`

`GraphScene` — `GraphModel`을 받아 `NodeItem`들을 배치하고 `Link`를 `LinkItem`으로 잇는다. 핀 경로의 첫 세그먼트로 노드를, 두 번째 세그먼트로 핀 행을 찾는다.

**Files:**
- Create: `src/t3dgraph/core/app/scene.py`
- Test: `tests/core/app/test_scene.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_scene.py
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.items import NodeItem, LinkItem


def _graph():
    a = Node(name="A", cls="X", position=(0.0, 0.0),
             pins=[Pin(name="O", cpp_type="exec", direction="Output")])
    b = Node(name="B", cls="X", position=(300.0, 0.0),
             pins=[Pin(name="I", cpp_type="exec", direction="Input")])
    return GraphModel(nodes=[a, b], links=[Link("A.O", "B.I")])


def test_scene_creates_one_item_per_node(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    assert sum(isinstance(i, NodeItem) for i in scene.items()) == 2


def test_scene_creates_one_link_item_per_link(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    assert sum(isinstance(i, LinkItem) for i in scene.items()) == 1


def test_scene_node_lookup(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    assert scene.node_item("A").node.name == "A"
    assert scene.node_item("Z") is None


def test_scene_repopulate_clears_previous(qtbot):
    scene = GraphScene()
    scene.populate(_graph())
    scene.populate(GraphModel(nodes=[Node(name="solo", cls="X")], links=[]))
    assert sum(isinstance(i, NodeItem) for i in scene.items()) == 1


def test_scene_link_to_unknown_node_skipped(qtbot):
    g = GraphModel(nodes=[Node(name="A", cls="X", pins=[Pin("O", "exec", "Output")])],
                   links=[Link("A.O", "Ghost.I")])
    scene = GraphScene()
    scene.populate(g)                                 # 예외 없이
    assert sum(isinstance(i, LinkItem) for i in scene.items()) == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_scene.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/scene.py
"""GraphModel → QGraphicsScene 빌드."""
from __future__ import annotations
from PySide6.QtWidgets import QGraphicsScene
from ..base.graph_model import GraphModel, Link
from .items import NodeItem, LinkItem


def _seg(pin_path: str, index: int) -> str:
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


class GraphScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._nodes: dict[str, NodeItem] = {}

    def node_item(self, name: str) -> NodeItem | None:
        return self._nodes.get(name)

    def populate(self, graph: GraphModel) -> None:
        self.clear()
        self._nodes = {}
        for node in graph.nodes:
            item = NodeItem(node)
            self.addItem(item)
            self._nodes[node.name] = item
        for link in graph.links:
            self._add_link(link)

    def _add_link(self, link: Link) -> None:
        src = self._nodes.get(_seg(link.source_path, 0))
        dst = self._nodes.get(_seg(link.target_path, 0))
        if src is None or dst is None:
            return                                    # 외부 참조 — 건너뜀
        p1 = src.pin_anchor(_seg(link.source_path, 1), "Output")
        p2 = dst.pin_anchor(_seg(link.target_path, 1), "Input")
        self.addItem(LinkItem(p1, p2))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_scene.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/scene.py tests/core/app/test_scene.py
git commit -m "feat(app): GraphScene builds items from GraphModel"
```

---

## Task 5: 뷰 — `core/app/graph_view.py`

`GraphView` — `QGraphicsView` 서브클래스. 휠 줌, 드래그 팬, `fit()`.

**Files:**
- Create: `src/t3dgraph/core/app/graph_view.py`
- Test: `tests/core/app/test_graph_view.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_graph_view.py
from t3dgraph.core.app.graph_view import GraphView
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.base.graph_model import GraphModel, Node


def test_view_holds_scene(qtbot):
    scene = GraphScene()
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(scene)
    assert view.scene() is scene


def test_view_drag_mode_is_scroll_hand(qtbot):
    from PySide6.QtWidgets import QGraphicsView
    view = GraphView()
    qtbot.addWidget(view)
    assert view.dragMode() == QGraphicsView.ScrollHandDrag


def test_fit_does_not_raise_on_populated_scene(qtbot):
    scene = GraphScene()
    scene.populate(GraphModel(nodes=[Node(name="A", cls="X", position=(0.0, 0.0))], links=[]))
    view = GraphView()
    qtbot.addWidget(view)
    view.setScene(scene)
    view.fit()                                        # 예외 없이
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_graph_view.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/graph_view.py
"""QGraphicsView — 팬·줌 가능한 그래프 캔버스."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView


class GraphView(QGraphicsView):
    _ZOOM_STEP = 1.15

    def __init__(self) -> None:
        super().__init__()
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event) -> None:
        factor = self._ZOOM_STEP if event.angleDelta().y() > 0 else 1 / self._ZOOM_STEP
        self.scale(factor, factor)

    def fit(self) -> None:
        """씬 전체가 보이도록 맞춘다."""
        if self.scene() is not None and self.scene().items():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_graph_view.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/graph_view.py tests/core/app/test_graph_view.py
git commit -m "feat(app): GraphView with pan/zoom/fit"
```

---

## Task 6: 메인 윈도우 — `core/app/main_window.py`

`MainWindow` — 메뉴(File>Open / Exit), 중앙 `GraphView`, "분석 중심" 도크 4개(좌·우·하 + 빈 placeholder). `AbstractGraphView` 구현. 파일 열기는 컨트롤러 콜백으로 위임.

**Files:**
- Create: `src/t3dgraph/core/app/main_window.py`
- Test: `tests/core/app/test_main_window.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_main_window.py
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.contracts import AbstractGraphView
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link


def test_main_window_is_graph_view(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert isinstance(w, AbstractGraphView)


def test_show_graph_populates_scene(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    g = GraphModel(
        nodes=[Node(name="A", cls="X", position=(0.0, 0.0),
                    pins=[Pin("O", "exec", "Output")]),
               Node(name="B", cls="X", position=(300.0, 0.0),
                    pins=[Pin("I", "exec", "Input")])],
        links=[Link("A.O", "B.I")],
    )
    w.show_graph(g)
    assert w.scene.node_item("A") is not None
    assert w.scene.node_item("B") is not None


def test_open_callback_invoked(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    captured = []
    w.set_open_handler(lambda path: captured.append(path))
    w.open_path("C:/some/file.t3d.txt")               # 콜백 직접 트리거
    assert captured == ["C:/some/file.t3d.txt"]


def test_has_three_docks(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    # 좌(노드 타입)·우(속성)·하(분석) — Phase 2a는 빈 placeholder
    assert {w.dock_left.windowTitle(), w.dock_right.windowTitle(),
            w.dock_bottom.windowTitle()} == {"노드 타입 필터", "속성 인스펙터", "분석"}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/main_window.py
"""메인 윈도우 — 메뉴·도크·중앙 그래프 캔버스."""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QDockWidget, QLabel, QFileDialog
from ..base.graph_model import GraphModel
from .contracts import AbstractGraphView
from .scene import GraphScene
from .graph_view import GraphView


def _placeholder_dock(title: str) -> QDockWidget:
    dock = QDockWidget(title)
    label = QLabel(f"({title} — Phase 2b)")
    label.setAlignment(Qt.AlignCenter)
    dock.setWidget(label)
    return dock


class MainWindow(QMainWindow, AbstractGraphView):
    """'분석 중심' 레이아웃. Phase 2a는 도크가 빈 placeholder."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("t3dgraph viewer")
        self.resize(1200, 800)

        self.scene = GraphScene()
        self.view = GraphView()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.dock_left = _placeholder_dock("노드 타입 필터")
        self.dock_right = _placeholder_dock("속성 인스펙터")
        self.dock_bottom = _placeholder_dock("분석")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_bottom)

        self._open_handler: Callable[[str], None] | None = None
        self._build_menu()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("파일")
        open_act = file_menu.addAction("열기…")
        open_act.triggered.connect(self._on_open)
        exit_act = file_menu.addAction("종료")
        exit_act.triggered.connect(self.close)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "T3D 파일 열기", "", "T3D files (*.t3d *.txt);;All files (*)")
        if path:
            self.open_path(path)

    def set_open_handler(self, handler: Callable[[str], None]) -> None:
        self._open_handler = handler

    def open_path(self, path: str) -> None:
        if self._open_handler is not None:
            self._open_handler(path)

    # --- AbstractGraphView ---
    def show_graph(self, graph: GraphModel) -> None:
        self.scene.populate(graph)
        self.view.fit()
        self.statusBar().showMessage(
            f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}", 5000)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window.py
git commit -m "feat(app): MainWindow shell with analysis-centric dock layout"
```

---

## Task 7: 컨트롤러 + 진입점 — `core/app/controller.py`, `core/app/app.py`

`AppController` — 파일 경로를 받아 Model 파이프라인(parse → detect → interpret)으로 `GraphModel`을 만들고 view에 렌더 지시. `app.py` — `QApplication` 조립 + 플러그인 view/controller 지연 참조 fallback.

**Files:**
- Create: `src/t3dgraph/core/app/controller.py`
- Create: `src/t3dgraph/core/app/app.py`
- Test: `tests/core/app/test_controller.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/core/app/test_controller.py
from t3dgraph.core.app.controller import AppController, load_ref
from t3dgraph.core.app.contracts import AbstractGraphController, AbstractGraphView
from t3dgraph.core.base.graph_model import GraphModel


class _FakeView(AbstractGraphView):
    def __init__(self):
        self.shown: GraphModel | None = None
        self.error: str | None = None
    def show_graph(self, graph):
        self.shown = graph
    def show_error(self, message):
        self.error = message


def test_controller_is_abstract_controller():
    assert issubclass(AppController, AbstractGraphController)


def test_open_real_file_renders(orion_dir):
    view = _FakeView()
    ctrl = AppController(view)
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    ctrl.open_file(str(f))
    assert view.shown is not None
    assert len(view.shown.nodes) > 0


def test_open_missing_file_reports_error():
    view = _FakeView()
    AppController(view).open_file("does-not-exist.t3d.txt")
    assert view.shown is None
    assert view.error is not None


def test_load_ref_resolves_dotted_path():
    cls = load_ref("t3dgraph.core.app.main_window:MainWindow")
    from t3dgraph.core.app.main_window import MainWindow
    assert cls is MainWindow


def test_load_ref_none_returns_none():
    assert load_ref(None) is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_controller.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# src/t3dgraph/core/app/controller.py
"""앱 컨트롤러 — 파일 열기 → Model 파이프라인 → view 렌더."""
from __future__ import annotations
import importlib
from pathlib import Path
from ..registry import default_registry
from ..t3d.document import parse_document
from ..t3d.objects import T3DParseError
from .contracts import AbstractGraphController, AbstractGraphView


def load_ref(ref: str | None):
    """'pkg.mod:Class' 문자열을 클래스로 해석. None이면 None."""
    if not ref:
        return None
    module_path, _, attr = ref.partition(":")
    return getattr(importlib.import_module(module_path), attr)


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


class AppController(AbstractGraphController):
    def __init__(self, view: AbstractGraphView) -> None:
        self.view = view

    def open_file(self, path: str) -> None:
        p = Path(path)
        if not p.is_file():
            self._fail(f"파일을 찾을 수 없습니다: {path}")
            return
        try:
            doc = parse_document(_read_text(p))
        except (UnicodeDecodeError, T3DParseError) as e:
            self._fail(f"파싱 실패: {e}")
            return
        try:
            plugin = default_registry().detect(doc)
        except LookupError as e:
            self._fail(str(e))
            return
        graph = plugin.interpreter_factory().interpret(doc)
        self.view.show_graph(graph)

    def _fail(self, message: str) -> None:
        show_error = getattr(self.view, "show_error", None)
        if callable(show_error):
            show_error(message)
```

`show_graph` 외에 에러 표시가 필요하므로 `MainWindow`에 `show_error`를 추가한다 — `core/app/main_window.py` 의 `show_graph` 메서드 다음에 추가:

```python
    def show_error(self, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "t3dgraph", message)
```

```python
# src/t3dgraph/core/app/app.py
"""뷰어 진입점 — QApplication 조립."""
from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from .controller import AppController, load_ref
from .main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    # 플러그인이 커스텀 view/controller를 제공하면 사용, 아니면 base.
    # (Phase 2a: 어느 플러그인도 view_ref/controller_ref 미설정 → base 사용)
    view_cls = MainWindow
    controller_cls = AppController

    window = view_cls()
    controller = controller_cls(window)
    window.set_open_handler(controller.open_file)
    window.show()

    # 명령행 인자로 파일을 주면 즉시 연다
    if len(sys.argv) > 1:
        controller.open_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

> 주: `load_ref`는 Phase 2b에서 `plugin.view_ref`/`controller_ref`가 설정될 때 `view_cls = load_ref(plugin.view_ref) or MainWindow` 형태로 쓰인다. Phase 2a에서는 import·테스트로 seam 동작만 검증하고 base를 쓴다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_controller.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/controller.py src/t3dgraph/core/app/app.py src/t3dgraph/core/app/main_window.py tests/core/app/test_controller.py
git commit -m "feat(app): AppController and application entry point"
```

---

## Task 8: 통합 스모크 테스트

실제 Orion 파일로 뷰어 전 경로(열기 → 파싱 → 해석 → 렌더)가 동작하는지 검증.

**Files:**
- Test: `tests/core/app/test_viewer_smoke.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/core/app/test_viewer_smoke.py
import pytest
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.controller import AppController
from t3dgraph.core.app.items import NodeItem, LinkItem


ALL = [
    "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt",
    "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__IK_Rig.t3d.txt",
    "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__Physics.t3d.txt",
]


@pytest.mark.parametrize("fname", ALL)
def test_viewer_opens_real_file(qtbot, orion_dir, fname):
    window = MainWindow()
    qtbot.addWidget(window)
    controller = AppController(window)
    window.set_open_handler(controller.open_file)

    window.open_path(str(orion_dir / fname))

    node_items = [i for i in window.scene.items() if isinstance(i, NodeItem)]
    link_items = [i for i in window.scene.items() if isinstance(i, LinkItem)]
    assert len(node_items) > 0
    # RigVMModel은 링크가 있음 (IK_Rig.ExecuteContext → StepPhysicsSolver.ExecutePin 등)
    if "RigVMModel" in fname:
        assert len(link_items) > 0


def test_viewer_window_shows(qtbot, orion_dir):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/core/app/test_viewer_smoke.py -q`
Expected: PASS — 실제 파일의 미처리 케이스가 드러나면 해당 모듈을 수정하고 회귀 테스트를 추가한 뒤 다시 실행

- [ ] **Step 3: 전체 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS (Phase 1/1.5 기존 63개 + Phase 2a 신규)

- [ ] **Step 4: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경에서): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 윈도우가 열리고 노드 그래프가 Position 좌표대로 표시됨

- [ ] **Step 5: Commit**

```bash
git add tests/core/app/test_viewer_smoke.py
git commit -m "test(app): viewer smoke tests over real Orion files"
```

---

## Self-Review

**1. Spec coverage (Phase 2a 범위)**
- spec §5.6 QGraphicsView 자체 구현, NodeItem/PinItem/LinkItem, Position 좌표 → Task 3·4 ✓ (PinItem은 NodeItem 자식 요소로 충분 — 독립 PinItem은 Phase 2b)
- spec §7.1 "분석 중심" 레이아웃(메뉴·중앙 캔버스·좌/우/하 도크) → Task 6 ✓ (도크 내용은 Phase 2b)
- spec §4.2 `core/app/` 구조, view/controller 추상 → Task 2·6·7 ✓
- spec §4.3 Qt 경계 — Qt import는 `core/app/`에만, Model 레이어 불변 ✓
- spec §8 GUI 에러 — 파일 없음·파싱 실패·그래프타입 미검출 → `AppController._fail` + `MainWindow.show_error`(QMessageBox) Task 7 ✓
- **범위 밖(Phase 2b, 의도적)**: 노드 타입 필터·속성 인스펙터(연결됨/변경됨)·분석 도크(수렴점·실행 순서)·뷰 모드 — Task 6에서 도크는 빈 placeholder로만 둠

**2. Placeholder scan** — "TBD/TODO" 없음. 도크의 `(... — Phase 2b)` 라벨은 실제 placeholder 위젯의 표시 텍스트이지 계획 미완성이 아니다. Task 7의 `load_ref`는 Phase 2a에서 테스트로 검증되는 실제 동작 함수이며 Phase 2b 확장 지점이다.

**3. Type consistency**
- `AbstractGraphView.show_graph(graph)` — Task 2 정의, `MainWindow`(Task 6)·`_FakeView`(Task 7) 구현 일치
- `AbstractGraphController.open_file(path)` — Task 2 정의, `AppController`(Task 7) 구현 일치
- `GraphScene.populate`/`node_item` — Task 4 정의, `MainWindow`(Task 6)·스모크(Task 8) 사용 일치
- `NodeItem(node)`/`pin_anchor`/`LinkItem(p1,p2)` — Task 3 정의, `GraphScene`(Task 4) 사용 일치
- `MainWindow.show_error` — Task 7에서 추가, `AppController._fail`이 getattr로 호출 — 일치
- `NODE_WIDTH`/`ROW_HEIGHT`/`HEADER_HEIGHT` 상수 — Task 3 정의, Task 3 테스트에서 import 일치

---

## 다음 단계 — Phase 2b

Phase 2a 완료 후 planner가 별도 계획 작성:
- 노드 타입 필터 패널 (좌측 도크)
- 속성 인스펙터 (우측 도크) — 핀 기본값, 연결됨(연결 노드로 네비게이션), 변경됨(타입 zero-value 휴리스틱)
- 분석 도크 (하단) — 수렴점 목록 탭 + 실행 순서 코드 뷰 탭, 캔버스 양방향 연동
- 뷰 모드 — 연결된 핀만 표시, 깊이 펼침, fan-in 강조
- 독립 `PinItem` (인스펙터 연동용)
- 필요 시 `plugins/rigvm/view.py` (NodeColor 등 RigVM 고유 렌더) + `plugin.view_ref` 설정
- 백로그 — `--lenient` 플래그, round-trip 익스포트, 에셋 resolver, CLI `--json`
