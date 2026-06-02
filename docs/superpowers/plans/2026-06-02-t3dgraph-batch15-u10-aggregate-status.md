# batch ⑮ u10 — 상위 핀 aggregate 상태 (원소 변경됨/연결됨) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 컬렉션(struct/array) 핀의 하위 아이템이 변경/연결되면 상위에 표시:
- 인스펙터 status: **"원소 변경됨"** / **"원소 연결됨"**
- 노드뷰: 상위 핀도 "수정된 핀만" 토글에서 보이고 라벨 bold
- 배열 자체가 직접 연결된 경우는 그냥 **"연결됨"** (자기 connection이 우선)

**Pre-condition:** master 최신 (u5/u6 머지됨 — `changed_paths`·`connected_paths` 인프라).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/scene.py` | 수정 (`_changed_paths_by_node`·`_connected_paths_by_node`가 부모 path 자동 포함) |
| `src/t3dgraph/core/app/inspector_panel.py` | 수정 (status 텍스트에 "원소 변경됨/연결됨" 추가) |
| `tests/app/test_aggregate_status.py` | 신규 |

---

## Task 1: scene aggregation up (parent paths)

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Create: `tests/app/test_aggregate_status.py`

- [ ] **Step 1: 테스트**

```python
"""u10 — 상위 핀 aggregate 상태."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import (
    _changed_paths_by_node, _connected_paths_by_node,
)


def test_changed_descendant_includes_parent_path() -> None:
    """struct의 자식이 default 변경 시 부모 path도 changed set에 포함."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")   # changed
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    result = _changed_paths_by_node(g)
    assert "N.Pos" in result.get("N", set())   # 부모 포함
    assert "N.Pos.X" in result.get("N", set())


def test_connected_descendant_includes_parent_path() -> None:
    """struct 자식 핀이 link target이면 부모 path도 connected set에 포함."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n_target = Node(name="T", cls="X", pins=[parent])
    n_src = Node(name="S", cls="X",
                 pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[n_src, n_target],
        links=[Link(source_path="S.Out", target_path="T.Pos.X")],
    )
    result = _connected_paths_by_node(g)
    # 부모 path도 connected set에
    assert "T.Pos" in result.get("T", set())
    assert "T.Pos.X" in result.get("T", set())


def test_unchanged_parent_no_changed_subpin() -> None:
    """자식 변경 없으면 부모도 changed set에 없음."""
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="0.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    result = _changed_paths_by_node(g)
    assert "N.Pos" not in result.get("N", set())
```

- [ ] **Step 2: scene 함수 갱신**

`src/t3dgraph/core/app/scene.py`:

```python
from .pin_status import is_changed_from_default


def _changed_paths_by_node(graph) -> dict[str, set[str]]:
    """default 값에서 변경된 핀의 path — 자식 변경 시 부모 path 자동 포함."""
    out: dict[str, set[str]] = {}

    def walk(node_name: str, pin, prefix: str) -> bool:
        path = f"{prefix}.{pin.name}"
        is_chg = is_changed_from_default(pin)
        descendant_chg = False
        for sp in pin.subpins:
            if walk(node_name, sp, path):
                descendant_chg = True
        if is_chg or descendant_chg:
            out.setdefault(node_name, set()).add(path)
            return True
        return False

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    return out


def _connected_paths_by_node(graph) -> dict[str, set[str]]:
    """connected pin paths — 자식이 link target이면 부모 path 자동 포함.

    기존 _connected_paths_by_node는 link path 자체와 prefix 모두를 add 했음.
    그 자체가 이미 부모 포함이라 변경 거의 없음 — 검증 + 명시화.
    """
    from ..base.paths import node_of
    out: dict[str, set[str]] = {}
    for link in graph.links:
        for path in (link.source_path, link.target_path):
            node = node_of(path)
            bucket = out.setdefault(node, set())
            parts = path.split(".")
            for i in range(2, len(parts) + 1):
                bucket.add(".".join(parts[:i]))
    return out
```

(connected는 이미 prefix 포함 — 검증 테스트가 통과해야 함.)

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_aggregate_status.py -v`
Expected: 3 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (u5 toggle도 부모 핀까지 자동으로 보이게 됨).

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_aggregate_status.py src/t3dgraph/core/app/scene.py
git commit -m "feat(app): aggregate changed paths up to parent pins (u10 task1)"
```

---

## Task 2: Inspector status — "원소 변경됨/연결됨"

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py`
- Modify: `tests/app/test_aggregate_status.py`

- [ ] **Step 1: 테스트**

```python
def test_inspector_shows_element_changed(qtbot) -> None:
    """struct 자식이 변경 + 부모 직접 변경 없음 → status에 '원소 변경됨'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub = Pin(name="X", cpp_type="float", direction="Input",
              default_value="42.0")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(n, g)
    parent_item = panel._items["N.Pos"]
    assert "원소 변경됨" in parent_item.text(4)
    # 자식은 자기 자신 "변경됨"
    sub_item = panel._items["N.Pos.X"]
    assert "변경됨" in sub_item.text(4)
    assert "원소" not in sub_item.text(4)   # 자기 자신


def test_inspector_shows_element_connected(qtbot) -> None:
    """배열 자식 핀이 link target → 부모는 '원소 연결됨'."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    sub_0 = Pin(name="0", cpp_type="float", direction="Input")
    array_pin = Pin(name="Items", cpp_type="TArray<float>",
                    direction="Input", subpins=[sub_0])
    target = Node(name="T", cls="X", pins=[array_pin])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Items.0")],
    )
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g)
    parent_item = panel._items["T.Items"]
    assert "원소 연결됨" in parent_item.text(4)


def test_inspector_array_self_connected_shows_connected(qtbot) -> None:
    """배열 자체가 link target이면 그냥 '연결됨' (자기 우선)."""
    from t3dgraph.core.app.inspector_panel import InspectorPanel
    array_pin = Pin(name="Items", cpp_type="TArray<float>",
                    direction="Input")
    target = Node(name="T", cls="X", pins=[array_pin])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="TArray<float>",
                         direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Items")],
    )
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_node(target, g)
    parent_item = panel._items["T.Items"]
    assert "연결됨" in parent_item.text(4)
    assert "원소" not in parent_item.text(4)
```

- [ ] **Step 2: InspectorPanel._add_pin 갱신**

```python
def _add_pin(self, pin, node_name, path, connected, graph, parent):
    full = f"{node_name}.{path}"
    is_self_conn = full in connected and self._is_self_target(full, graph)
    is_self_chg = is_changed_from_default(pin)
    has_desc_conn = self._has_connected_descendant(pin, full, connected, graph)
    has_desc_chg = self._has_changed_descendant(pin)
    
    status_parts = []
    if is_self_conn:
        status_parts.append("연결됨")
    elif has_desc_conn:
        status_parts.append("원소 연결됨")
    if is_self_chg:
        status_parts.append("변경됨(추정)")
    elif has_desc_chg:
        status_parts.append("원소 변경됨")
    status = " · ".join(status_parts)
    # ... 기존 texts 구성 ...


def _is_self_target(self, full: str, graph: GraphModel) -> bool:
    """이 핀 path 자체가 어떤 link의 source 또는 target?"""
    for link in graph.links:
        if link.source_path == full or link.target_path == full:
            return True
    return False


def _has_connected_descendant(self, pin: Pin, full: str,
                              connected: set, graph: GraphModel) -> bool:
    for sp in pin.subpins:
        sub_full = f"{full}.{sp.name}"
        if self._is_self_target(sub_full, graph):
            return True
        if self._has_connected_descendant(sp, sub_full, connected, graph):
            return True
    return False


def _has_changed_descendant(self, pin: Pin) -> bool:
    for sp in pin.subpins:
        if is_changed_from_default(sp):
            return True
        if self._has_changed_descendant(sp):
            return True
    return False
```

(connected set은 이미 prefix 모두 포함하므로 `full in connected`는 자기 또는 자식 어느 하나라도 link 받으면 True — `_is_self_target`로 자기 자신만 체크하도록 분리.)

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_aggregate_status.py -v`
Expected: 6 passed (Task 1 + Task 2).

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 샘플 — 구조체 핀에 자식 default가 변경되면 부모 status에 "원소 변경됨". 배열 자식 핀이 link 받으면 부모 "원소 연결됨". 배열 자체 link면 부모 "연결됨".

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_aggregate_status.py src/t3dgraph/core/app/inspector_panel.py
git commit -m "feat(app): inspector aggregate status '원소 변경됨/연결됨' (u10 task2)"
```

## 완료 후

컬렉션 핀의 상태 한눈에. 노드뷰는 u5 toggle + u6 bold가 부모도 자동 적용(scene path aggregation으로).
