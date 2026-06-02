# batch ⑭ k2 — NodeItem이 NodeStyleProfile 사용 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** NodeItem이 cls suffix 직접 검사하던 if-분기(var 배지, chevron 상태)를 NodeStyleProfile 기반 데이터 분기로 교체. MainWindow가 NodeProfileTable 1회 로드 후 매 NodeItem 생성 시 주입.

**Spec:** §6

**Pre-condition:** k1 머지 완료 (NodeStyleProfile/NodeProfileTable 존재).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/items.py` | 수정 (NodeItem에 `profile` 인자, cls suffix 검사 제거) |
| `src/t3dgraph/core/app/scene.py` | 수정 (populate에 `node_profiles` 인자 + NodeItem 생성에 전달) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`NodeProfileTable.load()` 보유 + populate에 주입) |
| `tests/app/test_node_profile_integration.py` | 신규 |

---

## Task 1: NodeItem에 profile 인자

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 시그니처 변경**

`NodeItem.__init__`에 `profile: NodeStyleProfile | None = None` 추가:

```python
from .node_profiles import NodeStyleProfile, _DEFAULT_PROFILE

class NodeItem(QGraphicsRectItem):
    def __init__(self, node, *, ..., 
                 profile: "NodeStyleProfile | None" = None,
                 ...):
        ...
        self._profile = profile if profile is not None else NodeStyleProfile()
```

`_DEFAULT_PROFILE`을 노출하거나 NodeStyleProfile() 직접 생성 — 둘 다 OK.

- [ ] **Step 2: var 배지 분기 profile로**

기존:
```python
if (node.cls or "").rsplit(".", 1)[-1] == "RigVMVariableNode":
    # var 배지 그리기
    ...
```

변경:
```python
if self._profile.show_var_badge:
    # var 배지 그리기 (동일 로직)
    ...
```

- [ ] **Step 3: `_function_entry_state` profile 기반**

기존 cls suffix 직접 검사 → profile 검사:

```python
def _function_entry_state(self) -> tuple[QColor, str] | None:
    if not self._profile.always_show_chevron:
        return None
    if self.node.subgraph is not None:
        return QColor("#90EE90"), "더블클릭하여 서브그래프 진입"
    if self._profile.chevron_state_aware:
        tooltip = self._profile.tooltip_when_no_subgraph or "내부 그래프 데이터 없음"
        # tooltip 있으면 노랑(폴더 필요), 없으면 회색(데이터 없음)
        if self._profile.tooltip_when_no_subgraph:
            return QColor("#FFD700"), tooltip
        return QColor("#888888"), tooltip
    # 상태 무관 — 항상 녹색 chevron (chevron만 의도)
    return QColor("#90EE90"), "더블클릭하여 서브그래프 진입"
```

- [ ] **Step 4: 회귀 확인**

Run: `pytest tests/app/test_function_marker.py -v`
Expected: 기존 g5 테스트 통과 — RigVMCollapseNode/RigVMFunctionReferenceNode가 profile 통해 같은 chevron 색.

만약 회귀 발생: NodeItem 생성자 호출이 `profile=` 명시 안 하면 `_DEFAULT_PROFILE` 사용 → 기존 테스트는 NodeItem 직접 생성 시 profile 없어 분기 안 됨. 그러면 NodeItem 테스트도 profile 명시 또는 NodeProfileTable.load() 통과.

테스트 갱신 예시:
```python
def test_collapse_node_with_subgraph_green_chevron(qtbot) -> None:
    from t3dgraph.core.app.node_profiles import NodeStyleProfile
    n = Node(name="C1", cls="/Script/RigVMDeveloper.RigVMCollapseNode",
             subgraph=GraphModel())
    profile = NodeStyleProfile(always_show_chevron=True, chevron_state_aware=True)
    item = NodeItem(n, profile=profile)
    ...
```

또는 NodeProfileTable 사용:
```python
profile_table = NodeProfileTable.load()
profile = profile_table.resolve("RigVMCollapseNode")
item = NodeItem(n, profile=profile)
```

후자가 통합성 좋음.

- [ ] **Step 5: 커밋**

```bash
git add src/t3dgraph/core/app/items.py
git commit -m "refactor(app): NodeItem uses NodeStyleProfile for var badge + chevron states (k2)"
```

---

## Task 2: Scene.populate + MainWindow 와이어링

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: scene.populate 시그니처 확장**

```python
def populate(self, graph, *, view_state=None, flow=None,
             pin_colors=None, layout_overrides=None, graph_key="",
             node_profiles: "NodeProfileTable | None" = None) -> None:
    # ... 기존 ...
    self._node_profiles = node_profiles
    for node in graph.nodes:
        profile = None
        if node_profiles is not None:
            suffix = (node.cls or "").rsplit(".", 1)[-1]
            profile = node_profiles.resolve(suffix)
        item = NodeItem(
            node,
            connected_paths=...,
            connected_only=...,
            expanded_paths=...,
            highlighted=...,
            pin_colors=pin_colors,
            profile=profile,
        )
        # ... 기존 ...
```

- [ ] **Step 2: MainWindow에 NodeProfileTable 보유**

`__init__`에서 PinColorTable 옆에:

```python
from .node_profiles import NodeProfileTable

self.node_profiles = NodeProfileTable.load()
```

`_rebuild_scene`/`_render_current`에 주입:

```python
self.scene.populate(
    current, view_state=self.current_view_state(),
    flow=bundle.flow, pin_colors=self.pin_colors,
    layout_overrides=self.layout_overrides,
    graph_key=self._current_graph_key(),
    node_profiles=self.node_profiles,
)
```

- [ ] **Step 3: 통합 테스트**

`tests/app/test_node_profile_integration.py`:

```python
"""k2 통합 — MainWindow가 NodeProfileTable 사용."""
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow


def test_main_window_loads_node_profiles(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.node_profiles is not None


def test_variable_node_renders_with_badge(qtbot) -> None:
    """RigVMVariableNode 노드를 그래프에 추가 → var 배지 표시."""
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    w = MainWindow()
    qtbot.addWidget(w)
    var_node = Node(name="V1",
                    cls="/Script/RigVMDeveloper.RigVMVariableNode")
    g = GraphModel(nodes=[var_node])
    w.open_graph(g)
    item = w.scene.node_item("V1")
    assert item is not None
    texts = [c.text() for c in item.childItems()
             if isinstance(c, QGraphicsSimpleTextItem)]
    assert "var" in texts
```

- [ ] **Step 4: 실행 + 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 5: 커밋**

```bash
git add src/t3dgraph/core/app/scene.py src/t3dgraph/core/app/main_window.py tests/app/test_node_profile_integration.py
git commit -m "feat(app): MainWindow/Scene wire NodeProfileTable to NodeItem (k2)"
```

## 완료 후

k1 인프라가 실제로 사용됨. 신규 노드 클래스 추가는 TOML 한 줄. k3가 layout_hint 처리.
