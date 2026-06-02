# batch ⑬ g5 — 함수/서브그래프 시각 구분 (F28) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `RigVMCollapseNode`/`RigVMFunctionReferenceNode` 노드를 항상 chevron으로 표시. 색으로 진입 가능 상태 구분 — 녹색(가능)·노랑(폴더 필요)·회색(데이터 없음).

**Spec:** §7

**Pre-condition:** master `f8fa09d` 이상. g1·g4와 items.py 공유.

---

## Task 1: function-like chevron 상태 표시

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_function_marker.py`

- [ ] **Step 1: 테스트**

```python
"""g5 (F28) — function-like 노드 chevron 상태."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsSimpleTextItem

from t3dgraph.core.base.graph_model import Node, GraphModel
from t3dgraph.core.app.items import NodeItem


def _chev(item: NodeItem) -> QGraphicsSimpleTextItem | None:
    return next(
        (c for c in item.childItems()
         if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "▶"),
        None,
    )


def test_collapse_node_with_subgraph_green_chevron(qtbot) -> None:
    n = Node(name="C1", cls="/Script/RigVMDeveloper.RigVMCollapseNode",
             subgraph=GraphModel())
    item = NodeItem(n)
    chev = _chev(item)
    assert chev is not None
    color = chev.brush().color()
    # 녹색 계열
    assert color.green() > color.red() and color.green() > color.blue()


def test_function_ref_without_subgraph_yellow_chevron(qtbot) -> None:
    n = Node(name="F1", cls="/Script/RigVMDeveloper.RigVMFunctionReferenceNode")
    item = NodeItem(n)
    chev = _chev(item)
    assert chev is not None
    color = chev.brush().color()
    # 노랑/주황 계열 (R+G > B*2)
    assert color.red() + color.green() > color.blue() * 2


def test_collapse_node_without_subgraph_gray_chevron(qtbot) -> None:
    n = Node(name="C2", cls="/Script/RigVMDeveloper.RigVMCollapseNode")
    item = NodeItem(n)
    chev = _chev(item)
    assert chev is not None
    color = chev.brush().color()
    # 회색 — RGB 거의 동일
    assert abs(color.red() - color.green()) < 20
    assert abs(color.green() - color.blue()) < 20


def test_regular_node_no_chevron(qtbot) -> None:
    n = Node(name="U1", cls="/Script/RigVMDeveloper.RigVMUnitNode")
    item = NodeItem(n)
    assert _chev(item) is None


def test_function_ref_yellow_chevron_has_tooltip(qtbot) -> None:
    n = Node(name="F1", cls="/Script/RigVMDeveloper.RigVMFunctionReferenceNode")
    item = NodeItem(n)
    tooltip = item.toolTip()
    assert "함수" in tooltip or "에셋 폴더" in tooltip
```

- [ ] **Step 2: NodeItem 변경**

`src/t3dgraph/core/app/items.py` NodeItem 클래스에 헬퍼 + 호출:

```python
def _function_entry_state(self) -> tuple[QColor, str] | None:
    """function-like 노드의 진입 가능 상태. (chevron 색, 툴팁) 또는 None."""
    suffix = (self.node.cls or "").rsplit(".", 1)[-1]
    if suffix not in ("RigVMCollapseNode", "RigVMFunctionReferenceNode"):
        return None
    if self.node.subgraph is not None:
        return QColor("#90EE90"), "더블클릭하여 서브그래프 진입"
    if suffix == "RigVMFunctionReferenceNode":
        return (
            QColor("#FFD700"),
            "함수 참조 — 함수 본문이 외부 파일에 있음.\n"
            "에셋 폴더 열기로 함수 라이브러리 등록 필요."
        )
    return QColor("#888888"), "내부 그래프 데이터 없음"
```

`__init__`의 기존 chevron 블록 교체:

```python
# 기존
if node.subgraph is not None:
    chev = QGraphicsSimpleTextItem("▶", self)
    chev.setBrush(QBrush(QColor(200, 200, 120)))
    chev.setPos(NODE_WIDTH - 16, 5)
    self.setCursor(Qt.PointingHandCursor)
    self.setToolTip("더블클릭하여 서브그래프 진입")

# 변경
state = self._function_entry_state()
if state is not None:
    chev_color, tooltip = state
    chev = QGraphicsSimpleTextItem("▶", self)
    chev.setBrush(QBrush(chev_color))
    chev.setPos(NODE_WIDTH - 16, 5)
    if node.subgraph is not None:
        self.setCursor(Qt.PointingHandCursor)
    self.setToolTip(tooltip)
```

(주의: `_function_entry_state`는 인스턴스 메서드이므로 `__init__`에서 호출 가능. self.node는 그 시점에 이미 설정됨.)

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_function_marker.py -v`
Expected: 5 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (기존 chevron 테스트가 색 검사하면 갱신 — 보통 존재 여부만 검사).

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_function_marker.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): function-like node chevron states (F28)"
```

## 완료 후

F28 시각 정보 추가 완료. 노드 직접 더블클릭(기존 동작) 또는 chevron 색으로 진입 가능성 즉시 인지 가능. 미니맵 진입 정상화는 별도 슬라이스 deferred.
