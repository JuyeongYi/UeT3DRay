# batch ⑭ k3 — layout_hint 처리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** NodeStyleProfile.layout_hint = `outputs_only`/`inputs_only`/`passthrough` 시 NodeItem 핀 배치 조정. Entry(outputs_only)·Return(inputs_only)·Reroute(passthrough) 시각 최적화.

**Spec:** §7

**Pre-condition:** k2 머지 완료 (NodeItem이 profile 받음).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (NodeItem `_resolve_input_side` helper + 렌더 분기) |
| `tests/app/test_layout_hint.py` | 신규 |

---

## Task 1: layout_hint 기반 핀 배치

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_layout_hint.py`

- [ ] **Step 1: 테스트**

```python
"""k3 (batch ⑭) — NodeItem layout_hint 처리."""
from PySide6.QtWidgets import QGraphicsEllipseItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.app.node_profiles import NodeStyleProfile


def _dots_x(item: NodeItem) -> list[float]:
    return sorted(c.rect().center().x()
                  for c in item.childItems()
                  if isinstance(c, QGraphicsEllipseItem))


def test_outputs_only_puts_all_pins_right(qtbot) -> None:
    n = Node(name="Entry", cls="X",
             pins=[Pin(name="A", cpp_type="float", direction="Output"),
                   Pin(name="B", cpp_type="float", direction="Input"),
                   Pin(name="C", cpp_type="float", direction="Hidden")])
    profile = NodeStyleProfile(layout_hint="outputs_only")
    item = NodeItem(n, profile=profile)
    xs = _dots_x(item)
    # Hidden 핀은 dot 없음, A/B 모두 우측
    assert all(x > 50 for x in xs)   # 우측(NODE_WIDTH 근처)


def test_inputs_only_puts_all_pins_left(qtbot) -> None:
    n = Node(name="Return", cls="X",
             pins=[Pin(name="A", cpp_type="float", direction="Output"),
                   Pin(name="B", cpp_type="float", direction="Input")])
    profile = NodeStyleProfile(layout_hint="inputs_only")
    item = NodeItem(n, profile=profile)
    xs = _dots_x(item)
    # 모두 좌측
    assert all(x < 50 for x in xs)


def test_default_unchanged(qtbot) -> None:
    """default hint는 기존 동작 (direction에 따라 분리)."""
    n = Node(name="N", cls="X",
             pins=[Pin(name="A", cpp_type="float", direction="Output"),
                   Pin(name="B", cpp_type="float", direction="Input")])
    profile = NodeStyleProfile()   # default
    item = NodeItem(n, profile=profile)
    xs = _dots_x(item)
    # 둘로 분리 — 하나는 좌, 하나는 우
    assert len(xs) == 2
    assert xs[0] < 50 and xs[1] > 50


def test_passthrough_single_row(qtbot) -> None:
    """passthrough — 라벨 한 줄, 최소 폭. 핀 한 쌍만 표시."""
    n = Node(name="Reroute", cls="X",
             pins=[Pin(name="In", cpp_type="float", direction="Input"),
                   Pin(name="Out", cpp_type="float", direction="Output")])
    profile = NodeStyleProfile(layout_hint="passthrough")
    item = NodeItem(n, profile=profile)
    # 노드 높이가 단일 행 수준 (HEADER + ROW_HEIGHT 정도)
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT
    assert item.rect().height() <= HEADER_HEIGHT + ROW_HEIGHT + 5
```

- [ ] **Step 2: 구현**

`src/t3dgraph/core/app/items.py` NodeItem 내 `_resolve_input_side` 헬퍼 추가:

```python
def _resolve_input_side(self, row_direction: str) -> bool:
    """layout_hint 적용해 핀 행이 left side에 그려질지 결정."""
    hint = self._profile.layout_hint
    if hint == "outputs_only":
        return False
    if hint == "inputs_only":
        return True
    # default / passthrough → direction 기준
    return row_direction != "output" and row_direction != "io"
    # IO는 양쪽 — _resolve_input_side는 IO에 대해 False 반환 (우측 처리하고 IO 분기 별도)
```

기존 `is_input` 계산을 `_resolve_input_side`로 교체. 단 IO 핀은 양쪽 그리는 케이스이므로 별도 분기 유지.

passthrough 처리:
- `__init__`에서 hint == "passthrough"면 rows를 첫 input + 첫 output만 사용해 단일 행으로 합치기

```python
if self._profile.layout_hint == "passthrough":
    # passthrough — 첫 input + 첫 output을 한 행으로
    # 단순화: rows 자체를 1행으로 축소(input dot + output dot 양쪽, 라벨 중앙)
    # 또는 별도 _render_passthrough 메서드
    self._render_passthrough(node)
    return
```

(passthrough 정확한 시각은 별도 메서드. 단일 행에 좌·우 dot + 라벨 "→".)

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_layout_hint.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과. 기존 NodeItem 테스트(g1 등)가 default profile로 동작.

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

함수 그래프 진입 시:
- Entry 노드 — 핀 모두 우측 (outputs_only)
- Return 노드 — 핀 모두 좌측 (inputs_only)
- Reroute 노드 — 단일 행 패스스루

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_layout_hint.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem layout_hint — outputs_only/inputs_only/passthrough (k3)"
```

## 완료 후

layout_hint 처리 완료. batch ⑭ 마감 후보. 사용자 노드 추가는 TOML 한 줄로 완성. 향후 분기 → 새 profile 필드 추가만으로 확장.
