# batch ⑮ v1 — aggregate status 단일 진실원·정보 손실 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** u10 improver findings 3건 통합 정리.

- **u10-A1**: scene의 `_changed_paths_by_node` 결과 set을 InspectorPanel에 주입 → 양쪽 walk 제거, 단일 진실원
- **u10-A3**: self+desc 동시 connected/changed 일 때 `"연결됨 (원소 포함)"` · `"변경됨(추정) (원소 포함)"` 합쳐 표시 (정보 손실 제거)
- **u10-B1**: `GraphScene._connected_paths_by_node`·`_changed_paths_by_node` staticmethod 래퍼 제거, 호출부 모듈 함수로 통일

**Pre-condition:** master 최新 — u10 머지 (HEAD `09af58f`), 628 tests.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/scene.py` | 수정 (B1 — staticmethod 래퍼 제거, populate 내부에서 모듈 함수 직접 호출) |
| `src/t3dgraph/core/app/inspector_panel.py` | 수정 (A1 — `show_node` 시그니처 확장 + 자체 walk 제거 / A3 — 합쳐 표시) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (A1 — show_node 호출 시 scene이 계산한 set 전달) |
| `tests/core/app/test_scene_helpers.py` | 수정 (B1 — 모듈 함수로 호출 갱신) |
| `tests/app/test_aggregate_status.py` | 수정 (A3 — 합쳐 표시 검증 추가) |
| `tests/app/test_aggregate_single_source.py` | 신규 (A1 — InspectorPanel은 scene set만 신뢰) |

---

## Task 1: B1 — staticmethod 래퍼 제거

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `tests/core/app/test_scene_helpers.py`

- [ ] **Step 1: scene.py — staticmethod 두 곳 제거 + populate 호출 갱신**

`src/t3dgraph/core/app/scene.py` 95~101 라인 삭제:

```python
    @staticmethod
    def _connected_paths_by_node(graph: GraphModel) -> dict[str, set[str]]:
        return _connected_paths_by_node(graph)

    @staticmethod
    def _changed_paths_by_node(graph: GraphModel) -> dict[str, set[str]]:
        return _changed_paths_by_node(graph)
```

`populate`의 49~50 라인은 모듈 함수 직접 호출로 변경:

```python
        connected = _connected_paths_by_node(graph)
        changed = _changed_paths_by_node(graph)
```

(모듈 함수는 파일 하단 181·194 라인에 이미 존재 — 그대로 둠.)

- [ ] **Step 2: tests/core/app/test_scene_helpers.py 갱신**

`tests/core/app/test_scene_helpers.py` 10 라인의 `GraphScene._connected_paths_by_node(g)` 호출을 모듈 함수로:

```python
from t3dgraph.core.app.scene import _connected_paths_by_node
...
by_node = _connected_paths_by_node(g)
```

(파일 상단 import 정리. `GraphScene` import 없어졌으면 제거.)

- [ ] **Step 3: 실행**

Run: `pytest tests/core/app/test_scene_helpers.py tests/app/test_aggregate_status.py -v`
Expected: 모두 통과 (회귀 없음).

Run: `pytest tests -v`
Expected: 전체 628 통과.

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/app/scene.py tests/core/app/test_scene_helpers.py
git commit -m "refactor(app): drop GraphScene staticmethod wrappers, call module fns directly (v1-B1)"
```

---

## Task 2: A1 — InspectorPanel 단일 진실원 (scene set 주입)

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_aggregate_single_source.py`

배경: 현재 InspectorPanel은 `_has_changed_descendant`·`_has_connected_descendant`로 별도 walk. scene이 만든 set과 의미는 같으나 두 구현 — 향후 정책(variable_source 제외 등) 추가 시 silent divergence 위험.

**해법:** `show_node(node, graph)` → `show_node(node, graph, *, changed_paths=None, connected_paths=None)`. 호출자가 set을 전달하면 그것만 사용. None이면 호환을 위해 모듈 함수로 직접 계산해 동일 결과 보장 (테스트 픽스처에서 graph만 넘기던 케이스 호환).

- [ ] **Step 1: 테스트 — InspectorPanel이 외부 set만 신뢰**

`tests/app/test_aggregate_single_source.py` 신규:

```python
"""v1-A1 — InspectorPanel은 외부 changed/connected set만 신뢰 (단일 진실원)."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.inspector_panel import InspectorPanel


def test_inspector_uses_external_changed_set_only(qtbot) -> None:
    """외부 changed_paths set이 자식 path 누락 — InspectorPanel은 부모를 '원소 변경됨'으로 표시 안 함."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")   # 실제 changed (is_changed_from_default True)
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    # 외부에서 빈 set 전달 — scene이 "이 그래프는 변경 없다"고 판정한 상황 시뮬
    panel.show_node(n, g, changed_paths=set(), connected_paths=set())
    parent_item = panel._items["N.Pos"]
    # InspectorPanel이 자체 walk를 안 하므로 "원소 변경됨" 표시 없음
    assert "원소 변경됨" not in parent_item.text(4)
    # 자식도 외부 set이 빈 이상 changed 표시 없음
    sub_item = panel._items["N.Pos.X"]
    assert "변경됨" not in sub_item.text(4)


def test_inspector_uses_external_connected_set_only(qtbot) -> None:
    """외부 connected_paths set이 자식 path 만 — 부모는 '원소 연결됨'."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    target = Node(name="T", cls="X", pins=[parent])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Pos.X")],
    )
    # scene이 prefix까지 포함한 set 전달 (실제 _connected_paths_by_node 동작)
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g,
                    changed_paths=set(),
                    connected_paths={"T.Pos", "T.Pos.X"})
    parent_item = panel._items["T.Pos"]
    assert "원소 연결됨" in parent_item.text(4)


def test_inspector_default_falls_back_to_module_fn(qtbot) -> None:
    """set 전달 없으면 모듈 함수로 직접 계산 (호환)."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(n, g)   # set 안 넘김
    parent_item = panel._items["N.Pos"]
    assert "원소 변경됨" in parent_item.text(4)
```

- [ ] **Step 2: inspector_panel.py 갱신**

`src/t3dgraph/core/app/inspector_panel.py`:

import 추가 (파일 상단):

```python
from .scene import _changed_paths_by_node, _connected_paths_by_node
```

`show_node` 시그니처 + 본문 변경 (59~76 라인):

```python
    def show_node(self, node: Node | None, graph: GraphModel,
                  *,
                  changed_paths: set[str] | None = None,
                  connected_paths: set[str] | None = None) -> None:
        self._tree.clear()
        self._items = {}
        if node is None:
            self._set_title("(노드를 선택하세요)")
            return
        header = node.display_name or node.name or "?"
        cls_part = node.cls or "?"
        role_bits = []
        if node.role_category:
            role_bits.append(node.role_category)
        if node.role_summary:
            role_bits.append(node.role_summary)
        role_suffix = f"   ·   역할: {' · '.join(role_bits)}" if role_bits else ""
        self._set_title(f"{header}  [{cls_part}]{role_suffix}")
        # 단일 진실원 — 외부에서 받으면 그대로, 아니면 모듈 함수로 계산
        if changed_paths is None:
            changed_paths = _changed_paths_by_node(graph).get(node.name, set())
        if connected_paths is None:
            connected_paths = _connected_paths_by_node(graph).get(node.name, set())
        for pin in node.pins:
            self._add_pin(pin, node.name, pin.name,
                          changed_paths, connected_paths, graph,
                          self._tree.invisibleRootItem())
```

`_add_pin` 시그니처 + 본문 변경 (93~127 라인):

```python
    def _add_pin(self, pin: Pin, node_name: str, path: str,
                 changed_paths: set[str], connected_paths: set[str],
                 graph: GraphModel, parent: QTreeWidgetItem) -> None:
        full = f"{node_name}.{path}"
        # connected_paths/changed_paths는 부모 prefix 자동 포함 — full만 체크
        is_in_conn = full in connected_paths
        is_in_chg = full in changed_paths
        # self vs descendant 구분 — self는 link/default 정확 매칭
        is_self_conn = self._is_self_target(full, graph)
        is_self_chg = is_changed_from_default(pin)
        has_desc_conn = is_in_conn and not is_self_conn
        has_desc_chg = is_in_chg and not is_self_chg
        status_parts = []
        # A3: self + desc 모두 있으면 합쳐서 표시
        if is_self_conn and has_desc_conn:
            status_parts.append("연결됨 (원소 포함)")
        elif is_self_conn:
            status_parts.append("연결됨")
        elif has_desc_conn:
            status_parts.append("원소 연결됨")
        if is_self_chg and has_desc_chg:
            status_parts.append("변경됨(추정) (원소 포함)")
        elif is_self_chg:
            status_parts.append("변경됨(추정)")
        elif has_desc_chg:
            status_parts.append("원소 변경됨")
        status = " · ".join(status_parts)
        default_text = pin.default_value or ""
        if pin.variable_source:
            if default_text:
                default_text = f"← var: {pin.variable_source} ({default_text})"
            else:
                default_text = f"← var: {pin.variable_source}"
        texts = [pin.name, pin.cpp_type or "", pin.direction or "",
                 default_text, status]
        item = QTreeWidgetItem(texts)
        self._apply_truncation_tooltips(item, texts)
        if is_self_conn:
            peer = _peer_of(full, graph)
            if peer:
                item.setData(0, _PEER_ROLE, peer)
        parent.addChild(item)
        self._items[full] = item
        for sub in pin.subpins:
            self._add_pin(sub, node_name, f"{path}.{sub.name}",
                          changed_paths, connected_paths, graph, item)

    @staticmethod
    def _is_self_target(full: str, graph: GraphModel) -> bool:
        for link in graph.links:
            if link.source_path == full or link.target_path == full:
                return True
        return False
```

`_has_connected_descendant`·`_has_changed_descendant` staticmethod 두 개 (129~146 라인) **전부 삭제** — 이제 외부 set + `_is_self_target`로 모두 결정.

- [ ] **Step 3: main_window.py — scene set 전달**

`src/t3dgraph/core/app/main_window.py` 512 라인 부근 `self.inspector.show_node(node, self.graph)` 호출지점에서, scene이 이미 populate 시점에 계산한 set이 있다면 그대로 사용. 가장 단순한 방법: `from .scene import _changed_paths_by_node, _connected_paths_by_node` 후 호출 시 계산:

```python
        from .scene import _changed_paths_by_node, _connected_paths_by_node
        changed_set = _changed_paths_by_node(self.graph).get(node.name, set())
        connected_set = _connected_paths_by_node(self.graph).get(node.name, set())
        self.inspector.show_node(node, self.graph,
                                 changed_paths=changed_set,
                                 connected_paths=connected_set)
```

(scene이 populate 동안 전체 dict를 캐싱하는 것은 별도 작업 — 여기는 단일 진실원 함수 호출이 핵심.)

614 라인 `self.inspector.show_node(None, current)`는 None이라 그대로 둠.

- [ ] **Step 4: 기존 test_aggregate_status 회귀 확인**

`tests/app/test_aggregate_status.py`의 InspectorPanel 테스트는 `panel.show_node(n, g)` 형태로 set을 안 넘겨 — fallback 경로(모듈 함수 자체 계산)가 그대로 동작해 회귀 없음.

- [ ] **Step 5: 실행**

Run: `pytest tests/app/test_aggregate_single_source.py -v`
Expected: 3 passed.

Run: `pytest tests/app/test_aggregate_status.py -v`
Expected: 기존 6 모두 통과.

Run: `pytest tests -v`
Expected: 전체 631 통과 (628 + 3 신규).

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_aggregate_single_source.py src/t3dgraph/core/app/inspector_panel.py src/t3dgraph/core/app/main_window.py
git commit -m "refactor(app): inspector single-source for aggregate status (v1-A1)"
```

---

## Task 3: A3 — self+desc 동시 합쳐 표시 검증

**Files:**
- Modify: `tests/app/test_aggregate_status.py`

Task 2 단계에서 코드 자체는 이미 `"연결됨 (원소 포함)"`·`"변경됨(추정) (원소 포함)"` 처리됨. 별도 회귀 테스트 추가.

- [ ] **Step 1: 테스트 추가**

`tests/app/test_aggregate_status.py` 하단에 두 테스트 추가:

```python
def test_inspector_self_and_descendant_connected_combined(qtbot) -> None:
    """배열 자체 연결 + 자식 핀도 따로 연결 → '연결됨 (원소 포함)'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub_0 = Pin(name="0", cpp_type="float", direction="Input")
    array_pin = Pin(name="Items", cpp_type="TArray<float>",
                    direction="Input", subpins=[sub_0])
    target = Node(name="T", cls="X", pins=[array_pin])
    src1 = Node(name="S1", cls="X",
                pins=[Pin(name="Out", cpp_type="TArray<float>",
                          direction="Output")])
    src2 = Node(name="S2", cls="X",
                pins=[Pin(name="Out", cpp_type="float",
                          direction="Output")])
    g = GraphModel(
        nodes=[src1, src2, target],
        links=[
            Link(source_path="S1.Out", target_path="T.Items"),    # self
            Link(source_path="S2.Out", target_path="T.Items.0"),  # desc
        ],
    )
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g)
    parent_item = panel._items["T.Items"]
    assert "연결됨 (원소 포함)" in parent_item.text(4)


def test_inspector_self_and_descendant_changed_combined(qtbot) -> None:
    """struct 자체 default + 자식도 default → '변경됨(추정) (원소 포함)'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 default_value="(X=1,Y=2,Z=3)", subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(n, g)
    parent_item = panel._items["N.Pos"]
    assert "변경됨(추정) (원소 포함)" in parent_item.text(4)
```

- [ ] **Step 2: 실행**

Run: `pytest tests/app/test_aggregate_status.py -v`
Expected: 8 passed (6 기존 + 2 신규).

Run: `pytest tests -v`
Expected: 전체 633 통과.

- [ ] **Step 3: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 샘플 — 배열 자체가 link 받으면서 자식도 link 받는 케이스에서 `"연결됨 (원소 포함)"`. 부모/자식 모두 default 변경된 struct는 `"변경됨(추정) (원소 포함)"`.

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_aggregate_status.py
git commit -m "test(app): cover combined self+desc aggregate status labels (v1-A3)"
```

---

## 완료 후

- A1: scene·inspector가 같은 의미를 두 번 walk하지 않는다. 향후 정책(variable_source 제외 등)은 모듈 함수 한 곳만 고치면 양쪽 일관.
- A3: 배열 자체 + 자식 모두 link 받는 정보가 status에 살아남는다.
- B1: staticmethod 래퍼 사라져 호출 표면 단일.

C1(시각 chip)은 별도 후순위 — ξ slice tooltip 인프라와 함께 묶을 수 있을 때 진행.
