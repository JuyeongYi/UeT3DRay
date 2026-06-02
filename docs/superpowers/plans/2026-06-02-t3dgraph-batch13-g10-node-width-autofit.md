# batch ⑬ g10 — 노드 폭 자동 맞춤 (F32) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `NodeItem`이 타이틀과 핀 라벨 폭에 맞춰 인스턴스별 노드 폭 결정. `NODE_WIDTH` 상수 제거(또는 MIN_NODE_WIDTH로 명칭 변경). 라벨이 노드 밖으로 나가는 문제 해결.

**Pre-condition:** master `185b639` 이상. g9와 items.py 공유 — 둘 중 먼저 머지된 쪽에 rebase.

---

## Task 1: 인스턴스별 node_width 계산

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_node_width_autofit.py`

- [ ] **Step 1: 테스트**

```python
"""g10 (F32) — NodeItem 폭 자동 맞춤."""
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem, MIN_NODE_WIDTH, MAX_NODE_WIDTH


def test_node_width_at_least_min() -> None:
    n = Node(name="X", cls="T")
    item = NodeItem(n)
    assert item._node_width >= MIN_NODE_WIDTH


def test_long_title_expands_width(qtbot) -> None:
    """긴 display_name이 폭 확장."""
    short = Node(name="N", cls="T", display_name="X")
    long_ = Node(name="N", cls="T",
                 display_name="VeryLongFunctionNameThatExceedsDefault")
    short_item = NodeItem(short)
    long_item = NodeItem(long_)
    assert long_item._node_width > short_item._node_width


def test_long_pin_labels_expand_width(qtbot) -> None:
    """긴 핀 라벨이 폭 확장."""
    short = Node(name="N", cls="T",
                 pins=[Pin(name="A", cpp_type="bool", direction="Input")])
    long_ = Node(name="N", cls="T",
                 pins=[Pin(name="VeryLongInputParameterName",
                           cpp_type="bool", direction="Input")])
    s = NodeItem(short)
    l = NodeItem(long_)
    assert l._node_width > s._node_width


def test_node_width_capped(qtbot) -> None:
    """극단적으로 긴 라벨도 MAX_NODE_WIDTH로 제한."""
    n = Node(name="N", cls="T",
             pins=[Pin(name="A" * 200, cpp_type="bool", direction="Input")])
    item = NodeItem(n)
    assert item._node_width <= MAX_NODE_WIDTH


def test_pin_anchor_uses_instance_width(qtbot) -> None:
    """pin_anchor가 instance node_width 기준으로 우측 좌표 반환."""
    from PySide6.QtCore import QPointF
    long_ = Node(name="N", cls="T",
                 pins=[Pin(name="LongPinName_AAAAAA", cpp_type="bool",
                           direction="Output")])
    item = NodeItem(long_)
    anchor = item.pin_anchor("LongPinName_AAAAAA", "Output")
    # Output anchor는 노드 우측 — instance width와 일치
    expected_x = item.pos().x() + item._node_width
    assert abs(anchor.x() - expected_x) < 1.0
```

- [ ] **Step 2: 구현 — `MIN_NODE_WIDTH`/`MAX_NODE_WIDTH` 도입**

`src/t3dgraph/core/app/items.py`:

```python
MIN_NODE_WIDTH = 200.0
MAX_NODE_WIDTH = 400.0
NODE_HORIZONTAL_PADDING = 24.0    # 라벨 양쪽 패딩

# 기존 NODE_WIDTH 상수는 호환을 위해 잔존 또는 제거
NODE_WIDTH = MIN_NODE_WIDTH      # legacy alias (점진 제거)
```

`NodeItem.__init__`:

```python
def __init__(self, node, *, ...):
    rows = collect_pin_rows(...)
    # 폭 계산 — 헤더 + 양쪽 핀 라벨 최대
    self._node_width = self._compute_width(node, rows)
    height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
    super().__init__(QRectF(0, 0, self._node_width, height))
    # ... 기존 ...

def _compute_width(self, node, rows) -> float:
    fm = QFontMetrics(QFont())
    title_text = node.display_name or node.name or "?"
    title_w = fm.horizontalAdvance(title_text) + 24.0   # 좌 6 + 우 18(chevron 여유)
    pin_w = MIN_NODE_WIDTH
    for row in rows:
        label_text = row.pin.name
        if row.pin.variable_source:
            label_text += f" (var: {row.pin.variable_source})"
        lw = fm.horizontalAdvance(label_text)
        # input과 output 분리 시 최대 = 양쪽 합 + 가운데 패딩
        # 단순화: 한 row의 label_w + indent + arrow + dot 영역 (~30px) 만 더해 양쪽 모드 모두 커버
        per_side = lw + 30 + row.depth * 12
        # 단순 모드: 양쪽 라벨 폭이 같다고 가정하지 않고 max로
        pin_w = max(pin_w, per_side * 2 + NODE_HORIZONTAL_PADDING)
    return min(max(MIN_NODE_WIDTH, title_w, pin_w), MAX_NODE_WIDTH)
```

`pin_anchor` 갱신 — `NODE_WIDTH` → `self._node_width`:

```python
def pin_anchor(self, pin_subpath: str, direction: str) -> QPointF:
    full = f"{self.node.name}.{pin_subpath}"
    cy = self._rows.get(full)
    if cy is None:
        top = pin_subpath.split(".", 1)[0]
        cy = self._rows.get(f"{self.node.name}.{top}")
    if cy is None:
        return self.mapToScene(QPointF(self._node_width / 2,
                                       self.rect().height() / 2))
    lx = self._node_width if (direction or "").lower() == "output" else 0.0
    return self.mapToScene(QPointF(lx, cy))
```

기타 `NODE_WIDTH` 직접 참조도 `self._node_width`로 갱신 (chevron 위치, 라벨 우측 정렬, arrow 위치 등).

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_node_width_autofit.py -v`
Expected: 5 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (기존 테스트가 NODE_WIDTH=200 가정해도 인스턴스 폭이 그 값 근처이면 통과).

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

긴 노드명 / 긴 핀 이름 가진 노드 폭이 자동 확대 — 라벨이 노드 안에 다 들어옴.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_node_width_autofit.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem instance width autofit for title/pin labels (F32)"
```

## 완료 후

F32 해소. 노드 라벨이 더 이상 노드 밖으로 나가지 않음.
