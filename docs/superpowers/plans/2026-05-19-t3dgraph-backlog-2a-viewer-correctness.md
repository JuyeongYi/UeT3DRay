# t3dgraph 백로그 정리 ②a — 뷰어 정확도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** improver findings 중 뷰어 정확도 직결 6건을 수정한다 — 변경됨 휴리스틱 거짓양성, 인스펙터 핀 키 충돌, 실행순서 폰트, Position 누락 노드 레이아웃, 서브핀 링크 앵커, fan-in 강조 토글 효율.

**Architecture:** Phase 2a~2d 뷰어(`core/app/`) 위의 버그·정확도 수정. Model·분석 레이어 불변.

**Tech Stack:** Python 3.11+, PySide6, pytest + pytest-qt.

**선행 조건:** 백로그 정리 ①(라이브러리) 완료. 리포: `C:/Users/jylee/source/UeT3DRay`.

**근거:** `docs/superpowers/backlog.md` — improver findings.

**재검토 결과 (착수 전 backlog 규칙 적용):**
- `P2a-A1`·`P2b-A1`·`P2b-A2`·`P2c-A1`·`P2d-A1`·`P2d-A2` — 현재 코드에서 **여전히 유효**, 본 계획 포함.
- `P2b-B2`(`_type_suffix` 중복) — 백로그 정리 ①의 `core/t3d/paths.py` 중앙화가 `scene.py`·`node_filter_panel.py`의 로컬 `_type_suffix`를 제거함 → **해소됨**, 그룹 ②에서 제외.
- 리팩토링 findings 5건(`P2b-B1`·`P2b-B3`·`P2c-B1`·`P2c-B2`·`P2d-B1`) → 그룹 ②b.

---

## File Structure (백로그 정리 ②a)

| 파일 | 변경 | finding |
| --- | --- | --- |
| `src/t3dgraph/core/app/pin_status.py` | 수정 | zero 구조체 거짓양성 (P2b-A2) |
| `src/t3dgraph/core/app/inspector_panel.py` | 수정 | `_items` 전체 경로 키잉 (P2b-A1) |
| `src/t3dgraph/core/app/execution_order_panel.py` | 수정 | monospace styleHint (P2c-A1) |
| `src/t3dgraph/core/app/scene.py` | 수정 | Position 누락 폴백 + 서브핀 링크 앵커 (P2a-A1, P2d-A1) |
| `src/t3dgraph/core/app/items.py` | 수정 | 서브핀 앵커 + in-place 강조 (P2d-A1, P2d-A2) |
| `src/t3dgraph/core/app/main_window.py` | 수정 | fan-in 강조 토글 in-place (P2d-A2) |

---

## Task 1: P2b-A2 — 변경됨 휴리스틱의 zero 구조체 거짓양성

`is_changed_from_default`가 구조체 분기에서 `(X=0,Y=0,Z=0)` 같은 zero 구조체를 "변경됨"으로 오탐한다(`v not in ("","()",'""')`).

**Files:**
- Modify: `src/t3dgraph/core/app/pin_status.py`
- Modify: `tests/core/app/test_pin_status.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_pin_status.py` 에 추가:

```python
def test_zero_struct_not_changed():
    assert is_changed_from_default(
        _pin("FVector", "(X=0.000000,Y=0.000000,Z=0.000000)")) is False


def test_nonzero_struct_changed():
    assert is_changed_from_default(
        _pin("FVector", "(X=1.000000,Y=0.000000,Z=0.000000)")) is True


def test_nested_zero_struct_not_changed():
    assert is_changed_from_default(
        _pin("FTransform", "(Rotation=(X=0,Y=0,Z=0),Translation=(X=0,Y=0,Z=0))")) is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_pin_status.py -q`
Expected: FAIL — zero 구조체가 `True`(변경됨)로 판정됨

- [ ] **Step 3: 구현**

`core/app/pin_status.py` — 상단 import 추가와 zero-구조체 헬퍼, 그리고 마지막 `return` 보강:

```python
from ..t3d.values import parse_value, Scalar, Struct, ArrayLiteral, ValueParseError
```

```python
def _all_zero(value) -> bool:
    """파싱된 값의 모든 숫자 잎이 0이면 True."""
    if isinstance(value, Scalar):
        s = value.text.strip()
        try:
            return float(s) == 0.0
        except ValueError:
            return s in ("", "0")
    if isinstance(value, Struct):
        return bool(value.items) and all(_all_zero(v) for _, v in value.items)
    if isinstance(value, ArrayLiteral):
        return all(_all_zero(v) for v in value.items)
    return False


def _is_zero_struct(v: str) -> bool:
    if not (v.startswith("(") and v.endswith(")")):
        return False
    try:
        return _all_zero(parse_value(v))
    except ValueParseError:
        return False
```

`is_changed_from_default` 의 마지막 줄 `return v not in ("", "()", '""')` 를 다음으로 교체:

```python
    if v in ("", "()", '""'):
        return False
    if _is_zero_struct(v):
        return False
    return True
```

> 주: Quat 항등값 `(X=0,Y=0,Z=0,W=1)`는 W=1이라 여전히 "변경됨(추정)"으로 표시된다 — 휴리스틱의 알려진 한계로 수용(UI 라벨이 '추정'). 본 수정은 improver가 지적한 all-zero 구조체 거짓양성을 해소한다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_pin_status.py -q`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/pin_status.py tests/core/app/test_pin_status.py
git commit -m "fix(app): zero-struct no longer false-flagged as changed (P2b-A2)"
```

---

## Task 2: P2b-A1 — 인스펙터 핀 키 전체 경로화

`InspectorPanel._items`가 `pin.name`으로 키잉돼 동명 서브핀(`Translation.X`·`Scale3D.X`)이 충돌, `pin_count()`·핀 API가 부정확. 전체 경로(`Node.Pin.Sub`)로 키잉한다.

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py`
- Modify: `tests/core/app/test_inspector_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_inspector_panel.py` 에 추가:

```python
def test_same_named_subpins_no_collision(qtbot):
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin
    x1 = Pin(name="X", cpp_type="double", direction="Input")
    x2 = Pin(name="X", cpp_type="double", direction="Input")
    t = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[x1])
    s = Pin(name="S", cpp_type="FVector", direction="Input", subpins=[x2])
    node = Node(name="N", cls="X", pins=[t, s])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(node, GraphModel(nodes=[node], links=[]))
    # T, T.X, S, S.X = 4개 — name 키잉이면 X 충돌로 3개
    assert panel.pin_count() == 4
```

기존 헬퍼 호출(`is_pin_connected("Out")` 등)은 전체 경로 API로 바뀐다 — 기존 테스트의 해당 호출을 전체 경로로 갱신한다 (Step 3 참조).

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_inspector_panel.py::test_same_named_subpins_no_collision -q`
Expected: FAIL — `pin_count()`가 3 (X 충돌)

- [ ] **Step 3: 구현**

`core/app/inspector_panel.py` — `_add_pin`의 `_items` 키를 전체 경로로:

```python
        parent.addChild(item)
        self._items[full] = item
        for sub in pin.subpins:
            self._add_pin(sub, node_name, f"{path}.{sub.name}", connected, graph, item)
```

핀 조회 API를 전체 경로 기준으로 변경 (`pin_name` → `full_path`):

```python
    def is_pin_connected(self, full_path: str) -> bool:
        item = self._items.get(full_path)
        return item is not None and "연결됨" in item.text(4)

    def is_pin_changed(self, full_path: str) -> bool:
        item = self._items.get(full_path)
        return item is not None and "변경됨" in item.text(4)

    def activate_pin(self, full_path: str) -> None:
        item = self._items.get(full_path)
        if item is not None:
            self._on_activated(item, 0)
```

`tests/core/app/test_inspector_panel.py` 기존 테스트에서 핀 API 호출을 전체 경로로 갱신 — 예: `panel.is_pin_connected("Out")` → `panel.is_pin_connected("A.Out")`, `panel.activate_pin("Out")` → `panel.activate_pin("A.Out")`, `is_pin_changed("Scale")` → `is_pin_changed("A.Scale")` (노드명 `A` 기준).

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_inspector_panel.py -q`
Expected: PASS (갱신된 기존 + 신규)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/inspector_panel.py tests/core/app/test_inspector_panel.py
git commit -m "fix(app): InspectorPanel keys pins by full path (P2b-A1)"
```

---

## Task 3: P2c-A1 — 실행 순서 패널 monospace 폰트

`ExecutionOrderPanel`이 `QFont("Consolas")`를 하드코딩 — Consolas 없는 환경에서 폴백 불명확. 시스템 고정폭 폰트를 쓴다.

**Files:**
- Modify: `src/t3dgraph/core/app/execution_order_panel.py:4,19`
- Modify: `tests/core/app/test_execution_order_panel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_execution_order_panel.py` 에 추가:

```python
def test_uses_fixed_pitch_font(qtbot):
    panel = ExecutionOrderPanel()
    qtbot.addWidget(panel)
    # 고정폭(monospace) 폰트여야 함 — 특정 패밀리명 하드코딩 아님
    assert panel.list_font().fixedPitch() or \
        panel.list_font().styleHint() == panel.list_font().StyleHint.Monospace
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_execution_order_panel.py::test_uses_fixed_pitch_font -q`
Expected: FAIL — `list_font()` 메서드 없음 (또는 `QFont("Consolas")`가 fixedPitch 아님)

- [ ] **Step 3: 구현**

`core/app/execution_order_panel.py` — import와 `__init__`의 폰트 설정 교체:

```python
from PySide6.QtGui import QFontDatabase
```

`__init__` 의 `self._list.setFont(QFont("Consolas"))` 를:

```python
        self._list.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
```

(`QFont` import가 더 이상 안 쓰이면 제거.) 그리고 테스트용 접근자 추가:

```python
    def list_font(self):
        return self._list.font()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_execution_order_panel.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/execution_order_panel.py tests/core/app/test_execution_order_panel.py
git commit -m "fix(app): use system fixed-pitch font for execution order panel (P2c-A1)"
```

---

## Task 4: P2a-A1 — Position 누락 노드 폴백 레이아웃

`Position`이 없는 노드는 `NodeItem`이 (0,0)에 적재 → 전부 원점에 겹침. 씬이 None-위치 노드에 격자 폴백 좌표를 부여한다(Model 불변 — `item.setPos`로 뷰만 조정).

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `tests/core/app/test_scene.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_scene.py` 에 추가:

```python
def test_position_missing_nodes_get_distinct_fallback(qtbot):
    from t3dgraph.core.base.graph_model import GraphModel, Node
    g = GraphModel(nodes=[
        Node(name="A", cls="X", position=None),
        Node(name="B", cls="X", position=None),
        Node(name="C", cls="X", position=None),
    ], links=[])
    scene = GraphScene()
    scene.populate(g)
    pts = {(scene.node_item(n).pos().x(), scene.node_item(n).pos().y())
           for n in ("A", "B", "C")}
    assert len(pts) == 3                       # 서로 다른 위치 — 원점 겹침 아님
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_scene.py::test_position_missing_nodes_get_distinct_fallback -q`
Expected: FAIL — 세 노드 모두 (0,0)

- [ ] **Step 3: 구현**

`core/app/scene.py` — `populate`의 노드 생성 루프에서 `position is None`인 노드에 격자 좌표를 부여. 노드 생성 루프를 다음으로 교체:

```python
        fallback_i = 0
        for node in graph.nodes:
            item = NodeItem(
                node,
                connected_paths=frozenset(connected.get(node.name, set())),
                connected_only=vs.connected_pins_only,
                show_subpins=vs.expand_subpins,
                highlighted=vs.fan_in_highlight and node.name in convergence,
            )
            if node.position is None:
                item.setPos((fallback_i % 8) * 240.0, (fallback_i // 8) * 200.0)
                fallback_i += 1
            self.addItem(item)
            self._nodes[node.name] = item
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_scene.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/scene.py tests/core/app/test_scene.py
git commit -m "fix(app): grid fallback layout for nodes without Position (P2a-A1)"
```

---

## Task 5: P2d-A1 — 서브핀 링크 앵커

'깊이 펼침' 시 서브핀이 행으로 보이지만, 서브핀을 가리키는 링크는 여전히 부모 최상위 핀 행에 앵커된다. `NodeItem.pin_anchor`가 서브 경로를 받고, 펼쳐졌으면 서브핀 행에 앵커한다.

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `tests/core/app/test_items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_items.py` 에 추가:

```python
def test_pin_anchor_resolves_subpin_when_expanded(qtbot):
    sub = Pin(name="X", cpp_type="double", direction="Input")
    parent = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[sub])
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[parent])
    item = NodeItem(node, show_subpins=True)
    sub_anchor = item.pin_anchor("T.X", "Input")
    parent_anchor = item.pin_anchor("T", "Input")
    assert sub_anchor.y() != parent_anchor.y()        # 서브핀 자체 행에 앵커


def test_pin_anchor_subpin_falls_back_to_parent_when_collapsed(qtbot):
    sub = Pin(name="X", cpp_type="double", direction="Input")
    parent = Pin(name="T", cpp_type="FVector", direction="Input", subpins=[sub])
    node = Node(name="N", cls="X", position=(0.0, 0.0), pins=[parent])
    item = NodeItem(node, show_subpins=False)          # 서브핀 미렌더
    assert item.pin_anchor("T.X", "Input").y() == item.pin_anchor("T", "Input").y()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_items.py -q`
Expected: FAIL — `pin_anchor("T.X", ...)`가 부모로만 해석돼 서브핀/부모 y가 같음

- [ ] **Step 3: 구현**

`core/app/items.py` — `NodeItem.pin_anchor` 를 서브 경로 인식형으로 교체:

```python
    def pin_anchor(self, pin_subpath: str, direction: str) -> QPointF:
        """핀 앵커. pin_subpath는 노드 이후 경로('Pin' 또는 'Pin.Sub').
        펼쳐진 서브핀 행이 있으면 거기에, 없으면 최상위 핀 행, 그것도 없으면 노드 중앙."""
        full = f"{self.node.name}.{pin_subpath}"
        cy = self._rows.get(full)
        if cy is None:                                   # 서브핀 미렌더 → 최상위 핀 폴백
            top = pin_subpath.split(".", 1)[0]
            cy = self._rows.get(f"{self.node.name}.{top}")
        if cy is None:
            return self.mapToScene(QPointF(NODE_WIDTH / 2, self.rect().height() / 2))
        lx = NODE_WIDTH if (direction or "").lower() == "output" else 0.0
        return self.mapToScene(QPointF(lx, cy))
```

`core/app/scene.py` — `_add_link`이 최상위 핀 세그먼트 대신 노드 이후 전체 서브 경로를 넘기도록:

```python
    def _add_link(self, link: Link) -> None:
        s_node, t_node = node_of(link.source_path), node_of(link.target_path)
        src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
        if src is None or dst is None:
            return
        s_sub = link.source_path.split(".", 1)[1] if "." in link.source_path else ""
        t_sub = link.target_path.split(".", 1)[1] if "." in link.target_path else ""
        p1 = src.pin_anchor(s_sub, "Output")
        p2 = dst.pin_anchor(t_sub, "Input")
        item = LinkItem(p1, p2)
        self.addItem(item)
        self._links.append((item, s_node, t_node))
```

> 주: 기존 `pin_anchor("Pin", dir)` 호출(최상위 핀)은 그대로 동작 — `full` 조회 실패 시 같은 최상위 핀으로 폴백. Phase 2a/2d items 테스트 호환.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_items.py tests/core/app/test_scene.py -q`
Expected: PASS (기존 + 신규 2개)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py tests/core/app/test_items.py
git commit -m "fix(app): subpin-aware link anchoring (P2d-A1)"
```

---

## Task 6: P2d-A2 — fan-in 강조 토글 in-place 갱신

fan-in 강조 토글이 펜만 바뀌는데도 씬 전체를 재구축한다. 강조 토글은 NodeItem 펜만 in-place 갱신한다.

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/core/app/test_main_window.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/app/test_main_window.py` 에 추가:

```python
def test_fan_in_highlight_toggle_keeps_same_node_items(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_graph(_wired_graph())
    before = w.scene.node_item("A")
    w.set_view_mode("fan-in 강조", True)
    after = w.scene.node_item("A")
    assert before is after                            # 재구축 없음 — 같은 아이템 객체
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/core/app/test_main_window.py::test_fan_in_highlight_toggle_keeps_same_node_items -q`
Expected: FAIL — 강조 토글이 `_rebuild_scene` → `populate`로 새 NodeItem 생성

- [ ] **Step 3: 구현**

`core/app/items.py` — `NodeItem`에 in-place 펜 갱신 메서드 추가 (`pin_anchor` 다음):

```python
    def set_highlighted(self, on: bool) -> None:
        if on:
            self.setPen(QPen(QColor(255, 180, 60), 2.5))
        else:
            self.setPen(QPen(QColor(40, 40, 40)))
```

`core/app/scene.py` — 수렴점 집합으로 강조를 in-place 적용하는 메서드 추가 (`apply_hidden_types` 다음):

```python
    def apply_fan_in_highlight(self, convergence: set[str], on: bool) -> None:
        for name, item in self._nodes.items():
            item.set_highlighted(on and name in convergence)
```

`core/app/main_window.py` — fan-in 강조 토글만 재구축 대신 in-place 갱신. `_build_view_mode_toolbar`의 액션 구성에서 fan-in 강조만 별도 핸들러를 쓰도록 하고, 핸들러 추가:

`_build_view_mode_toolbar` 의 토글 목록을 다음으로 교체:

```python
        for label, setter, in_place in (
            ("연결된 핀만", self.view_state.set_connected_pins_only, False),
            ("깊이 펼침", self.view_state.set_expand_subpins, False),
            ("fan-in 강조", self.view_state.set_fan_in_highlight, True),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.toggled.connect(
                lambda checked, s=setter, ip=in_place: self._on_view_mode(s, checked, ip))
            toolbar.addAction(action)
            self.view_mode_actions.append(action)
```

`_on_view_mode` 를 다음으로 교체:

```python
    def _on_view_mode(self, setter, checked: bool, in_place: bool = False) -> None:
        setter(checked)
        if in_place and self._flow is not None:
            self.scene.apply_fan_in_highlight(
                set(self._flow.convergence_points), checked)
        else:
            self._rebuild_scene()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/core/app/test_main_window.py -q`
Expected: PASS (기존 + 신규)

- [ ] **Step 5: Commit**

```bash
git add src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py src/t3dgraph/core/app/main_window.py tests/core/app/test_main_window.py
git commit -m "perf(app): in-place pen update for fan-in highlight toggle (P2d-A2)"
```

---

## Task 7: 전체 회귀 검증

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `python -m pytest -q`
Expected: 전체 PASS — 기존 + 백로그 정리 ①·②a 신규 테스트, 실패 0

- [ ] **Step 2: GUI 수동 스모크 (선택)**

Run (디스플레이 있는 환경): `python -m t3dgraph.core.app.app tests/fixtures/orion/Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt`
Expected: 노드 겹침 없음, 인스펙터 서브핀 정확, fan-in 강조 토글 즉시 반영

(검증 전용 — 별도 커밋 없음.)

---

## Self-Review

**1. Findings coverage (그룹 ②a 범위)**
- P2b-A2 zero 구조체 거짓양성 → Task 1 ✓
- P2b-A1 인스펙터 핀 키 충돌 → Task 2 ✓
- P2c-A1 실행순서 폰트 → Task 3 ✓
- P2a-A1 Position 누락 폴백 → Task 4 ✓
- P2d-A1 서브핀 링크 앵커 → Task 5 ✓
- P2d-A2 강조 토글 효율 → Task 6 ✓
- **제외**: P2b-B2(`_type_suffix` 중복) — 백로그 정리 ①로 해소.
- **범위 밖**: 리팩토링 5건(P2b-B1·P2b-B3·P2c-B1·P2c-B2·P2d-B1) → 그룹 ②b. FEAT-5 → 그룹 ③.

**2. Placeholder scan** — "TBD/TODO" 없음. 모든 코드 단계에 실제 코드.

**3. Type consistency**
- `_is_zero_struct`/`_all_zero` — Task 1 내부, `parse_value`/`Scalar`/`Struct`/`ArrayLiteral`는 `core/t3d/values`의 기존 타입
- `InspectorPanel._items` 전체 경로 키 + `is_pin_connected/changed/activate_pin(full_path)` — Task 2 일관, 기존 테스트 호출 갱신 명시
- `NodeItem.pin_anchor(pin_subpath, direction)` — Task 5 정의, `scene._add_link`가 노드 이후 서브 경로 전달 일치. 최상위 핀 호출은 폴백으로 호환
- `NodeItem.set_highlighted`/`GraphScene.apply_fan_in_highlight`/`_on_view_mode(setter, checked, in_place)` — Task 6 일관. `self._flow`는 Phase 2d에서 MainWindow가 보관 중

---

## 다음 — 그룹 ②b·③

- **그룹 ②b** 뷰어 리팩토링 — P2b-B1(ViewState 옵저버 미사용)·P2b-B3(pin_status 전략 정합)·P2c-B1(패널 보일러플레이트 베이스)·P2c-B2(MainWindow MVC — 모델 오케스트레이션을 AppController로)·P2d-B1(set_view_mode 안정 식별자). planner가 별도 계획.
- **그룹 ③** FEAT-5 — 실행 순서 패널 코드형 렌더링 고도화.
