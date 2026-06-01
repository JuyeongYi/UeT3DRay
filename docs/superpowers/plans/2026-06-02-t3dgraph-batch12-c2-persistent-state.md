# batch ⑫ c2 — Persistent State Cleanup + Migration Toast + .bak 통일 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** ⑪-B1 + ψ-B2(ViewState 팩토리), ⑪-B2(from_dict v2 정규화), FEAT-50(migration toast), ⑪h5-A1/A2/B1(.bak 통일 + 회전) 한 슬라이스에 묶음.

**Architecture:** `ViewState.from_graph_state(gs)` 팩토리. `PersistentState.from_dict`가 v1 → v2 정규화하며 `migrated_from_v1` 플래그 설정. `load_state` 모든 폴백 분기를 `_backup_corrupted`로 통일, ts suffix 회전.

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-12-cleanup-design.md` §4

**Pre-condition:** master `0d5892c` 이상. c1/c3/c4와 병렬 가능.

---

## Task 1: ViewState.from_graph_state 팩토리

**Files:**
- Modify: `src/t3dgraph/core/app/view_state.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/app/test_view_state.py` 또는 신규

- [ ] **Step 1: 테스트**

```python
def test_view_state_from_graph_state() -> None:
    from t3dgraph.core.app.persistent_state import GraphState
    gs = GraphState(
        node_positions={"N1": (1.0, 2.0)},
        expanded_pin_paths=["N1.P", "N1.P.X"],
        connected_pins_only=True,
        fan_in_highlight=False,
        hidden_node_types=["RigVMUnitNode"],
    )
    vs = ViewState.from_graph_state(gs)
    assert vs.connected_pins_only is True
    assert vs.expanded_pin_paths == {"N1.P", "N1.P.X"}
    assert vs.hidden_node_types == {"RigVMUnitNode"}
```

- [ ] **Step 2: 구현**

`view_state.py`:

```python
@classmethod
def from_graph_state(cls, gs: "GraphState") -> "ViewState":
    """GraphState(영속 표현)에서 ViewState 생성."""
    vs = cls(
        connected_pins_only=gs.connected_pins_only,
        fan_in_highlight=gs.fan_in_highlight,
    )
    vs.expanded_pin_paths = set(gs.expanded_pin_paths)
    vs.hidden_node_types = set(gs.hidden_node_types)
    return vs
```

`main_window._apply_persistent_state`의 두 분기 → `ViewState.from_graph_state(gs)` 1줄.

- [ ] **Step 3: 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_view_state.py src/t3dgraph/core/app/view_state.py src/t3dgraph/core/app/main_window.py
git commit -m "refactor(app): ViewState.from_graph_state factory (⑪-B1 + ψ-B2)"
```

---

## Task 2: from_dict v2 정규화 + migrated_from_v1 플래그

**Files:**
- Modify: `src/t3dgraph/core/app/persistent_state.py`
- Modify: `tests/app/test_persistent_state.py`

- [ ] **Step 1: 테스트**

```python
def test_from_dict_v1_normalizes_to_v2() -> None:
    """v1 dict 입력 → v2 표현으로 정규화."""
    data = {
        "schema_version": 1,
        "node_positions": [{"node": "N1", "x": 1.0, "y": 2.0}],
        "expanded_pin_paths": ["N1.P"],
        "connected_pins_only": True,
        "fan_in_highlight": False,
        "hidden_node_types": [],
    }
    state = PersistentState.from_dict(data)
    assert state.schema_version == 2
    assert state.migrated_from_v1 is True
    assert "" in state.per_graph
    gs = state.per_graph[""]
    assert gs.connected_pins_only is True
    assert gs.node_positions == {"N1": (1.0, 2.0)}


def test_from_dict_v2_no_migration_flag() -> None:
    data = {
        "schema_version": 2,
        "per_graph": {
            "key/": {"node_positions": [], "expanded_pin_paths": [],
                     "connected_pins_only": False, "fan_in_highlight": False,
                     "hidden_node_types": []},
        },
    }
    state = PersistentState.from_dict(data)
    assert state.migrated_from_v1 is False


def test_migrated_flag_excluded_from_equality() -> None:
    a = PersistentState(per_graph={"k": GraphState()}, migrated_from_v1=True)
    b = PersistentState(per_graph={"k": GraphState()}, migrated_from_v1=False)
    assert a == b   # flag는 equality에 영향 없음
```

- [ ] **Step 2: 구현**

`persistent_state.py`:

```python
@dataclass
class PersistentState:
    schema_version: int = _SCHEMA_VERSION
    per_graph: dict[str, GraphState] = field(default_factory=dict)
    migrated_from_v1: bool = field(default=False, compare=False)
    # v1 호환 필드 — 외부 접근용 (정규화 후엔 비워둠)
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentState":
        version = data.get("schema_version", _SCHEMA_VERSION)
        if version == 1:
            gs = GraphState(
                node_positions={
                    e["node"]: (float(e["x"]), float(e["y"]))
                    for e in data.get("node_positions", [])
                },
                expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
                connected_pins_only=bool(data.get("connected_pins_only", False)),
                fan_in_highlight=bool(data.get("fan_in_highlight", False)),
                hidden_node_types=list(data.get("hidden_node_types", [])),
            )
            return cls(schema_version=2, per_graph={"": gs}, migrated_from_v1=True)
        if version != _SCHEMA_VERSION:
            return cls()
        return cls(
            schema_version=version,
            per_graph={k: GraphState.from_dict(v)
                       for k, v in data.get("per_graph", {}).items()},
        )
```

`main_window._apply_persistent_state` 단순화:

```python
def _apply_persistent_state(self, path: str) -> None:
    state, error = load_state(path)
    if error:
        self.statusBar().showMessage(f"영속 상태 로드 실패: {error}", 10000)
    if state.migrated_from_v1:
        self.statusBar().showMessage(
            "영속 상태 v1 → v2 자동 변환됨 (저장 시 v2로 덮어쓰기)", 4000
        )
    # "" 키(v1 잔재)를 현재 graph_key로 이관
    if "" in state.per_graph:
        state.per_graph[self._current_graph_key()] = state.per_graph.pop("")
    for key, gs in state.per_graph.items():
        for node, (x, y) in gs.node_positions.items():
            self.layout_overrides.set(key, node, x, y)
        self._view_states[key] = ViewState.from_graph_state(gs)
    self._rebuild_scene()
    self._sync_toolbar_to_current_view_state()
```

- [ ] **Step 3: 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_persistent_state.py src/t3dgraph/core/app/persistent_state.py src/t3dgraph/core/app/main_window.py
git commit -m "refactor(app): from_dict v2 normalization + migrated_from_v1 + toast (⑪-B2 + FEAT-50)"
```

---

## Task 3: .bak 통일 + timestamp 회전

**Files:**
- Modify: `src/t3dgraph/core/app/persistent_state.py`
- Modify: `tests/app/test_persistent_state.py`

- [ ] **Step 1: 테스트**

```python
def test_schema_mismatch_creates_bak(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 999}', encoding="utf-8")
    state, error = load_state("/test/x.t3d.txt")
    assert error is not None
    # .bak.{timestamp} 파일 존재
    baks = list(p.parent.glob(p.name + ".bak.*"))
    assert len(baks) == 1


def test_structure_error_creates_bak(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    # 정상 JSON이지만 PersistentState 구조 아님
    p.write_text('{"schema_version": 2, "per_graph": "not a dict"}',
                 encoding="utf-8")
    state, error = load_state("/test/x.t3d.txt")
    assert error is not None
    baks = list(p.parent.glob(p.name + ".bak.*"))
    assert len(baks) == 1


def test_bak_rotation_ts_suffix(tmp_path, monkeypatch) -> None:
    """동일 손상 두 번 — 두 백업 파일 보존."""
    import time
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ broken1", encoding="utf-8")
    load_state("/test/x.t3d.txt")
    time.sleep(1.1)   # ts 다르게
    p.write_text("{ broken2", encoding="utf-8")
    load_state("/test/x.t3d.txt")
    baks = list(p.parent.glob(p.name + ".bak.*"))
    assert len(baks) == 2
```

- [ ] **Step 2: 구현**

`persistent_state.py`:

```python
import datetime


def _backup_corrupted(p: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak.{ts}")
    try:
        p.replace(bak)
    except OSError:
        return p
    return bak


def load_state(file_path: str) -> tuple[PersistentState, str | None]:
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState(), None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        bak = _backup_corrupted(p)
        return PersistentState(), f"JSON 해독 실패 — {bak.name}으로 백업: {exc}"
    version = data.get("schema_version", _SCHEMA_VERSION)
    if version not in (1, _SCHEMA_VERSION):
        bak = _backup_corrupted(p)
        return PersistentState(), (
            f"미지원 schema_version={version} — {bak.name}으로 백업"
        )
    try:
        return PersistentState.from_dict(data), None
    except (KeyError, TypeError, ValueError) as exc:
        bak = _backup_corrupted(p)
        return PersistentState(), f"구조 오류 — {bak.name}으로 백업: {exc}"
```

- [ ] **Step 3: 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_persistent_state.py src/t3dgraph/core/app/persistent_state.py
git commit -m "fix(app): .bak backup uniform across all load_state failures + ts rotation (⑪h5-A1/A2/B1)"
```

## 완료 후

⑪-B1, ψ-B2, ⑪-B2, FEAT-50, ⑪h5-A1, ⑪h5-A2, ⑪h5-B1 모두 해소.
