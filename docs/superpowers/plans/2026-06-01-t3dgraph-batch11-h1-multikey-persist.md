# batch ⑪ h1 — Multi-subgraph 영속 키 (ω-A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 영속 상태가 활성 graph_key 하나만 저장하던 함정 해소. `_view_states`·`layout_overrides`의 모든 키를 직렬화·복원.

**Architecture:** `PersistentState`에 `per_graph: dict[str, GraphState]` 필드 추가, `schema_version: 1 → 2` bump. 1 로드 시 단일 키를 현재 graph_key로 흡수.

**Tech Stack:** Python 3.11 dataclass·JSON, pytest.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-11-hotfix-dump-design.md` §3

**Pre-condition:** master `6ebd03d` 이상. h5와 같은 파일 — h1 먼저 머지.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/persistent_state.py` | 수정 (`GraphState` + `PersistentState.per_graph` + schema_version 2 + 호환 흡수) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`_save_persistent_state`·`_apply_persistent_state` 멀티키) |
| `tests/app/test_persistent_state.py` | 확장 |
| `tests/app/test_main_window_persistence.py` | 확장 |

---

## Task 1: `GraphState` + multi-key 라운드트립 — TDD

**Files:**
- Modify: `src/t3dgraph/core/app/persistent_state.py`
- Modify: `tests/app/test_persistent_state.py` (또는 `tests/core/app/test_persistent_state.py`)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
def test_per_graph_round_trip() -> None:
    """multi-key 라운드트립."""
    from t3dgraph.core.app.persistent_state import GraphState
    state = PersistentState(
        schema_version=2,
        per_graph={
            "rootA/": GraphState(
                node_positions={"N1": (1.0, 2.0)},
                expanded_pin_paths=["N1.P"],
                connected_pins_only=True,
            ),
            "rootA/SubB": GraphState(
                node_positions={"M1": (3.0, 4.0)},
                fan_in_highlight=True,
            ),
        },
    )
    save_state("/test/f.t3d.txt", state)
    loaded, _ = load_state("/test/f.t3d.txt")  # h5 시그니처 변경
    # h1만 머지된 시점에는 load_state가 기존 시그니처일 수 있음 — adapt:
    # loaded = load_state("/test/f.t3d.txt")  # h5 이전
    assert loaded.schema_version == 2
    assert "rootA/" in loaded.per_graph
    assert loaded.per_graph["rootA/"].node_positions == {"N1": (1.0, 2.0)}
    assert loaded.per_graph["rootA/SubB"].fan_in_highlight is True


def test_schema_v1_absorbed_into_current_key() -> None:
    """schema_version=1 로드 시 단일 키를 빈 per_graph로 → MainWindow가 흡수."""
    # JSON 직접 작성 (v1 형식)
    import json
    from t3dgraph.core.app.persistent_state import _state_path
    p = _state_path("/test/legacy.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "schema_version": 1,
        "node_positions": [{"node": "N1", "x": 10.0, "y": 20.0}],
        "expanded_pin_paths": ["N1.P"],
        "connected_pins_only": True,
        "fan_in_highlight": False,
        "hidden_node_types": [],
    }), encoding="utf-8")
    loaded = load_state("/test/legacy.t3d.txt")
    # h5 이전: loaded는 PersistentState. h1만으론 호환 흡수 OFF — MainWindow에서 처리.
    # 본 plan h1에서는 load_state가 v1 dict를 그대로 v1 PersistentState로 빌드.
    assert loaded.schema_version == 1
    assert loaded.node_positions == {"N1": (10.0, 20.0)}
```

(h1·h5 분리되어 있고 load_state 시그니처는 h5에서 튜플로 바뀜 — h1 시점엔 기존 단일 반환 유지.)

- [ ] **Step 2: `GraphState` + `PersistentState.per_graph` 추가**

`src/t3dgraph/core/app/persistent_state.py`:

```python
@dataclass
class GraphState:
    """graph_key 단위 상태 — multi-subgraph 영속용."""
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_positions": [
                {"node": k, "x": v[0], "y": v[1]}
                for k, v in self.node_positions.items()
            ],
            "expanded_pin_paths": sorted(self.expanded_pin_paths),
            "connected_pins_only": self.connected_pins_only,
            "fan_in_highlight": self.fan_in_highlight,
            "hidden_node_types": sorted(self.hidden_node_types),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GraphState":
        return cls(
            node_positions={
                e["node"]: (float(e["x"]), float(e["y"]))
                for e in data.get("node_positions", [])
            },
            expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
            connected_pins_only=bool(data.get("connected_pins_only", False)),
            fan_in_highlight=bool(data.get("fan_in_highlight", False)),
            hidden_node_types=list(data.get("hidden_node_types", [])),
        )
```

`PersistentState`에 필드 추가 (그리고 `_SCHEMA_VERSION = 2`로 bump):

```python
_SCHEMA_VERSION = 2


@dataclass
class PersistentState:
    schema_version: int = _SCHEMA_VERSION
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)
    per_graph: dict[str, GraphState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "node_positions": [
                {"node": k, "x": v[0], "y": v[1]}
                for k, v in self.node_positions.items()
            ],
            "expanded_pin_paths": sorted(self.expanded_pin_paths),
            "connected_pins_only": self.connected_pins_only,
            "fan_in_highlight": self.fan_in_highlight,
            "hidden_node_types": sorted(self.hidden_node_types),
            "per_graph": {k: v.to_dict() for k, v in self.per_graph.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentState":
        version = data.get("schema_version", _SCHEMA_VERSION)
        if version == 1:
            # v1 — 기존 단일 필드만 살리고 per_graph 비움
            return cls(
                schema_version=1,
                node_positions={
                    e["node"]: (float(e["x"]), float(e["y"]))
                    for e in data.get("node_positions", [])
                },
                expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
                connected_pins_only=bool(data.get("connected_pins_only", False)),
                fan_in_highlight=bool(data.get("fan_in_highlight", False)),
                hidden_node_types=list(data.get("hidden_node_types", [])),
                per_graph={},
            )
        if version != _SCHEMA_VERSION:
            return cls()
        return cls(
            schema_version=version,
            per_graph={
                k: GraphState.from_dict(v)
                for k, v in data.get("per_graph", {}).items()
            },
        )
```

- [ ] **Step 3: 실행 — 통과 확인**

Run: `pytest tests/app/test_persistent_state.py -v`
Expected: 전 통과 (기존 + 신규).

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_persistent_state.py src/t3dgraph/core/app/persistent_state.py
git commit -m "feat(app): PersistentState v2 — per_graph dict for multi-subgraph (ω-A1)"
```

---

## Task 2: MainWindow multi-key save + v1 호환 흡수

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/app/test_main_window_persistence.py`

- [ ] **Step 1: 실패하는 통합 테스트 추가**

```python
def test_multi_subgraph_state_persists(qtbot, synth_t3d_file) -> None:
    """두 graph_key에 다른 토글 → 모두 복원."""
    from t3dgraph.core.app.view_state import ViewState
    w1 = MainWindow()
    qtbot.addWidget(w1)
    w1.open_path(synth_t3d_file)
    # 키 A
    w1._view_states["keyA/"] = ViewState(connected_pins_only=True)
    w1._view_states["keyB/Sub"] = ViewState(fan_in_highlight=True)
    w1._save_persistent_state()
    w1.close()
    # 재오픈
    w2 = MainWindow()
    qtbot.addWidget(w2)
    w2.open_path(synth_t3d_file)
    assert w2._view_states.get("keyA/").connected_pins_only is True
    assert w2._view_states.get("keyB/Sub").fan_in_highlight is True
```

- [ ] **Step 2: MainWindow 변경**

```python
def _save_persistent_state(self) -> None:
    if self._current_file_path is None:
        return
    from .persistent_state import GraphState   # 본 task에서 사용
    all_keys = set(self._view_states.keys())
    # layout_overrides 키도 합치기
    if hasattr(self.layout_overrides, "_by_graph"):
        all_keys |= set(self.layout_overrides._by_graph.keys())
    per_graph: dict[str, GraphState] = {}
    for key in all_keys:
        vs = self._view_states.get(key)
        if vs is None:
            from .view_state import ViewState
            vs = ViewState()
        per_graph[key] = GraphState(
            node_positions=dict(self.layout_overrides.all_for_graph(key)),
            expanded_pin_paths=list(vs.expanded_pin_paths),
            connected_pins_only=vs.connected_pins_only,
            fan_in_highlight=vs.fan_in_highlight,
            hidden_node_types=list(vs.hidden_node_types),
        )
    state = PersistentState(schema_version=2, per_graph=per_graph)
    save_state(self._current_file_path, state)


def _apply_persistent_state(self, path: str) -> None:
    from .persistent_state import GraphState
    state = load_state(path)
    # v1 호환 흡수
    if state.schema_version == 1 and not state.per_graph:
        current_key = self._current_graph_key()
        state.per_graph[current_key] = GraphState(
            node_positions=state.node_positions,
            expanded_pin_paths=state.expanded_pin_paths,
            connected_pins_only=state.connected_pins_only,
            fan_in_highlight=state.fan_in_highlight,
            hidden_node_types=state.hidden_node_types,
        )
    for key, gs in state.per_graph.items():
        for node, (x, y) in gs.node_positions.items():
            self.layout_overrides.set(key, node, x, y)
        from .view_state import ViewState
        vs = ViewState(
            connected_pins_only=gs.connected_pins_only,
            fan_in_highlight=gs.fan_in_highlight,
        )
        vs.expanded_pin_paths = set(gs.expanded_pin_paths)
        vs.hidden_node_types = set(gs.hidden_node_types)
        self._view_states[key] = vs
    self._rebuild_scene()
    self._sync_toolbar_to_current_view_state()
```

- [ ] **Step 3: 실행 — 통과 확인**

Run: `pytest tests -v`
Expected: 전 통과 (기존 ω 단일 키 라운드트립도 v2로 라운드트립 + v1 JSON 호환).

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_main_window_persistence.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): MainWindow multi-key save + v1 absorption (ω-A1)"
```

---

## Self-Review

- Spec §3 multi-key 직렬화 ✅
- Spec §3 schema_version 2 + v1 호환 ✅
- 회귀 — 기존 라운드트립 테스트 통과 ✅

## 완료 후

ω-A1 해소. h5는 본 슬라이스 머지 후 진입 (같은 파일).
