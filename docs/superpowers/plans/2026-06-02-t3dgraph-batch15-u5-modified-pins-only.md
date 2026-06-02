# batch ⑮ u5 — "수정된 핀만" 토글 (연결/변경 합집합) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 툴바 "연결된 핀만" 라벨을 "수정된 핀만"으로 변경. 동작은 핀이 **연결됨 OR 변경됨(default 값에서 변경됨)** 일 때 표시되도록 확장.

**Pre-condition:** master 최신. NodeItem `collect_pin_rows` + InspectorPanel `is_changed_from_default` 존재.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (`collect_pin_rows` — `changed_pins` 인자 + include 조건 확장) |
| `src/t3dgraph/core/app/scene.py` | 수정 (`populate` — `changed_pins` 계산해 NodeItem 전달) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (toolbar 라벨 변경) |
| `tests/app/test_modified_pins_only.py` | 신규 |

---

## Task 1: collect_pin_rows + 라벨 변경

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `src/t3dgraph/core/app/scene.py`
- Create: `tests/app/test_modified_pins_only.py`

- [ ] **Step 1: 테스트**

```python
"""u5 — '수정된 핀만' 토글 (연결 OR 변경 합집합)."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.view_state import ViewState


def _data_pin(name, default_value=None, direction="Input"):
    return Pin(name=name, cpp_type="float", direction=direction,
               default_value=default_value)


def test_changed_pin_visible_in_modified_only_mode(qtbot) -> None:
    """default value에서 변경된 핀은 보임."""
    node = Node(name="N", cls="X",
                pins=[
                    _data_pin("UnchangedDefault", default_value="0.0"),
                    _data_pin("ChangedFromDefault", default_value="42.5"),
                ])
    g = GraphModel(nodes=[node], links=[])
    scene = GraphScene()
    vs = ViewState(connected_pins_only=True)   # 토글 ON
    scene.populate(g, view_state=vs)
    item = scene.node_item("N")
    # ChangedFromDefault 행은 존재
    assert any(p.endswith(".ChangedFromDefault") for p in item._row_paths)
    # default 값 그대로인 핀은 숨김
    assert not any(p.endswith(".UnchangedDefault") for p in item._row_paths)


def test_connected_pin_visible_in_modified_only_mode(qtbot) -> None:
    """연결된 핀도 여전히 보임."""
    a = Node(name="A", cls="X",
             pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    b = Node(name="B", cls="X",
             pins=[Pin(name="In", cpp_type="float", direction="Input")])
    g = GraphModel(nodes=[a, b],
                   links=[Link(source_path="A.Out", target_path="B.In")])
    scene = GraphScene()
    vs = ViewState(connected_pins_only=True)
    scene.populate(g, view_state=vs)
    a_item = scene.node_item("A")
    b_item = scene.node_item("B")
    assert any(p.endswith(".Out") for p in a_item._row_paths)
    assert any(p.endswith(".In") for p in b_item._row_paths)


def test_off_mode_shows_all_pins(qtbot) -> None:
    """토글 OFF면 모든 핀 표시 (기존 동작 회귀 없음)."""
    node = Node(name="N", cls="X",
                pins=[_data_pin("A"), _data_pin("B")])
    g = GraphModel(nodes=[node])
    scene = GraphScene()
    vs = ViewState(connected_pins_only=False)
    scene.populate(g, view_state=vs)
    item = scene.node_item("N")
    assert len(item._row_paths) == 2
```

- [ ] **Step 2: collect_pin_rows에 changed_pins 인자**

`src/t3dgraph/core/app/items.py`:

```python
def collect_pin_rows(
    node: Node,
    *,
    connected_subtree: frozenset[str],
    changed_pins: frozenset[str] = frozenset(),
    connected_only: bool,
    expanded: frozenset[str],
) -> list[PinRow]:
    rows: list[PinRow] = []

    def walk(pin, path, depth, parent_dir):
        my_dir = _normalize_direction(pin.direction)
        if not my_dir:
            my_dir = parent_dir
        # "수정된 핀만" 모드: 연결 OR 변경된 핀만 포함
        is_conn = path in connected_subtree
        is_chg = path in changed_pins
        include_self = (not connected_only) or is_conn or is_chg
        # ... 기존 walk 로직
```

(쉬운 디폴트: `changed_pins=frozenset()` — 변경 없으면 기존 동작.)

- [ ] **Step 3: scene.populate에 changed_pins 계산**

`src/t3dgraph/core/app/scene.py`:

```python
from .pin_status import is_changed_from_default


def _changed_paths_by_node(graph) -> dict[str, set[str]]:
    """default 값에서 변경된 핀의 full path 모음."""
    out: dict[str, set[str]] = {}

    def walk(node_name, pin, prefix):
        path = f"{prefix}.{pin.name}"
        if is_changed_from_default(pin):
            out.setdefault(node_name, set()).add(path)
        for sp in pin.subpins:
            walk(node_name, sp, path)

    for n in graph.nodes:
        for p in n.pins:
            walk(n.name, p, n.name)
    return out


# populate 내 NodeItem 생성 시:
connected = self._connected_paths_by_node(graph)
changed = _changed_paths_by_node(graph)
for node in graph.nodes:
    item = NodeItem(
        node,
        connected_paths=frozenset(connected.get(node.name, set())),
        changed_paths=frozenset(changed.get(node.name, set())),
        connected_only=vs.connected_pins_only,
        ...
    )
```

`NodeItem.__init__`에 `changed_paths` 인자 추가 후 `collect_pin_rows`에 전달.

- [ ] **Step 4: 툴바 라벨 변경**

`main_window.py::_build_view_mode_toolbar`:

```python
toggles = (
    ("connected_only", "수정된 핀만", ...),  # 변경
    ("fan_in_highlight", "fan-in 강조", ...),
)
```

(내부 식별자 `connected_only`는 유지 — 호환성. 라벨만 변경.)

- [ ] **Step 5: 실행**

Run: `pytest tests/app/test_modified_pins_only.py -v`
Expected: 3 passed.

Run: `pytest tests -v`
Expected: 전체 통과. 기존 "연결된 핀만" 가정 테스트가 라벨로 검사하면 갱신.

- [ ] **Step 6: 수동 검증**

```bash
uv run t3dgraph-gui
```

툴바 "수정된 핀만" 토글 ON → 연결됐거나 default 값에서 변경된 핀만 노드에 표시.

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_modified_pins_only.py src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): '수정된 핀만' toggle — connected OR changed-from-default"
```

## 완료 후

기존 "연결된 핀만"보다 사용성↑. 사용자가 default와 다른 모든 의미 있는 핀 한눈에 파악.
