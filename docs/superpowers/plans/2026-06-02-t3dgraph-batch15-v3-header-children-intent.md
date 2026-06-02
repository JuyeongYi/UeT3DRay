# batch ⑮ v3 — _header_children 의도 명시 + _add_row_item invariant 강제 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** v2-B1 improver findings 2건 정리.

- **v2B1-A1**: `_header_children`가 append만 되고 read 없음 — 다음 리팩터에서 dead code로 정리될 위험. 클래스 docstring + 리스트 자체 docstring 한 줄로 의도(헤더 invariant 추적·향후 헤더 일괄 조작 hook 자리) 명시
- **v2B1-B1**: `_add_row_item`이 wrapper 한 줄 — 실제 invariant 강제 없음. `assert gitem.parentItem() is self` 한 줄로 precondition 검증

**Pre-condition:** master `877c570`, 644 tests (v2-A1+B1 머지 반영).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (docstring + assert) |
| `tests/app/test_nodeitem_invariants.py` | 수정 (assert 위반 테스트) |

---

## Task 1: A1 — _header_children docstring 명시

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 클래스 docstring에 항목 추가**

`NodeItem` 클래스 docstring "상태 invariant" 절에 추가:

```python
        - `_header_children` : list[QGraphicsItem]
            header 영역(title·chevron·var badge) 아이템 추적. `_clear_rows`에서
            제거되지 않는 것을 명시하기 위한 invariant 마커. 향후 헤더 일괄 조작
            (예: 헤더 hide·opacity 토글)이 추가되면 이 리스트를 iterate 한다.
        - `_row_children` : list[QGraphicsItem]
            행 영역(dot·arrow·label) 아이템. `_clear_rows`의 청소 대상.
            추가는 반드시 `_add_row_item()` 통로로.
```

- [ ] **Step 2: `_header_children` 선언부 한 줄 주석**

```python
        # header 영역 아이템 (title·chevron·badge) — _clear_rows 제외 대상
        self._header_children: list[QGraphicsItem] = []
        # 행 영역 아이템 (dot·arrow·label) — _add_row_item 통해서만 등록
        self._row_children: list[QGraphicsItem] = []
```

- [ ] **Step 3: 실행**

Run: `pytest tests -v`
Expected: 전체 644 통과 (변경 없음 — docstring만).

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/app/items.py
git commit -m "docs(app): document _header_children intent + _row_children invariant (v3-A1)"
```

---

## Task 2: B1 — _add_row_item parentItem assert

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `tests/app/test_nodeitem_invariants.py`

- [ ] **Step 1: 테스트**

`tests/app/test_nodeitem_invariants.py`에 추가:

```python
def test_add_row_item_rejects_foreign_parent(qtbot) -> None:
    """parentItem이 self 아닌 graphics item을 _add_row_item에 넘기면 assert."""
    from PySide6.QtWidgets import QGraphicsEllipseItem
    from t3dgraph.core.base.graph_model import Node, Pin
    from t3dgraph.core.app.items import NodeItem
    n = Node(name="N", cls="X", pins=[Pin(name="P", cpp_type="float")])
    item = NodeItem(n)
    # 다른 parent — 부모 미설정
    rogue = QGraphicsEllipseItem(0, 0, 4, 4)   # parent=None
    import pytest
    with pytest.raises(AssertionError):
        item._add_row_item(rogue)


def test_add_row_item_accepts_self_parent(qtbot) -> None:
    """parentItem이 self면 통과."""
    from PySide6.QtWidgets import QGraphicsEllipseItem
    from t3dgraph.core.base.graph_model import Node, Pin
    from t3dgraph.core.app.items import NodeItem
    n = Node(name="N", cls="X", pins=[Pin(name="P", cpp_type="float")])
    item = NodeItem(n)
    legit = QGraphicsEllipseItem(0, 0, 4, 4, item)   # parent=item
    item._add_row_item(legit)
    assert legit in item._row_children
```

- [ ] **Step 2: `_add_row_item` 본문 강화**

```python
    def _add_row_item(self, gitem: QGraphicsItem) -> None:
        """행 전용 그래픽 아이템 등록. _clear_rows의 청소 대상.

        Precondition: `gitem.parentItem() is self` (행 아이템은 NodeItem의 자식).
        """
        assert gitem.parentItem() is self, (
            "row item must be child of NodeItem")
        self._row_children.append(gitem)
```

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_nodeitem_invariants.py -v`
Expected: 기존 6 + 신규 2 = 8 passed.

Run: `pytest tests -v`
Expected: 전체 646 통과.

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_nodeitem_invariants.py src/t3dgraph/core/app/items.py
git commit -m "refactor(app): assert _add_row_item parentItem invariant (v3-B1)"
```

---

## 무엇이 깨질 수 있나

| 위험 | 완화 |
|---|---|
| 기존 `_add_row_item` 호출 중 parent 미설정 케이스 있으면 assert 폭발 | 현재 _install_rows의 dot/arrow/label은 모두 `self`를 parent로 생성 — 회귀 없음. 전체 테스트로 검증 |
| assert가 production에서 비활성(`python -O`)이면 invariant 무의미 | 본 프로젝트는 `-O` 미사용 — assert는 항상 활성 |

## 완료 후

- `_header_children` 의도가 코드에서 자기 설명적 — 다음 리팩터러가 dead code로 오인하지 않음
- `_add_row_item` 호출 실수가 즉시 발견 (test 통과 시 잘못된 parent 영구 방지)
