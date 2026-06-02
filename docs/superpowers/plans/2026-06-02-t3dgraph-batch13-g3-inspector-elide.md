# batch ⑬ g3 — 인스펙터 헤더 elide (F24) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** InspectorPanel `_title` QLabel을 단일 라인 강제 + elide right로 잘림 표시. 풀 텍스트는 툴팁.

**Spec:** §5

**Pre-condition:** master `f8fa09d` 이상. 다른 슬라이스와 파일 충돌 없음.

---

## Task 1: 단일 라인 + elide + resize 핸들

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py`
- Modify: `tests/core/app/test_inspector_layout.py` 또는 신규

- [ ] **Step 1: 테스트**

```python
"""g3 (F24) — InspectorPanel 헤더 elide."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QSizePolicy

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.inspector_panel import InspectorPanel


def test_title_word_wrap_disabled(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    assert panel._title.wordWrap() is False


def test_title_height_capped(qtbot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    fm = QFontMetrics(panel._title.font())
    # maximumHeight이 한 줄 + 여유 (8px 이내)
    assert panel._title.maximumHeight() <= fm.lineSpacing() + 8


def test_long_title_elided_with_tooltip(qtbot) -> None:
    node = Node(name="N1", cls="A" * 100,
                role_summary="B" * 100, role_category="C" * 100)
    g = GraphModel(nodes=[node])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.resize(300, 200)
    panel.show_node(node, g)
    # 표시 텍스트에 '…' (elide marker)
    assert "…" in panel._title.text() or "..." in panel._title.text()
    # 툴팁은 풀 텍스트(짧지 않음)
    assert len(panel._title.toolTip()) > len(panel._title.text())


def test_short_title_not_elided(qtbot) -> None:
    node = Node(name="Short", cls="Foo")
    g = GraphModel(nodes=[node])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.resize(400, 200)
    panel.show_node(node, g)
    assert "…" not in panel._title.text()
```

- [ ] **Step 2: InspectorPanel 변경**

`src/t3dgraph/core/app/inspector_panel.py` 상단 import:

```python
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView, QSizePolicy,
)
```

`__init__` 본문에서 `self._title = QLabel(...)` 다음:

```python
self._title.setWordWrap(False)
self._title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
fm = QFontMetrics(self._title.font())
self._title.setMaximumHeight(fm.lineSpacing() + 4)
self._title_raw_text: str = ""   # 풀 텍스트 보관
```

`show_node`의 `self._title.setText(...)`를 `self._set_title(...)`로 교체:

```python
def show_node(self, node, graph) -> None:
    self._tree.clear()
    self._items = {}
    if node is None:
        self._set_title("(노드를 선택하세요)")
        return
    header = node.display_name or node.name or "?"
    cls_part = node.cls or "?"
    role_bits = []
    if node.role_category:
        role_bits.append(node.role_category)
    if node.role_summary:
        role_bits.append(node.role_summary)
    role_suffix = f"   ·   역할: {' · '.join(role_bits)}" if role_bits else ""
    self._set_title(f"{header}  [{cls_part}]{role_suffix}")
    connected = _connected_pin_paths(graph)
    for pin in node.pins:
        self._add_pin(pin, node.name, pin.name, connected, graph,
                      self._tree.invisibleRootItem())

def _set_title(self, raw_text: str) -> None:
    self._title_raw_text = raw_text
    self._apply_title_elide()

def _apply_title_elide(self) -> None:
    fm = QFontMetrics(self._title.font())
    available = max(self._title.width() - 12, 100)
    elided = fm.elidedText(self._title_raw_text, Qt.ElideRight, available)
    self._title.setText(elided)
    self._title.setToolTip(self._title_raw_text)

def resizeEvent(self, event) -> None:
    super().resizeEvent(event)
    self._apply_title_elide()
```

- [ ] **Step 3: 실행**

Run: `pytest tests/core/app/test_inspector_layout.py -v`
Expected: 전 통과.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 4: 커밋**

```bash
git add tests/core/app/test_inspector_layout.py src/t3dgraph/core/app/inspector_panel.py
git commit -m "fix(app): inspector title single-line elide + tooltip (F24)"
```

## 완료 후

F24 해소.
