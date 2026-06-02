# batch ⑮ u6 — 수정된 핀 라벨 굵게 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 핀이 연결되었거나 default 값에서 변경된 경우 라벨을 굵은 글씨(`font.setBold(True)`)로 표시. 토글 OFF 상태에서도 항상 적용 — 사용자가 한눈에 의미 있는 핀 파악.

**Pre-condition:** u5 머지 완료 (NodeItem이 `changed_paths` 받음).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (NodeItem 라벨 그리기 시 bold 조건 확장) |
| `tests/app/test_modified_pin_bold.py` | 신규 |

---

## Task 1: bold 적용

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_modified_pin_bold.py`

- [ ] **Step 1: 테스트**

```python
"""u6 — 수정된 핀 라벨 bold 표시."""
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _label_for(item, pin_name):
    for c in item.childItems():
        if isinstance(c, QGraphicsSimpleTextItem) and c.text().startswith(pin_name):
            return c
    return None


def test_connected_pin_label_bold(qtbot) -> None:
    n = Node(name="N", cls="X",
             pins=[Pin(name="ConnectedPin", cpp_type="float",
                       direction="Input")])
    item = NodeItem(n, connected_paths=frozenset({"N.ConnectedPin"}))
    label = _label_for(item, "ConnectedPin")
    assert label is not None
    assert label.font().bold() is True


def test_changed_pin_label_bold(qtbot) -> None:
    n = Node(name="N", cls="X",
             pins=[Pin(name="ChangedPin", cpp_type="float",
                       direction="Input", default_value="42.5")])
    item = NodeItem(n, changed_paths=frozenset({"N.ChangedPin"}))
    label = _label_for(item, "ChangedPin")
    assert label is not None
    assert label.font().bold() is True


def test_unchanged_unconnected_pin_label_not_bold(qtbot) -> None:
    n = Node(name="N", cls="X",
             pins=[Pin(name="DefaultPin", cpp_type="float",
                       direction="Input", default_value="0.0")])
    item = NodeItem(n)
    label = _label_for(item, "DefaultPin")
    assert label is not None
    assert label.font().bold() is False


def test_exec_pin_still_bold(qtbot) -> None:
    """exec 핀은 기존대로 bold (F26 회귀 없음)."""
    n = Node(name="N", cls="X",
             pins=[Pin(name="Exec", cpp_type="FRigVMExecuteContext",
                       direction="Output", is_execution=True)])
    item = NodeItem(n)
    label = _label_for(item, "Exec")
    assert label is not None
    assert label.font().bold() is True
```

- [ ] **Step 2: 구현**

`src/t3dgraph/core/app/items.py` `NodeItem.__init__` 라벨 그리기 부분:

```python
# 기존 라벨 생성
label = QGraphicsSimpleTextItem(label_text, self)
label.setBrush(QBrush(label_color))

# bold 조건 확장 (exec + connected + changed)
font = label.font()
is_modified = (row.path in connected_paths) or (row.path in changed_paths)
if row.pin.is_execution or is_modified:
    font.setBold(True)
    label.setFont(font)
```

`changed_paths`는 u5에서 도입된 NodeItem 생성자 인자. 디폴트 `frozenset()`.

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_modified_pin_bold.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과. F26 exec bold 테스트 회귀 없음.

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 샘플 — 연결된 핀과 default 변경된 핀 라벨이 굵게. 토글 OFF 상태에서도 적용.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_modified_pin_bold.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): bold label for connected OR changed pins (u6)"
```

## 완료 후

수정된 핀이 한눈에 식별됨. exec 핀 bold(F26) + 수정 핀 bold(u6) 일관 시각화.
