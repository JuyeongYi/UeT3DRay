# batch ⑨ φ (phi) — Variable Display (F16) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RigVMVariableNode를 식별 가능한 배지로 그리고(헤더 우측), 변수 출력에서 링크된 소비 핀에 `← var: Name` 인라인 표시 + 핀 라벨 prefix를 추가한다. 팔레트(`pin_colors.toml`)에 `variable` 엔트리도 추가.

**Architecture:** `Pin.variable_source: str | None` 메타를 도입, 인터프리터 사후 처리(`_annotate_variable_consumers`)로 채움. NodeItem이 헤더에서 `RigVMVariableNode` 검사 + 핀 행에서 `pin.variable_source` 검사로 시각 표시. InspectorPanel은 기본값 컬럼에 `← var: Name` 접두.

**Tech Stack:** Python 3.11 dataclass, PySide6 (`QGraphicsSimpleTextItem`, `QGraphicsRectItem`), pytest + pytest-qt. 외부 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` §8

**Pre-condition:** master `bd34968`(또는 그 이후) 기준. Spec 1 μ 완료 — `pin_colors.toml`·`PinColorTable` 존재.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/base/graph_model.py` | 수정 (`Pin.variable_source` 추가) |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (`_annotate_variable_consumers` + `_locate_pin`) |
| `src/t3dgraph/core/app/resources/pin_colors.toml` | 수정 (`palette.variable` 엔트리) |
| `src/t3dgraph/core/app/items.py` | 수정 (변수 노드 배지, 핀 라벨 `var:` prefix) |
| `src/t3dgraph/core/app/inspector_panel.py` | 수정 (기본값 컬럼 `← var: Name` 접두) |
| `tests/base/test_variable_annotation.py` | 신규 |
| `tests/app/test_variable_visualization.py` | 신규 |

---

## Task 1: `Pin.variable_source` 필드 + `_annotate_variable_consumers`

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Create: `tests/base/test_variable_annotation.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/base/test_variable_annotation.py`:

```python
"""F16 — Pin.variable_source 부여 정확도."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import (
    GraphModel, Node, Pin, Link, VariableRef,
)
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_pin_has_variable_source_default_none() -> None:
    p = Pin(name="A", cpp_type="bool", direction="Input")
    assert p.variable_source is None


def test_annotate_simple_consumer() -> None:
    """VariableNode.Value → ConsumerNode.InputPin 링크면 InputPin에 var 이름 부여."""
    var_node = Node(name="V1", cls="/Script/RigVMDeveloper.RigVMVariableNode",
                    pins=[Pin(name="Variable", cpp_type=None, direction=None,
                              default_value="MyVar"),
                          Pin(name="Value", cpp_type="float", direction="Output")])
    consumer = Node(name="C1", cls="/Script/RigVMDeveloper.RigVMUnitNode",
                    pins=[Pin(name="A", cpp_type="float", direction="Input")])
    g = GraphModel(
        nodes=[var_node, consumer],
        links=[Link(source_path="V1.Value", target_path="C1.A")],
        variable_refs=[VariableRef(variable_name="MyVar",
                                   cpp_type="float", node_name="V1")],
    )
    RigVMGraphInterpreter()._annotate_variable_consumers(g)
    pin_a = next(p for p in consumer.pins if p.name == "A")
    assert pin_a.variable_source == "MyVar"


def test_annotate_sub_pin_consumer() -> None:
    """링크 대상이 sub-pin(struct field)이어도 그 sub-pin에 부여."""
    var_node = Node(name="V1", cls="/Script/RigVMDeveloper.RigVMVariableNode",
                    pins=[Pin(name="Variable", cpp_type=None, direction=None,
                              default_value="MyVar"),
                          Pin(name="Value", cpp_type="float", direction="Output")])
    sub_x = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="P", cpp_type="FVector", direction="Input", subpins=[sub_x])
    consumer = Node(name="C1", cls="/Script/RigVMDeveloper.RigVMUnitNode",
                    pins=[parent])
    g = GraphModel(
        nodes=[var_node, consumer],
        links=[Link(source_path="V1.Value", target_path="C1.P.X")],
        variable_refs=[VariableRef(variable_name="MyVar",
                                   cpp_type="float", node_name="V1")],
    )
    RigVMGraphInterpreter()._annotate_variable_consumers(g)
    assert parent.variable_source is None         # 부모 pin엔 부여 안 됨
    assert sub_x.variable_source == "MyVar"        # sub-pin에 부여


def test_annotate_recurses_into_subgraph() -> None:
    sub_var = Node(name="SV", cls="/Script/RigVMDeveloper.RigVMVariableNode",
                   pins=[Pin(name="Variable", cpp_type=None, direction=None,
                             default_value="SubVar"),
                         Pin(name="Value", cpp_type="bool", direction="Output")])
    sub_consumer = Node(name="SC", cls="/Script/RigVMDeveloper.RigVMUnitNode",
                        pins=[Pin(name="Flag", cpp_type="bool", direction="Input")])
    sub = GraphModel(
        nodes=[sub_var, sub_consumer],
        links=[Link(source_path="SV.Value", target_path="SC.Flag")],
        variable_refs=[VariableRef(variable_name="SubVar",
                                   cpp_type="bool", node_name="SV")],
    )
    parent_node = Node(name="P1", cls="/Script/RigVMDeveloper.RigVMCollapseNode",
                       pins=[], subgraph=sub)
    g = GraphModel(nodes=[parent_node])
    RigVMGraphInterpreter()._annotate_variable_consumers(g)
    flag = sub_consumer.pins[0]
    assert flag.variable_source == "SubVar"


def test_annotate_no_links_no_change() -> None:
    consumer = Node(name="C1", cls="X",
                    pins=[Pin(name="A", cpp_type="bool", direction="Input")])
    g = GraphModel(nodes=[consumer])
    RigVMGraphInterpreter()._annotate_variable_consumers(g)
    assert consumer.pins[0].variable_source is None
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_variable_annotation.py -v`
Expected: FAIL — `Pin.variable_source`·`_annotate_variable_consumers`/`_locate_pin` 미존재.

- [ ] **Step 3: `Pin.variable_source` 필드 추가**

`src/t3dgraph/core/base/graph_model.py` `Pin` 데이터클래스에 필드 추가 (`raw` 다음):

```python
@dataclass
class Pin:
    name: str
    cpp_type: str | None
    direction: str | None
    default_value: str | None = None
    is_execution: bool = False
    subpins: list["Pin"] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    variable_source: str | None = None    # F16: 이 핀이 var X의 출력에서 링크되면 X 이름
```

- [ ] **Step 4: 인터프리터에 `_annotate_variable_consumers` + `_locate_pin` 추가**

`src/t3dgraph/plugins/rigvm/interpreter.py`의 `RigVMGraphInterpreter`에 메서드 추가:

```python
def _annotate_variable_consumers(self, g: GraphModel) -> None:
    """variable_refs + links → 각 소비 핀에 variable_source 부여."""
    var_outputs: dict[str, str] = {}   # "VariableNode.Value" → variable_name
    for ref in g.variable_refs:
        var_outputs[f"{ref.node_name}.Value"] = ref.variable_name
    for link in g.links:
        var_name = var_outputs.get(link.source_path)
        if var_name is None:
            continue
        target_pin = self._locate_pin(g, link.target_path)
        if target_pin is not None:
            target_pin.variable_source = var_name
    # 재귀 — 서브그래프 자체에도 variable_refs/links가 있다
    for node in g.nodes:
        if node.subgraph is not None:
            self._annotate_variable_consumers(node.subgraph)
        for extra in node.extra_subgraphs:
            self._annotate_variable_consumers(extra)

def _locate_pin(self, g: GraphModel, path: str) -> Pin | None:
    """'NodeName.PinName[.SubPin...]' → Pin 객체. 없으면 None."""
    parts = path.split(".")
    if not parts:
        return None
    node = g.node_by_name(parts[0])
    if node is None:
        return None
    cur_pins = node.pins
    last: Pin | None = None
    for name in parts[1:]:
        pin = next((p for p in cur_pins if p.name == name), None)
        if pin is None:
            return None
        last = pin
        cur_pins = pin.subpins
    return last
```

`interpret()` 메서드 끝에 호출 추가 (π 슬라이스에서 `diagnostics` attach 후):

```python
def interpret(self, doc: T3DDocument) -> GraphModel:
    diag = InterpreterDiagnostics()
    g = self._interpret_objects(doc.objects, label=None, parent_node=None,
                                diagnostics=diag)
    g.diagnostics = diag
    self._annotate_variable_consumers(g)     # F16
    return g
```

(π 슬라이스가 먼저 머지 안 됐다면, `diagnostics` 부분은 본 슬라이스에선 추가하지 않고 단순히 기존 `interpret`에 `self._annotate_variable_consumers(g)` 한 줄만 추가. 머지 순서는 π → φ 또는 φ → π 무관 — 충돌 없음.)

- [ ] **Step 5: 실행 — 통과 확인**

Run: `pytest tests/base/test_variable_annotation.py -v`
Expected: 5 passed

- [ ] **Step 6: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과. 기존 `Pin` 인스턴스화 호출부가 `variable_source=`를 명시하지 않아도 디폴트 None.

- [ ] **Step 7: 커밋**

```bash
git add tests/base/test_variable_annotation.py src/t3dgraph/core/base/graph_model.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "feat(rigvm): Pin.variable_source + _annotate_variable_consumers (F16)"
```

---

## Task 2: 팔레트에 `variable` 색 추가

**Files:**
- Modify: `src/t3dgraph/core/app/resources/pin_colors.toml`

- [ ] **Step 1: TOML 갱신**

`src/t3dgraph/core/app/resources/pin_colors.toml`의 `[palette]` 섹션에 추가:

```toml
[palette]
exec     = "#FFFFFF"
bool     = "#A02020"
int      = "#1FBEB6"
float    = "#7AC74F"
name     = "#C68FE6"
string   = "#FF66FF"
struct   = "#5B8FF9"
object   = "#3F9CBE"
variable = "#9966FF"   # F16: 변수 노드 헤더·var-fed 핀 시각용
default  = "#C8C878"
```

(기존 키 순서 유지, `default` 위에 `variable` 끼움.)

- [ ] **Step 2: 단위 테스트 갱신**

`tests/app/test_pin_colors.py`에 추가:

```python
def test_palette_includes_variable_key(bundled_table: PinColorTable) -> None:
    """팔레트에 variable 색이 있어야 함 — F16 그리기에서 참조."""
    # 직접 노출되는 API가 없으므로 내부 palette dict 검사
    assert "variable" in bundled_table._palette
    assert bundled_table._palette["variable"].name().upper() == "#9966FF"
```

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_pin_colors.py -v`
Expected: 모든 기존 테스트 + 신규 1건 통과.

- [ ] **Step 4: 사용자 파일 카피 갱신 정책**

기존 사용자 `pin_colors.toml`이 있는 경우 `variable` 엔트리가 빠져 있을 수 있다. 런타임 `resolve()`는 cpp_type→bucket→palette 경로라 `variable` 키 누락이 직접 영향은 없다 (NodeItem이 별도로 참조). 다만 NodeItem 코드에서 `palette` 룩업 시 KeyError 방지를 위해 fallback 처리 — Task 3에서 다룸.

- [ ] **Step 5: 커밋**

```bash
git add src/t3dgraph/core/app/resources/pin_colors.toml tests/app/test_pin_colors.py
git commit -m "feat(app): pin_colors.toml — variable palette entry (F16)"
```

---

## Task 3: `NodeItem` — 변수 노드 배지 + 핀 라벨 prefix

**Files:**
- Create: `tests/app/test_variable_visualization.py`
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_variable_visualization.py`:

```python
"""F16 NodeItem — 변수 노드 배지 + 소비 핀 라벨 prefix."""
from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtWidgets import QGraphicsSimpleTextItem, QGraphicsRectItem

from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.app.pin_colors import PinColorTable


@pytest.fixture
def pin_colors(tmp_path, monkeypatch) -> PinColorTable:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    return PinColorTable.load()


def _texts(item: NodeItem) -> list[str]:
    return [c.text() for c in item.childItems()
            if isinstance(c, QGraphicsSimpleTextItem)]


def test_variable_node_has_var_badge(qtbot, pin_colors: PinColorTable) -> None:
    """RigVMVariableNode면 헤더에 'var' 텍스트 표시."""
    n = Node(name="V1", cls="/Script/RigVMDeveloper.RigVMVariableNode",
             pins=[Pin(name="Value", cpp_type="float", direction="Output")])
    item = NodeItem(n, pin_colors=pin_colors)
    assert "var" in _texts(item)


def test_non_variable_node_has_no_var_badge(qtbot, pin_colors: PinColorTable) -> None:
    n = Node(name="U1", cls="/Script/RigVMDeveloper.RigVMUnitNode",
             pins=[Pin(name="A", cpp_type="float", direction="Input")])
    item = NodeItem(n, pin_colors=pin_colors)
    assert "var" not in _texts(item)


def test_consumer_pin_label_has_var_prefix(qtbot, pin_colors: PinColorTable) -> None:
    """variable_source가 있는 핀의 라벨에 'var:' prefix."""
    n = Node(name="C1", cls="/Script/RigVMDeveloper.RigVMUnitNode",
             pins=[Pin(name="A", cpp_type="float", direction="Input",
                       variable_source="MyVar")])
    item = NodeItem(n, pin_colors=pin_colors)
    labels = _texts(item)
    # 핀 라벨이 'A (var: MyVar)' 형식이어야 함
    assert any("var: MyVar" in t for t in labels), (
        f"var prefix 누락 — labels={labels}"
    )


def test_normal_pin_label_no_prefix(qtbot, pin_colors: PinColorTable) -> None:
    n = Node(name="C1", cls="/Script/RigVMDeveloper.RigVMUnitNode",
             pins=[Pin(name="A", cpp_type="float", direction="Input")])
    item = NodeItem(n, pin_colors=pin_colors)
    labels = _texts(item)
    # 'A' 라벨 그대로
    assert any(t == "A" for t in labels), f"normal pin 라벨 변경됨 — {labels}"
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_variable_visualization.py -v`
Expected: FAIL — var 배지·prefix 미존재.

- [ ] **Step 3: `NodeItem` 변경**

`src/t3dgraph/core/app/items.py` `NodeItem.__init__` 본문에서 헤더 그리기 블록(`title`/`chev` 다음) 뒤에 변수 노드 배지 추가:

```python
# F16: 변수 노드 헤더 우측에 'var' 배지
if (node.cls or "").rsplit(".", 1)[-1] == "RigVMVariableNode":
    var_palette_color = QColor("#9966FF")
    if pin_colors is not None:
        var_palette_color = pin_colors._palette.get("variable", var_palette_color)
    badge_w, badge_h = 24.0, 14.0
    badge_x = NODE_WIDTH - badge_w - 6
    badge_y = (HEADER_HEIGHT - badge_h) / 2
    badge_bg = QGraphicsRectItem(badge_x, badge_y, badge_w, badge_h, self)
    badge_bg.setBrush(QBrush(var_palette_color))
    badge_bg.setPen(QPen(Qt.NoPen))
    badge_text = QGraphicsSimpleTextItem("var", self)
    badge_text.setBrush(QBrush(QColor(255, 255, 255)))
    badge_text.setPos(badge_x + 5, badge_y + 1)
```

(`QGraphicsRectItem` import 이미 있음. `QGraphicsSimpleTextItem`도 이미 있음.)

핀 라벨 렌더링에 `variable_source` prefix 적용. 기존 라벨 생성 줄:

```python
label = QGraphicsSimpleTextItem(row.pin.name, self)
```

다음으로 교체:

```python
label_text = row.pin.name
if row.pin.variable_source:
    label_text = f"{row.pin.name} (var: {row.pin.variable_source})"
label = QGraphicsSimpleTextItem(label_text, self)
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_variable_visualization.py -v`
Expected: 4 passed

- [ ] **Step 5: 회귀 확인**

Run: `pytest tests/app -v`
Expected: 전체 통과 (μ 의 핀 라벨 테스트도 — variable_source 없으면 prefix 없음).

만약 회귀: μ의 `test_arrow_zone_click_emits_toggle` 등이 라벨 좌표를 직접 검사하면 길어진 라벨로 broken 가능. `label.boundingRect().width()` 계산에 영향 — 출력 핀 (오른쪽 정렬)이 늘어진다. 보강 필요 시 prefix는 출력 핀에만, 입력 핀엔 prefix 없이 별도 표시 등 옵션. 다만 변수는 보통 input pin에 fed → 라벨 길이만 늘어남(기본 NODE_WIDTH=200 안에 들어가는지 확인). 너무 길면 truncation:

```python
if len(label_text) > 30:
    label_text = label_text[:27] + "…"
```

위 truncation은 spec에 없으므로 회귀 발생 시 추가, 없으면 건너뜀.

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_variable_visualization.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem variable badge + pin label var: prefix (F16)"
```

---

## Task 4: `InspectorPanel` — 기본값 컬럼에 `← var: Name` 접두

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py`

- [ ] **Step 1: 테스트 추가**

`tests/app/test_variable_visualization.py`에 추가:

```python
from t3dgraph.core.base.graph_model import GraphModel
from t3dgraph.core.app.inspector_panel import InspectorPanel


def test_inspector_default_column_prefixed_with_var(qtbot) -> None:
    consumer = Node(name="C1", cls="X",
                    pins=[Pin(name="A", cpp_type="float", direction="Input",
                              default_value="0.0", variable_source="MyVar")])
    g = GraphModel(nodes=[consumer])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(consumer, g)
    item = panel._items["C1.A"]
    # 기본값 컬럼(3)이 "← var: MyVar" 접두
    text = item.text(3)
    assert text.startswith("← var: MyVar"), (
        f"기본값 컬럼 prefix 누락 — '{text}'"
    )


def test_inspector_default_column_unchanged_for_normal_pin(qtbot) -> None:
    consumer = Node(name="C1", cls="X",
                    pins=[Pin(name="A", cpp_type="float", direction="Input",
                              default_value="0.5")])
    g = GraphModel(nodes=[consumer])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(consumer, g)
    item = panel._items["C1.A"]
    assert item.text(3) == "0.5"
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_variable_visualization.py::test_inspector_default_column_prefixed_with_var tests/app/test_variable_visualization.py::test_inspector_default_column_unchanged_for_normal_pin -v`
Expected: FAIL

- [ ] **Step 3: `InspectorPanel._add_pin` 수정**

`src/t3dgraph/core/app/inspector_panel.py` `_add_pin`의 `texts` 리스트 생성 부분:

```python
default_text = pin.default_value or ""
if pin.variable_source:
    if default_text:
        default_text = f"← var: {pin.variable_source} ({default_text})"
    else:
        default_text = f"← var: {pin.variable_source}"
texts = [pin.name, pin.cpp_type or "", pin.direction or "",
         default_text, status]
```

(기존 `pin.default_value or ""`를 위 정의에 통합.)

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_variable_visualization.py -v`
Expected: 6 passed (Task 3 4건 + Task 4 2건)

- [ ] **Step 5: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과. ξ 의 truncation 툴팁 테스트가 default 컬럼 텍스트를 검사하면 영향 — 다만 variable_source 없는 핀은 그대로 default_value라 회귀 없음.

- [ ] **Step 6: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

Orion 샘플 열어:
- 변수 노드(`RigVMVariableNode`) 헤더에 보라 `var` 배지 표시
- 변수에서 fed되는 노드 핀 라벨에 `(var: VarName)` 표시
- 인스펙터에서 해당 핀의 "기본값" 컬럼이 `← var: VarName` 시작

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_variable_visualization.py src/t3dgraph/core/app/inspector_panel.py
git commit -m "feat(app): inspector default column prefix with variable source (F16)"
```

---

## Self-Review 체크리스트

- Spec §8.1 디자인 — 변수 노드 배지 + 소비 핀 인라인 + 팔레트 entry ✅
- Spec §8.2 `_annotate_variable_consumers` 호출 위치 (`interpret()` 끝) — Task 1 Step 4 ✅
- Spec §8.2 sub-pin 매핑 — Task 1 `test_annotate_sub_pin_consumer` ✅
- Spec §8.2 서브그래프 재귀 — Task 1 `test_annotate_recurses_into_subgraph` ✅
- Spec §8.3 NodeItem 배지 + 핀 라벨 prefix — Task 3 ✅
- Spec §8.4 팔레트 `variable` 엔트리 — Task 2 ✅
- Spec §8.5 인스펙터 기본값 컬럼 결합(별도 컬럼 X) — Task 4 ✅
- Spec §8.6 테스트 6건 — Task 1·3·4 ✅
- PRESERVE-ALL — 가시화만, 모델 무변경 ✅

---

## 완료 후

머지 후:
- improver 자동 리뷰 → backlog
- 본 슬라이스는 π·τ와 독립 — 1차 사이클 종료 단계
- φ의 팔레트 엔트리 추가로 기존 사용자 `pin_colors.toml`에 `variable` 누락 가능성 — μ-A2 백로그(팔레트 파일 열기·재로드 액션) 진행 후 사용자가 직접 추가하거나 "팔레트 리셋"으로 해결
