# batch ⑮ u8 — Sequence 노드 핀 처리 정정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Sequence 노드(`kind == "sequence"`)는 Pins(N) 권위 정렬 적용 제외 + 핀 라벨 숨김. T3D 원본 직렬 순서(= 실제 실행 의도) 보존.

**배경**:
- g14가 Pins(N)/SubPins(N) 권위 정렬 적용했으나 Sequence 케이스에서 역효과 — A/B 순서로 정렬됐는데 실제 실행 흐름은 B가 먼저(원본 T3D)
- Sequence 노드의 핀 이름(A, B, C)은 실행 흐름과 무관 — 라벨 표시가 오히려 혼란
- 사용자 의도: 시퀀스 핀은 그래프 연결 순서로 평가 (T3D 직렬 순서)

**Pre-condition:** master 최신.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (kind=="sequence" 면 Pins(N) skip) |
| `src/t3dgraph/core/app/items.py` | 수정 (kind=="sequence" 노드는 핀 라벨 숨김, dot만) |
| `tests/base/test_sequence_pin_order.py` | 신규 |
| `tests/app/test_sequence_label_hidden.py` | 신규 |

---

## Task 1: 인터프리터 — Sequence는 Pins(N) skip

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Create: `tests/base/test_sequence_pin_order.py`

- [ ] **Step 1: 테스트**

```python
"""u8 Task 1 — Sequence 노드는 Pins(N) 정렬 적용 안 함."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_sequence_node_preserves_t3d_order() -> None:
    """Sequence는 T3D 직렬(B, A) 순서 그대로. Pins(N) 무시."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="Seq"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="ExecuteContext"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Name="Seq"\n'
        '      ResolvedFunctionName="RigVMFunction_Sequence::Execute"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'ExecuteContext\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '      Pins(2)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    seq = g.node_by_name("Seq")
    # 실행 핀 우선 정렬 적용 후 — ExecuteContext 첫째, 그 다음 B, A (T3D 원본)
    pin_names = [p.name for p in seq.pins]
    # ExecuteContext가 첫 번째 (실행 핀 우선)
    assert pin_names[0] == "ExecuteContext"
    # 그 다음 B, A 순서 (Pins(N) 무시)
    assert pin_names[1:] == ["B", "A"], (
        f"Sequence가 Pins(N) 정렬 적용됨 — pin_names={pin_names}"
    )


def test_non_sequence_node_uses_pins_n() -> None:
    """일반 노드는 g14 동작 그대로 — Pins(N) 적용."""
    src = (
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="Regular"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="ExecuteContext"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="B"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="A"\n'
        '   End Object\n'
        '   Begin Object Name="Regular"\n'
        '      ResolvedFunctionName="RigVMFunction_Add::Execute"\n'
        '      Pins(0)="/Script/RigVMDeveloper.RigVMPin\'ExecuteContext\'"\n'
        '      Pins(1)="/Script/RigVMDeveloper.RigVMPin\'A\'"\n'
        '      Pins(2)="/Script/RigVMDeveloper.RigVMPin\'B\'"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    reg = g.node_by_name("Regular")
    pin_names = [p.name for p in reg.pins]
    # 일반 노드 — Pins(N) 적용
    assert pin_names == ["ExecuteContext", "A", "B"]
```

- [ ] **Step 2: 인터프리터 수정**

`src/t3dgraph/plugins/rigvm/interpreter.py` `_add_node`:

```python
def _add_node(self, obj, g, *, diagnostics, depth=0, max_depth=64):
    summary, category = role_for(obj)
    raw_pins = [_build_pin(c) for c in obj.children
                if t.is_pin_class(c.cls) or c.cls is None]
    
    # 노드 kind 미리 결정 (Sequence 등 특수 케이스 검사용)
    node_kind = _classify_kind(obj)
    
    # Sequence 노드는 Pins(N) 권위 정렬 skip — T3D 원본 순서 보존
    if node_kind != "sequence":
        pin_order = _read_ordered_pin_names(obj, "Pins")
        if pin_order is not None:
            raw_pins = _reorder_by_names(raw_pins, pin_order)
    
    sorted_pins = _sort_pins_exec_first(raw_pins)
    node = Node(
        ...,
        kind=node_kind,
        pins=sorted_pins,
        ...,
    )
```

(이미 `kind=_classify_kind(obj)` 호출 두 번이면 한 번으로 통합.)

- [ ] **Step 3: 실행 + 회귀**

Run: `pytest tests/base/test_sequence_pin_order.py -v`
Expected: 2 passed.

Run: `pytest tests -v`
Expected: 전체 통과. g14의 다른 테스트는 영향 없음 (그들은 kind != sequence).

- [ ] **Step 4: 커밋**

```bash
git add tests/base/test_sequence_pin_order.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "fix(rigvm): Sequence nodes skip Pins(N) — preserve T3D execution order (u8)"
```

---

## Task 2: NodeItem — Sequence 노드 핀 라벨 숨김

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Create: `tests/app/test_sequence_label_hidden.py`

- [ ] **Step 1: 테스트**

```python
"""u8 Task 2 — Sequence kind 노드는 핀 라벨 숨김."""
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _all_text_items(item):
    return [c for c in item.childItems() if isinstance(c, QGraphicsSimpleTextItem)]


def test_sequence_node_hides_pin_labels(qtbot) -> None:
    n = Node(
        name="Seq",
        cls="X",
        kind="sequence",
        pins=[
            Pin(name="ExecuteContext", cpp_type="FRigVMExecuteContext",
                direction="IO", is_execution=True),
            Pin(name="A", cpp_type="FRigVMExecuteContext",
                direction="Output", is_execution=True),
            Pin(name="B", cpp_type="FRigVMExecuteContext",
                direction="Output", is_execution=True),
        ],
    )
    item = NodeItem(n)
    texts = [t.text() for t in _all_text_items(item)]
    # 핀 이름 A·B는 표시 안 됨
    assert "A" not in texts
    assert "B" not in texts
    # 헤더 또는 다른 텍스트는 보일 수 있음 (Seq 이름 등)


def test_non_sequence_node_shows_pin_labels(qtbot) -> None:
    """sequence 외 노드는 라벨 그대로 표시 (회귀 없음)."""
    n = Node(
        name="Regular",
        cls="X",
        kind="node",
        pins=[Pin(name="DataIn", cpp_type="float", direction="Input")],
    )
    item = NodeItem(n)
    texts = [t.text() for t in _all_text_items(item)]
    assert "DataIn" in texts
```

- [ ] **Step 2: NodeItem 변경**

`src/t3dgraph/core/app/items.py` NodeItem 핀 행 라벨 그리기 부분:

```python
# 라벨 생성 전 — sequence 노드는 라벨 생략
is_sequence = self.node.kind == "sequence"
if not is_sequence:
    label_text = row.pin.name
    if row.pin.variable_source:
        label_text = f"{row.pin.name} (var: {row.pin.variable_source})"
    label = QGraphicsSimpleTextItem(label_text, self)
    label.setBrush(QBrush(label_color))
    # bold 적용 (기존 u6)
    ...
    # 위치 설정
    ...
# sequence면 라벨 생성 안 함, dot만 표시
```

(arrow_zones 등록도 라벨 의존이면 생략 처리.)

- [ ] **Step 3: 실행 + 회귀**

Run: `pytest tests/app/test_sequence_label_hidden.py -v`
Expected: 2 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 함수 그래프 진입 → RigVMFunction_Sequence 노드 — 핀 라벨(A, B 등) 사라지고 dot만 표시. 연결선은 그대로 — 사용자가 그래프 흐름만으로 평가.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_sequence_label_hidden.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): hide pin labels on Sequence nodes — graph flow only (u8)"
```

## 완료 후

Sequence 노드 정상화. T3D 원본 순서 보존(실행 흐름 일치) + 라벨 숨김(혼란 제거).
