# batch ⑬ g1 — 핀 Direction 정확화 (F21) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Hidden 핀 dot 미표시(라벨 muted), IO 핀 양쪽 dot, subpin이 direction 미설정이면 부모로부터 상속. 결과: 출력 노드의 "phantom input dot" 제거.

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-13-visual-fixes-design.md` §3

**Pre-condition:** master `f8fa09d` 이상. g4/g5와 items.py 공유 — 머지 순서 코디네이션.

---

## Task 1: PinRow에 effective_direction + collect_pin_rows 상속

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `tests/app/test_items_direction.py` 신규

- [ ] **Step 1: 테스트**

```python
"""g1 (F21) — Direction-aware 렌더링."""
from PySide6.QtWidgets import QGraphicsEllipseItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem, collect_pin_rows


def _dots_on_side(item: NodeItem, x_threshold: float, *, left: bool) -> int:
    """left=True면 x < threshold, False면 x > threshold."""
    n = 0
    for c in item.childItems():
        if not isinstance(c, QGraphicsEllipseItem):
            continue
        cx = c.rect().center().x()
        if (left and cx < x_threshold) or (not left and cx > x_threshold):
            n += 1
    return n


def test_hidden_pin_no_dot(qtbot) -> None:
    n = Node(name="N", cls="T",
             pins=[Pin(name="Cfg", cpp_type="bool", direction="Hidden")])
    item = NodeItem(n)
    # Hidden → dot 0개
    assert _dots_on_side(item, 100, left=True) == 0
    assert _dots_on_side(item, 100, left=False) == 0


def test_io_pin_both_sides(qtbot) -> None:
    n = Node(name="N", cls="T",
             pins=[Pin(name="Exec", cpp_type="FRigVMExecuteContext",
                       direction="IO", is_execution=True)])
    item = NodeItem(n)
    assert _dots_on_side(item, 100, left=True) == 1
    assert _dots_on_side(item, 100, left=False) == 1


def test_output_subpin_inherits_parent_direction(qtbot) -> None:
    sub_x = Pin(name="X", cpp_type="float", direction=None)
    sub_y = Pin(name="Y", cpp_type="float", direction=None)
    parent = Pin(name="Out", cpp_type="FVector", direction="Output",
                 subpins=[sub_x, sub_y])
    n = Node(name="N", cls="T", pins=[parent])
    item = NodeItem(n, expanded_paths=frozenset({"N.Out"}))
    # 부모와 자식 모두 RIGHT — 좌측 dot 0개, 우측 3개(부모+2자식)
    assert _dots_on_side(item, 100, left=True) == 0
    assert _dots_on_side(item, 100, left=False) >= 2   # subpin 최소 2 (parent has_dot=False when expanded)


def test_input_unchanged(qtbot) -> None:
    n = Node(name="N", cls="T",
             pins=[Pin(name="In", cpp_type="bool", direction="Input")])
    item = NodeItem(n)
    assert _dots_on_side(item, 100, left=True) == 1


def test_hidden_pin_label_muted(qtbot) -> None:
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    n = Node(name="N", cls="T",
             pins=[Pin(name="Cfg", cpp_type="bool", direction="Hidden")])
    item = NodeItem(n)
    # 라벨 'Cfg'의 brush 색이 muted (#969696 또는 그 근사)
    label = next(c for c in item.childItems()
                 if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "Cfg")
    color = label.brush().color()
    # 일반 라벨(#D2D2D2)보다 어두움
    assert color.lightness() < 180
```

- [ ] **Step 2: PinRow + collect_pin_rows 확장**

`items.py`:

```python
@dataclass(frozen=True)
class PinRow:
    pin: Pin
    path: str
    depth: int
    has_dot: bool
    has_children: bool = False
    effective_direction: str = ""   # 정규화된 방향 ("input"/"output"/"io"/"hidden"/"")


def _normalize_direction(raw: str | None) -> str:
    return (raw or "").strip().lower()


def collect_pin_rows(
    node: Node,
    *,
    connected_subtree: frozenset[str],
    connected_only: bool,
    expanded: frozenset[str],
) -> list[PinRow]:
    rows: list[PinRow] = []

    def walk(pin: Pin, path: str, depth: int, parent_dir: str) -> bool:
        my_dir = _normalize_direction(pin.direction)
        if not my_dir:
            my_dir = parent_dir
        include_self = (not connected_only) or (path in connected_subtree)
        my_idx: int | None = None
        if include_self:
            my_idx = len(rows)
            rows.append(PinRow(pin=pin, path=path, depth=depth, has_dot=True,
                               has_children=bool(pin.subpins),
                               effective_direction=my_dir))
        children_added = False
        if path in expanded:
            for sp in pin.subpins:
                child_path = f"{path}.{sp.name}"
                if walk(sp, child_path, depth + 1, my_dir):
                    children_added = True
        if my_idx is not None and children_added:
            cur = rows[my_idx]
            rows[my_idx] = PinRow(pin=cur.pin, path=cur.path,
                                  depth=cur.depth, has_dot=False,
                                  has_children=cur.has_children,
                                  effective_direction=cur.effective_direction)
        return include_self or children_added

    for pin in node.pins:
        walk(pin, f"{node.name}.{pin.name}", 0, "")
    return rows
```

- [ ] **Step 3: NodeItem 렌더링 분기**

`NodeItem.__init__` 내 핀 행 처리 부분 갱신. `is_input` 단일 boolean 대신 `effective_direction` 사용:

```python
for i, row in enumerate(rows):
    cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
    self._rows[row.path] = cy
    direction = row.effective_direction
    is_hidden = direction == "hidden"
    is_io = direction == "io"
    is_output = direction == "output"
    # 라벨 색
    label_color = QColor(150, 150, 150) if is_hidden else QColor(210, 210, 210)
    # dot 생성
    if row.has_dot and not is_hidden:
        def _make_dot(mx: float) -> QGraphicsEllipseItem:
            dot = QGraphicsEllipseItem(
                mx - PIN_RADIUS, cy - PIN_RADIUS,
                2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
            if pin_colors is not None:
                resolved = pin_colors.resolve(row.pin.cpp_type)
                dot.setBrush(QBrush(resolved.color))
                if resolved.is_array:
                    dot.setPen(QPen(QColor(40, 40, 40), 1.5))
                else:
                    dot.setPen(QPen(Qt.NoPen))
            else:
                dot.setBrush(QBrush(QColor(200, 200, 120)))
                dot.setPen(QPen(Qt.NoPen))
            return dot
        if is_output:
            _make_dot(NODE_WIDTH)
        elif is_io:
            _make_dot(0.0)
            _make_dot(NODE_WIDTH)
        else:
            _make_dot(0.0)
    # 라벨/disclosure 들여쓰기 — 기존 로직 유지
    is_input_side = not is_output and not is_io
    indent = 18 + row.depth * 12
    # ... arrow zone + label 위치 (기존 로직) ...
    label_text = row.pin.name
    if row.pin.variable_source:
        label_text = f"{row.pin.name} (var: {row.pin.variable_source})"
    label = QGraphicsSimpleTextItem(label_text, self)
    label.setBrush(QBrush(label_color))
    if is_input_side:
        lx = indent
    else:
        lx = NODE_WIDTH - 8 - label.boundingRect().width()
        if row.has_children:
            lx -= 0  # arrow는 라벨과 반대편, 영향 없음
    label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)
```

(기존 라벨/arrow 좌표 로직과 통합 — `is_input` 대신 `is_input_side` 사용. arrow zone은 is_input_side 기준.)

- [ ] **Step 4: pin_anchor가 Hidden 핀 처리**

Hidden 핀은 dot 없으므로 link target이 될 수 없음. `pin_anchor`는 path만 보고 cy 반환 — Hidden 행도 _rows에 있으므로 정상 동작. 단 link가 Hidden 핀을 가리키는 경우는 데이터 모델상 없음 (Hidden은 설정 필드라 link 안 받음).

- [ ] **Step 5: 실행 — 통과 확인**

Run: `pytest tests/app/test_items_direction.py -v`
Expected: 5 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (기존 dot 개수 가정 테스트가 깨지면 갱신).

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_items_direction.py src/t3dgraph/core/app/items.py
git commit -m "fix(app): Hidden/IO/inheritance direction handling (F21)"
```

## 완료 후

F21 해소. F23 부수 효과(Hidden 사라져 가시 순서 정리). g4/g5 머지 시 rebase 협조.
