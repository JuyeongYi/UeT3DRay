# Slice ε: 잡정리 묶음 (P1.5-A1 + P2a-B2 + P2c-B1 + BL1-B2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백로그 잔여 4건을 한 묶음으로. (1) ValueParseError에 pos 노출, (2) AbstractGraphView.show_error 계약 추가, (3) highlight_node 보일러플레이트를 NavigablePanel로 추출, (4) scene._connected_paths_by_node에서 pin_segment(0) → node_of 일관화.

**Architecture:** 독립 4개 정리. 각 task가 별도 commit. δ와 다른 파일 영역(`values.py`, `contracts.py`, `navigable_panel.py`, `scene.py`)이라 병렬 가능.

**Tech Stack:** Python 3.11+, PySide6, pytest.

**Spec ref:** `docs/superpowers/specs/2026-05-22-t3dgraph-batch-4-analysis-bundle-cleanup-design.md` §2 slice ε.

---

### Task 1: ValueParseError에 pos 속성 (P1.5-A1)

**Files:**
- Modify: `src/t3dgraph/core/t3d/values.py`
- Modify: `tests/core/t3d/test_values.py` (또는 신규)

- [ ] **Step 1: Test**

`tests/core/t3d/test_values_pos.py`(신규):

```python
import pytest
from t3dgraph.core.t3d.values import parse_value, ValueParseError


def test_value_parse_error_carries_pos():
    with pytest.raises(ValueParseError) as exc_info:
        parse_value("(X=1, Y=)")
    err = exc_info.value
    assert hasattr(err, "pos")
    assert isinstance(err.pos, int)
    assert err.pos >= 0


def test_pos_points_to_offending_position():
    src = "(X=1, Y=garbage"
    with pytest.raises(ValueParseError) as exc_info:
        parse_value(src)
    # pos가 적어도 'Y=' 이후를 가리키는지 (정확 위치는 구현 자유)
    assert exc_info.value.pos >= src.index("Y")
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

`values.py`의 `ValueParseError` 클래스:

```python
class ValueParseError(Exception):
    def __init__(self, message: str, pos: int = 0):
        super().__init__(message)
        self.pos = pos
```

parse 함수가 raise 시 현재 토큰/스캔 위치를 pos로 전달. 구체 위치는 기존 토큰 인덱스로.

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/t3d/values.py tests/core/t3d/test_values_pos.py
git commit -m "feat(values): ValueParseError carries pos attribute (P1.5-A1)"
```

---

### Task 2: AbstractGraphView.show_error 계약 (P2a-B2)

**Files:**
- Modify: `src/t3dgraph/core/app/contracts.py`
- Modify: `src/t3dgraph/core/app/controller.py`

- [ ] **Step 1: 변경 — contracts**

```python
class AbstractGraphView(ABC):
    ...
    @abstractmethod
    def show_error(self, message: str) -> None:
        """오류 메시지를 사용자에게 표시한다."""
        raise NotImplementedError
```

- [ ] **Step 2: controller._fail 단순화 — getattr 제거**

```python
def _fail(self, message: str) -> None:
    self.view.show_error(message)
```

MainWindow에 이미 `show_error` 구현되어 있음 (line 258).

- [ ] **Step 3: 회귀**

```
pytest tests/ -x
```

- [ ] **Step 4: Commit**

```
git add src/t3dgraph/core/app/contracts.py src/t3dgraph/core/app/controller.py
git commit -m "refactor(contracts): show_error abstract; drop controller getattr (P2a-B2)"
```

---

### Task 3: NavigablePanel.highlight_node 공용 (P2c-B1)

**Files:**
- Modify: `src/t3dgraph/core/app/navigable_panel.py`
- Modify: `src/t3dgraph/core/app/inspector_panel.py` · `analysis_panel.py` · `execution_order_panel.py` · `data_flow_panel.py`
- Create: `tests/core/app/test_navigable_panel.py`

- [ ] **Step 1: Test**

```python
import pytest
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from t3dgraph.core.app.navigable_panel import NavigablePanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakePanel(NavigablePanel):
    def __init__(self):
        super().__init__()
        self.tree = QTreeWidget()
        self._items = {"A": QTreeWidgetItem(["A"])}
        self.tree.addTopLevelItem(self._items["A"])

    def _lookup_item(self, name):
        return self._items.get(name)


def test_highlight_node_sets_current(qapp):
    p = _FakePanel()
    p.highlight_node("A")
    # _FakePanel은 _set_current_item 기본 — tree.setCurrentItem 호출
    assert p.tree.currentItem() is p._items["A"]


def test_highlight_node_none_clears(qapp):
    p = _FakePanel()
    p.highlight_node("A")
    p.highlight_node(None)
    assert p.tree.currentItem() is None
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement — NavigablePanel 베이스 확장**

```python
"""네비게이션 가능한 도크 패널의 공용 베이스."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem


class NavigablePanel(QWidget):
    """`navigate_requested(node_name)` + `highlight_node(name | None)` 공통."""
    navigate_requested = Signal(str)

    def highlight_node(self, name: str | None) -> None:
        item = self._lookup_item(name) if name else None
        self._set_current_item(item)

    def _lookup_item(self, name: str):
        """서브클래스가 override — 노드 이름 → QTreeWidgetItem 또는 None."""
        return None

    def _set_current_item(self, item) -> None:
        """기본 — self.tree(QTreeWidget) 가 있으면 currentItem 설정 또는 clearSelection."""
        tree = getattr(self, "tree", None) or getattr(self, "_tree", None)
        if tree is None:
            return
        if item is not None:
            tree.setCurrentItem(item)
        else:
            tree.clearSelection()
            tree.setCurrentItem(None)
```

각 패널의 기존 `highlight_node`는 **삭제** 후 `_lookup_item`만 구현:

`inspector_panel.py`에서는 이미 highlight_node 메서드 없음 — `activate_pin`만 있음. skip 또는 추가.

`analysis_panel.py`:
```python
def _lookup_item(self, name):
    return self._rows.get(name)
```
(기존 highlight_node 메서드 삭제)

`execution_order_panel.py`:
```python
def _lookup_item(self, name):
    return self._rows.get(name)
```
(기존 highlight_node 삭제)

`data_flow_panel.py`:
```python
def _lookup_item(self, name):
    items = self._items.get(name)
    return items[0] if items else None
```
(기존 highlight_node 삭제)

각 패널의 `tree` 또는 `_tree` 속성 이름을 일관 — 기존 `_tree`를 그대로 두고 NavigablePanel이 둘 다 확인하면 OK (위 코드).

- [ ] **Step 4: Run — pass**

```
pytest tests/core/app/test_navigable_panel.py -v
pytest tests/ -x
```

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/core/app/navigable_panel.py \
        src/t3dgraph/core/app/analysis_panel.py \
        src/t3dgraph/core/app/execution_order_panel.py \
        src/t3dgraph/core/app/data_flow_panel.py \
        tests/core/app/test_navigable_panel.py
git commit -m "refactor(navigable_panel): centralize highlight_node template (P2c-B1)"
```

---

### Task 4: scene `_connected_paths_by_node` 일관화 (BL1-B2)

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`

- [ ] **Step 1: 변경**

```python
@staticmethod
def _connected_paths_by_node(graph: GraphModel) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for link in graph.links:
        for path in (link.source_path, link.target_path):
            node = node_of(path)               # was: pin_segment(path, 0)
            bucket = out.setdefault(node, set())
            parts = path.split(".")
            for i in range(2, len(parts) + 1):
                bucket.add(".".join(parts[:i]))
    return out
```

import에서 `pin_segment`가 더 이상 안 쓰이면 제거.

- [ ] **Step 2: 회귀**

```
pytest tests/ -x
```
Expected: PASS.

- [ ] **Step 3: Commit**

```
git add src/t3dgraph/core/app/scene.py
git commit -m "refactor(scene): node_of() instead of pin_segment(path, 0) (BL1-B2)"
```

---

### Task 5: 전체 회귀

```
pytest tests/ -v
```
Expected: PASS.

---

## 완료 정의

- [ ] Task 1-5 PASS
- [ ] `ValueParseError`에 `pos` 속성
- [ ] `AbstractGraphView.show_error` 추상 + controller가 직접 호출
- [ ] NavigablePanel이 `highlight_node` 템플릿 메서드 — 각 패널은 `_lookup_item`만
- [ ] scene이 `node_of` 일관 사용
