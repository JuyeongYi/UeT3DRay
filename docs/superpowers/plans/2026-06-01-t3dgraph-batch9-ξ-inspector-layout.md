# batch ⑨ ξ (xi) — 인스펙터 레이아웃 (F15) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 노드 선택 시 인스펙터 dock이 옆으로 폭주하는 현상을 잡는다. 컬럼별 디폴트 폭 + Interactive resize + 가로 스크롤 + 잘림 셀 툴팁(F15).

**Architecture:** `InspectorPanel`의 `QTreeWidget` 헤더 설정만 조정. 다른 모듈·모델 무변경. 슬라이스 μ·ν와 독립 — 어디서든 끼울 수 있다.

**Tech Stack:** PySide6 (`QHeaderView`, `QTreeWidget`), pytest + pytest-qt.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-1-vis-rendering-design.md` §6

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/inspector_panel.py` | 수정 (헤더 모드·컬럼 폭·스크롤 정책·툴팁) |
| `tests/app/test_inspector_layout.py` | 신규 |

---

## Task 1: 인스펙터 컬럼 폭 안정 — TDD

**Files:**
- Create: `tests/app/test_inspector_layout.py`
- Modify: `src/t3dgraph/core/app/inspector_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_inspector_layout.py`:

```python
"""F15 InspectorPanel 폭 안정 — 컬럼 디폴트·Interactive·가로 스크롤·툴팁."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin
from t3dgraph.core.app.inspector_panel import InspectorPanel


_EXPECTED_WIDTHS = (140, 160, 70, 120, 90)


def _graph_with_long_default() -> GraphModel:
    long_default = "x" * 200
    pin = Pin(name="P", cpp_type="FRigVMRedirectorTargetsExtremelyLongTypeName",
              direction="Input", default_value=long_default)
    n = Node(name="N1", cls="T", pins=[pin])
    return GraphModel(nodes=[n], label="root")


def test_columns_have_default_widths(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    for i, w in enumerate(_EXPECTED_WIDTHS):
        assert panel._tree.columnWidth(i) == w


def test_header_mode_is_interactive(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    header = panel._tree.header()
    for i in range(panel._tree.columnCount()):
        assert header.sectionResizeMode(i) == QHeaderView.Interactive


def test_stretch_last_section_off(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    assert panel._tree.header().stretchLastSection() is False


def test_horizontal_scroll_as_needed(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    assert panel._tree.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded


def test_long_default_gets_tooltip(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    graph = _graph_with_long_default()
    panel.show_node(graph.nodes[0], graph)
    item = panel._items["N1.P"]
    # 기본값 컬럼(3)이 잘림 → 풀 텍스트 툴팁
    assert "x" * 200 in item.toolTip(3)


def test_long_cpp_type_gets_tooltip(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    graph = _graph_with_long_default()
    panel.show_node(graph.nodes[0], graph)
    item = panel._items["N1.P"]
    assert "FRigVMRedirectorTargetsExtremelyLongTypeName" in item.toolTip(1)


def test_short_value_no_tooltip(qtbot) -> None:
    pin = Pin(name="P", cpp_type="bool", direction="Input", default_value="False")
    graph = GraphModel(nodes=[Node(name="N1", cls="T", pins=[pin])], label="root")
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(graph.nodes[0], graph)
    item = panel._items["N1.P"]
    assert item.toolTip(3) == ""
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_inspector_layout.py -v`
Expected: FAIL — 디폴트 컬럼 폭·Interactive·툴팁 미구현.

- [ ] **Step 3: `InspectorPanel` 수정**

`src/t3dgraph/core/app/inspector_panel.py` 상단 import 갱신:

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView,
)
```

`__init__` 본문을 다음으로 교체:

```python
def __init__(self) -> None:
    super().__init__()
    layout = QVBoxLayout(self)
    self._title = QLabel("(노드를 선택하세요)")
    self._tree = QTreeWidget()
    self._tree.setColumnCount(5)
    self._tree.setHeaderLabels(["핀", "타입", "방향", "기본값", "상태"])
    header = self._tree.header()
    header.setSectionResizeMode(QHeaderView.Interactive)
    header.setStretchLastSection(False)
    self._col_widths = (140, 160, 70, 120, 90)
    for i, w in enumerate(self._col_widths):
        self._tree.setColumnWidth(i, w)
    self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    layout.addWidget(self._title)
    layout.addWidget(self._tree)
    self._tree.itemActivated.connect(self._on_activated)
    self._items: dict[str, QTreeWidgetItem] = {}
```

`_add_pin` 끝부분 (`parent.addChild(item)` 다음, `self._items[full] = item` 위)에 툴팁 부여 로직 추가. `_add_pin` 전체 메서드를 다음으로 교체:

```python
def _add_pin(self, pin: Pin, node_name: str, path: str,
             connected: set[str], graph: GraphModel, parent: QTreeWidgetItem) -> None:
    full = f"{node_name}.{path}"
    is_conn = full in connected
    is_chg = is_changed_from_default(pin)
    status = " · ".join(
        s for s in ("연결됨" if is_conn else "", "변경됨(추정)" if is_chg else "") if s)
    texts = [pin.name, pin.cpp_type or "", pin.direction or "",
             pin.default_value or "", status]
    item = QTreeWidgetItem(texts)
    self._apply_truncation_tooltips(item, texts)
    if is_conn:
        peer = _peer_of(full, graph)
        if peer:
            item.setData(0, _PEER_ROLE, peer)
    parent.addChild(item)
    self._items[full] = item
    for sub in pin.subpins:
        self._add_pin(sub, node_name, f"{path}.{sub.name}", connected, graph, item)

def _apply_truncation_tooltips(self, item: QTreeWidgetItem, texts: list[str]) -> None:
    """셀 텍스트가 컬럼 폭을 초과하면 ToolTipRole에 풀 텍스트를 박는다."""
    fm = QFontMetrics(self._tree.font())
    for i, text in enumerate(texts):
        if not text:
            continue
        if fm.horizontalAdvance(text) > self._col_widths[i] - 12:
            item.setToolTip(i, text)
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_inspector_layout.py -v`
Expected: 7 passed

- [ ] **Step 5: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과 (인스펙터 동작 시그니처 변경 없음).

- [ ] **Step 6: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

긴 cpp_type을 가진 노드(`Orion_WorkStation_Rig_Analysis`의 RigVMDispatch 노드 등) 선택 시 인스펙터 dock 폭이 폭주하지 않고, 셀 hover 시 풀 텍스트 툴팁이 뜨는지.

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_inspector_layout.py src/t3dgraph/core/app/inspector_panel.py
git commit -m "feat(app): inspector column widths + interactive header + tooltips (F15)"
```

---

## Self-Review 체크리스트

- Spec §6.1 컬럼 디폴트 폭 (140·160·70·120·90) — Task 1 Step 3 ✅
- Spec §6.1 Interactive resize — Task 1 Step 3 ✅
- Spec §6.1 stretchLastSection=False — Task 1 Step 3 ✅
- Spec §6.1 가로 스크롤 AsNeeded — Task 1 Step 3 ✅
- Spec §6.1 잘림 셀 ToolTipRole — Task 1 Step 3 `_apply_truncation_tooltips` ✅
- Spec §6.2 inspector_panel.py 단일 파일 변경 — ✅
- Spec §6.3 테스트 7건 — ✅
- PRESERVE-ALL — 노드/링크/모델 무영향 ✅
- 독립성: μ·ν와 충돌 없음 (다른 파일 미접근) ✅

---

## 완료 후

머지 후:
- Spec 1 (μ/ν/ξ) 모두 완료
- Spec 2 (F11·F14·F16·F17·F20) 별도 brainstorming 세션 진입 — 트래커 ⑨ §4.2 참조
