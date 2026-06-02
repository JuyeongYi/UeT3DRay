# batch ⑮ v2 — NodeItem cached state invariants + header/row 분리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** w1-C improver findings 2건 정리.

- **w1C-A1**: `NodeItem`이 캐시한 `_connected_paths`·`_changed_paths`·`_pin_colors` 무효화 경로 명시 — invariant docstring + `update_state(...)` setter (향후 partial-update API 대비)
- **w1C-B1**: `_row_children` "행 전용" invariant 강제 — `_header_children` 별도 분리 + `_add_row_item(item)` 헬퍼, 헤더/배지/chevron 신규 추가자가 실수로 행 청소에 휘말리지 않도록 패턴 보호

**Pre-condition:** master `cc3ad78`, 639 tests.

C1(애니메이션)은 후순위 — 별도 시각 슬라이스에서 처리.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (Task 1: docstring + update_state / Task 2: _header_children + _add_row_item) |
| `tests/app/test_nodeitem_invariants.py` | 신규 |

---

## Task 1: A1 — cached state invariant + update_state setter

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_nodeitem_invariants.py`

- [ ] **Step 1: 테스트**

```python
"""v2-A1 — NodeItem cached state setter."""
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def test_update_state_changes_subsequent_rebuild(qtbot) -> None:
    """update_state() 후 set_expanded_paths()가 새 connected/changed set으로 재구성."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    item = NodeItem(n)   # 기본 빈 set
    # 펼치기
    item.set_expanded_paths(frozenset({"N.Pos"}))
    # 이 시점에 N.Pos.X 행은 bold 처리 안 됨 (changed_paths 비어있음)
    # update_state로 changed_paths 갱신
    item.update_state(connected_paths=frozenset(),
                      changed_paths=frozenset({"N.Pos.X"}),
                      pin_colors=None)
    # set_expanded_paths 다시 호출 — 새 changed_paths 반영
    item.set_expanded_paths(frozenset({"N.Pos"}))
    # N.Pos.X 행의 라벨이 bold (changed 표시) — 직접 검증
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    bold_labels = [
        c.text() for c in item.childItems()
        if isinstance(c, QGraphicsSimpleTextItem) and c.font().bold()
    ]
    assert "X" in bold_labels or any(
        "X" in t for t in bold_labels
    ), f"changed_paths setter 효과 없음 — bold_labels={bold_labels}"


def test_update_state_no_op_when_unchanged(qtbot) -> None:
    """동일 set/색 재호출은 변화 없음 (idempotent)."""
    n = Node(name="N", cls="X", pins=[Pin(name="P", cpp_type="float")])
    item = NodeItem(n)
    cnt_before = len(item.childItems())
    item.update_state(connected_paths=frozenset(),
                      changed_paths=frozenset(),
                      pin_colors=None)
    # update_state 자체는 caches만 갱신, install 안 함
    assert len(item.childItems()) == cnt_before
```

- [ ] **Step 2: NodeItem.update_state + docstring**

`src/t3dgraph/core/app/items.py` `NodeItem` 클래스 docstring에 invariant 명시:

```python
class NodeItem(QGraphicsRectItem):
    """그래프 노드 시각 요소.

    **상태 invariant** — 다음 인스턴스 캐시는 `__init__` 또는 `update_state()`로만
    갱신되어야 한다. populate() 외 경로(partial-update API 등)가 추가되면
    그 호출자가 `update_state()`로 갱신을 명시해야 in-place rebuild가 stale
    렌더링을 피한다:
        - `_connected_paths` : frozenset[str]
        - `_changed_paths`   : frozenset[str]
        - `_connected_only`  : bool
        - `_pin_colors`      : PinColorTable | None

    `_expanded_paths`는 `set_expanded_paths()`로 갱신된다 (그 자체가 rebuild 트리거).
    """
```

`update_state` 메서드 추가:

```python
    def update_state(self, *,
                     connected_paths: frozenset[str] | None = None,
                     changed_paths: frozenset[str] | None = None,
                     connected_only: bool | None = None,
                     pin_colors: "PinColorTable | None" = None) -> None:
        """캐시된 렌더 상태 setter. 호출자는 이후 set_expanded_paths()로
        rebuild를 명시적으로 트리거해야 한다 (이 setter는 install 안 함)."""
        if connected_paths is not None:
            self._connected_paths = connected_paths
        if changed_paths is not None:
            self._changed_paths = changed_paths
        if connected_only is not None:
            self._connected_only = connected_only
        if pin_colors is not None:
            self._pin_colors = pin_colors
```

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_nodeitem_invariants.py -v`
Expected: 2 passed.

Run: `pytest tests -v`
Expected: 전체 641 통과.

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_nodeitem_invariants.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem.update_state setter + cached state invariant (v2-A1)"
```

---

## Task 2: B1 — _header_children 분리 + _add_row_item 헬퍼

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `tests/app/test_nodeitem_invariants.py`

- [ ] **Step 1: 테스트**

`tests/app/test_nodeitem_invariants.py`에 추가:

```python
def test_header_children_not_cleared_on_rebuild(qtbot) -> None:
    """헤더 영역(title·chevron·badge)은 set_expanded_paths로 사라지지 않는다."""
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    # subgraph 있는 노드 — chevron 렌더
    n = Node(name="N", cls="X.RigVMCollapseNode",
             pins=[parent], subgraph="dummy")
    item = NodeItem(n)
    headers_before = list(item._header_children)
    item.set_expanded_paths(frozenset({"N.Pos"}))
    headers_after = list(item._header_children)
    # 헤더 자식은 동일성 유지 (제거·재생성 없음)
    assert headers_before == headers_after
    # 모두 살아있는지 — text 호출이 RuntimeError 안 던짐
    for h in headers_after:
        if isinstance(h, QGraphicsSimpleTextItem):
            _ = h.text()


def test_row_children_replaced_on_rebuild(qtbot) -> None:
    """행 자식만 _clear_rows로 제거 + 새 _install_rows."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    item = NodeItem(n)
    rows_before = list(item._row_children)
    item.set_expanded_paths(frozenset({"N.Pos"}))
    rows_after = list(item._row_children)
    # 행 자식은 갈아끼움 — 동일 객체 없음
    assert not any(r in rows_before for r in rows_after)
    # 자식 수는 펼친 후 더 많음 (N.Pos.X 행 추가)
    assert len(rows_after) > len(rows_before)
```

- [ ] **Step 2: items.py 분리**

`NodeItem.__init__`:

```python
        self._row_children: list[QGraphicsItem] = []
        self._header_children: list[QGraphicsItem] = []
```

기존 `__init__`의 헤더·title·chevron·var badge 생성 부분에 `_header_children.append(...)` 추가:

```python
        title = QGraphicsSimpleTextItem(node.display_name or node.name or "?", self)
        title.setBrush(QBrush(QColor(235, 235, 235)))
        title.setPos(6, 5)
        self._header_children.append(title)
        ...
        # chevron 생성 시
        chev = QGraphicsSimpleTextItem("▶", self)
        ...
        self._header_children.append(chev)
        ...
        # var badge 생성 시
        badge_bg = QGraphicsRectItem(...)
        ...
        self._header_children.append(badge_bg)
        badge_text = QGraphicsSimpleTextItem("var", self)
        ...
        self._header_children.append(badge_text)
```

`_install_rows` 안에서 모든 행 dot/arrow/label 생성을 `self._add_row_item(item)`로 통과:

```python
    def _add_row_item(self, gitem: QGraphicsItem) -> None:
        """행 전용 그래픽 아이템 등록. _clear_rows의 청소 대상."""
        self._row_children.append(gitem)
```

`_install_rows` 본문에서:

```python
                dot = QGraphicsEllipseItem(...)
                ...
                self._add_row_item(dot)
                ...
                arrow = QGraphicsSimpleTextItem(arrow_char, self)
                ...
                self._add_row_item(arrow)
                ...
                label = QGraphicsSimpleTextItem(label_text, self)
                ...
                self._add_row_item(label)
```

(기존 `self._row_children.append(...)` 호출이 있었다면 모두 `_add_row_item`으로 교체.)

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_nodeitem_invariants.py -v`
Expected: 4 passed (Task 1 + Task 2).

Run: `pytest tests -v`
Expected: 전체 643 통과.

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_nodeitem_invariants.py src/t3dgraph/core/app/items.py
git commit -m "refactor(app): separate _header_children + _add_row_item helper (v2-B1)"
```

---

## 무엇이 깨질 수 있나

| 위험 | 완화 |
|---|---|
| `_add_row_item` 누락 시 신규 행 graphics가 `_clear_rows`에서 빠짐 → 다음 rebuild 시 잔여 | Step 2 자체가 모든 행 객체에 헬퍼 적용; 회귀 테스트로 `_row_children` 카운트 검증 |
| `update_state` 호출자 부재로 dead code 우려 | invariant docstring으로 호출 시점(향후 partial-update API) 명시 — YAGNI 수준의 최소 setter |
| 헤더 자식이 `_header_children`에 빠지면 추적 누락 | 현재는 테스트에서 chevron/title 살아있음만 검증; 모든 헤더 항목 register는 코드 리뷰 책임 |

## 완료 후

- 향후 partial-update API 추가 시 update_state 호출 한 줄로 in-place rebuild 일관성 보장
- 헤더 vs 행 자식 invariant 강제 — 신규 시각 요소 추가자가 헬퍼만 따라가면 안전
