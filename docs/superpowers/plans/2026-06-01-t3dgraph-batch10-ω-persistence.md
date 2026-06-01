# batch ⑩ ω (omega) — 영속화 통일 (ν-A2 + τ-A2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 노드 위치(LayoutOverrides) + 뷰 상태(ViewState)를 파일 단위로 `~/.t3dgraph/state/{sha256(abs_path)}.json`에 영속화. 같은 t3d 재오픈 시 마지막 상태 복원.

**Architecture:** 신규 모듈 `persistent_state.py` — 자료구조(`PersistentState`) + load/save (atomic, JSON, sha256 키). `MainWindow`가 파일 열기 직후 load, 변경 신호 다수에서 디바운스(500ms) save.

**Tech Stack:** Python 3.11 (`hashlib`·`json`·표준), PySide6 (`QTimer`), pytest + pytest-qt.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-10-hotfix-design.md` §8

**Pre-condition:** master에 **υ 머지 완료** — `_sync_toolbar_to_current_view_state` helper 사용. υ 머지 전 진입 시 `AttributeError`. 본 plan 시작 시 `git log` 확인 필수.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/persistent_state.py` | 신규 (`PersistentState` + `load_state`/`save_state`) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`__init__` QTimer + load/save 시점 + 트리거 6곳) |
| `tests/app/test_persistent_state.py` | 신규 (단위 라운드트립·미존재·손상·미래 버전·atomic) |
| `tests/app/test_main_window_persistence.py` | 신규 (통합 라운드트립) |

---

## Task 1: `PersistentState` 자료구조 + 파일 IO — TDD

**Files:**
- Create: `tests/app/test_persistent_state.py`
- Create: `src/t3dgraph/core/app/persistent_state.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_persistent_state.py`:

```python
"""ω — PersistentState 단위 (라운드트립·폴백·atomic)."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from t3dgraph.core.app.persistent_state import (
    PersistentState, _state_path, load_state, save_state,
)


@pytest.fixture(autouse=True)
def _state_dir_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    return tmp_path


def test_state_path_uses_sha256_of_abs_path(tmp_path) -> None:
    p1 = _state_path("/some/path/a.t3d.txt")
    p2 = _state_path("/some/path/b.t3d.txt")
    assert p1 != p2
    assert p1.suffix == ".json"
    assert len(p1.stem) == 64  # sha256 hex


def test_save_then_load_round_trip() -> None:
    state = PersistentState(
        node_positions={"N1": (10.0, 20.0), "N2": (-5.5, 3.3)},
        expanded_pin_paths=["N1.P", "N1.P.X"],
        connected_pins_only=True,
        fan_in_highlight=False,
        hidden_node_types=["RigVMUnitNode"],
    )
    save_state("/test/file.t3d.txt", state)
    loaded = load_state("/test/file.t3d.txt")
    assert loaded == state


def test_load_missing_returns_empty() -> None:
    assert load_state("/non/existent/file.t3d.txt") == PersistentState()


def test_load_corrupted_json_returns_empty() -> None:
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ broken", encoding="utf-8")
    assert load_state("/test/x.t3d.txt") == PersistentState()


def test_future_schema_version_returns_empty() -> None:
    """미래 버전은 사용자 데이터 손실 차단을 위해 빈 상태."""
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 999}', encoding="utf-8")
    assert load_state("/test/x.t3d.txt") == PersistentState()


def test_save_is_atomic() -> None:
    """save 후 .tmp 파일 잔존 없음."""
    save_state("/test/x.t3d.txt", PersistentState(connected_pins_only=True))
    p = _state_path("/test/x.t3d.txt")
    assert p.exists()
    assert not p.with_suffix(p.suffix + ".tmp").exists()


def test_save_creates_parent_dir() -> None:
    save_state("/deep/path/file.t3d.txt", PersistentState())
    p = _state_path("/deep/path/file.t3d.txt")
    assert p.parent.exists()


def test_round_trip_preserves_position_floats() -> None:
    state = PersistentState(node_positions={"N1": (-1.5, 2.7e3)})
    save_state("/test/f.t3d.txt", state)
    loaded = load_state("/test/f.t3d.txt")
    assert loaded.node_positions == {"N1": (-1.5, 2700.0)}
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_persistent_state.py -v`
Expected: FAIL — 모듈 미존재.

- [ ] **Step 3: `persistent_state.py` 구현**

`src/t3dgraph/core/app/persistent_state.py`:

```python
"""파일 단위 영속 상태 — layout overrides + view state.

저장 위치: `~/.t3dgraph/state/{sha256(absolute_path)}.json`
형식: JSON (schema_version=1)
atomic write: tmp + replace
폴백: 손상·미래 버전 → 빈 상태 (사용자 데이터 손실 차단)
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


_SCHEMA_VERSION = 1


@dataclass
class PersistentState:
    """파일 단위 영속 상태."""
    schema_version: int = _SCHEMA_VERSION
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)

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
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentState":
        version = data.get("schema_version", _SCHEMA_VERSION)
        if version != _SCHEMA_VERSION:
            return cls()
        return cls(
            schema_version=version,
            node_positions={
                e["node"]: (float(e["x"]), float(e["y"]))
                for e in data.get("node_positions", [])
            },
            expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
            connected_pins_only=bool(data.get("connected_pins_only", False)),
            fan_in_highlight=bool(data.get("fan_in_highlight", False)),
            hidden_node_types=list(data.get("hidden_node_types", [])),
        )


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "t3dgraph" / "state"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "t3dgraph" / "state"


def _state_path(file_path: str) -> Path:
    abs_path = str(Path(file_path).resolve())
    digest = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()
    return _state_dir() / f"{digest}.json"


def load_state(file_path: str) -> PersistentState:
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState()
    try:
        with p.open("r", encoding="utf-8") as f:
            return PersistentState.from_dict(json.load(f))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return PersistentState()


def save_state(file_path: str, state: PersistentState) -> None:
    p = _state_path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
    tmp.replace(p)
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_persistent_state.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_persistent_state.py src/t3dgraph/core/app/persistent_state.py
git commit -m "feat(app): PersistentState + sha256-keyed JSON store (ω prep)"
```

---

## Task 2: MainWindow load 시점 통합

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: `_apply_persistent_state` + `open_path` 통합**

`src/t3dgraph/core/app/main_window.py` 상단 import 추가:

```python
from PySide6.QtCore import Qt, QTimer  # QTimer 추가
from .persistent_state import PersistentState, load_state, save_state
```

`__init__`에 추가 (`self.layout_overrides = LayoutOverrides()` 다음):

```python
self._save_state_timer = QTimer(self)
self._save_state_timer.setSingleShot(True)
self._save_state_timer.setInterval(500)
self._save_state_timer.timeout.connect(self._save_persistent_state)
self._current_file_path: str | None = None
```

`open_path` 메서드를 다음으로 교체:

```python
def open_path(self, path: str) -> None:
    self._current_file_path = path
    if self._open_handler is not None:
        self._open_handler(path)
    self._apply_persistent_state(path)
```

helper 추가 (`_render_current` 근처):

```python
def _apply_persistent_state(self, path: str) -> None:
    state = load_state(path)
    key = self._current_graph_key()
    for node, (x, y) in state.node_positions.items():
        self.layout_overrides.set(key, node, x, y)
    vs = self.current_view_state()
    vs.expanded_pin_paths = set(state.expanded_pin_paths)
    vs.connected_pins_only = state.connected_pins_only
    vs.fan_in_highlight = state.fan_in_highlight
    vs.hidden_node_types = set(state.hidden_node_types)
    self._rebuild_scene()
    self._sync_toolbar_to_current_view_state()   # υ helper 필수
```

- [ ] **Step 2: 회귀 확인**

Run: `pytest tests -v`
Expected: 전 통과. load_state가 미존재 시 빈 상태이므로 기존 흐름 영향 없음.

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): MainWindow loads persistent state on open_path (ω)"
```

---

## Task 3: MainWindow save 디바운스 + 트리거 6곳

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: `_save_persistent_state` + `_schedule_save_state` 추가**

`_apply_persistent_state` 다음에 추가:

```python
def _schedule_save_state(self) -> None:
    if self._current_file_path is not None:
        self._save_state_timer.start()

def _save_persistent_state(self) -> None:
    if self._current_file_path is None:
        return
    key = self._current_graph_key()
    vs = self.current_view_state()
    state = PersistentState(
        node_positions=dict(self.layout_overrides.all_for_graph(key)),
        expanded_pin_paths=list(vs.expanded_pin_paths),
        connected_pins_only=vs.connected_pins_only,
        fan_in_highlight=vs.fan_in_highlight,
        hidden_node_types=list(vs.hidden_node_types),
    )
    save_state(self._current_file_path, state)
```

- [ ] **Step 2: 변경 신호 6곳에 `_schedule_save_state` 호출**

각 핸들러 끝부분에 `self._schedule_save_state()` 추가:

1. `_on_node_moved` (드래그):

```python
def _on_node_moved(self, node_name: str, x: float, y: float) -> None:
    self.layout_overrides.set(self._current_graph_key(), node_name, x, y)
    self._schedule_save_state()
```

2. `_on_pin_toggle`:

```python
def _on_pin_toggle(self, full_path: str) -> None:
    self.current_view_state().toggle_pin_expanded(full_path)
    self._rebuild_scene()
    self._schedule_save_state()
```

3. `_on_view_mode` 끝:

```python
def _on_view_mode(self, setter, checked: bool, in_place: bool = False) -> None:
    setter(checked)
    if in_place and self._flow is not None:
        self.scene.apply_fan_in_highlight(
            set(self._flow.convergence_points), checked)
    else:
        self._rebuild_scene()
    self._schedule_save_state()
```

4. `_on_type_toggled`:

```python
def _on_type_toggled(self, type_name: str, hidden: bool) -> None:
    self.current_view_state().set_type_hidden(type_name, hidden)
    self.scene.apply_hidden_types(self.current_view_state().hidden_node_types)
    self._schedule_save_state()
```

5. `_invoke_node_action` 끝(각 분기 후):

```python
def _invoke_node_action(self, node_name: str, action: str) -> None:
    if action == "expand_all":
        ...
        self._rebuild_scene()
    elif action == "collapse_all":
        ...
        self._rebuild_scene()
    elif action == "reset_position":
        ...
        self._rebuild_scene()
    self._schedule_save_state()
```

6. `_on_expand_all_pins` / `_on_collapse_all_pins`:

```python
def _on_expand_all_pins(self) -> None:
    ...
    self._rebuild_scene()
    self._schedule_save_state()

def _on_collapse_all_pins(self) -> None:
    self.current_view_state().collapse_all_pins()
    self._rebuild_scene()
    self._schedule_save_state()
```

- [ ] **Step 3: 회귀 확인**

Run: `pytest tests -v`
Expected: 전 통과. `_save_state_timer`는 디바운스라 즉시 발사 안 함 — 기존 테스트가 디스크에 안 씀.

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): debounced persistent state save on 6 change triggers (ω)"
```

---

## Task 4: 통합 라운드트립 테스트

**Files:**
- Create: `tests/app/test_main_window_persistence.py`

- [ ] **Step 1: 통합 테스트 작성**

`tests/app/test_main_window_persistence.py`:

```python
"""ω — MainWindow 영속 상태 통합 (열기·변경·닫기·재오픈)."""
from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF

from t3dgraph.core.app.main_window import MainWindow


@pytest.fixture
def synth_t3d_file(tmp_path: Path) -> str:
    src = (
        'Begin Object Name="N1" Class=/Script/RigVMDeveloper.RigVMUnitNode\n'
        'End Object\n'
        'Begin Object Name="N2" Class=/Script/RigVMDeveloper.RigVMUnitNode\n'
        'End Object\n'
    )
    f = tmp_path / "sample.t3d.txt"
    f.write_text(src, encoding="utf-8")
    return str(f)


@pytest.fixture(autouse=True)
def _state_dir_isolation(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: state_dir)


def test_view_mode_persists_across_reopen(qtbot, synth_t3d_file) -> None:
    """connected_only 토글 → 닫기 → 재오픈 → 토글 ON 복원."""
    w1 = MainWindow()
    qtbot.addWidget(w1)
    w1.open_path(synth_t3d_file)
    w1.set_view_mode("connected_only", True)
    w1._save_persistent_state()   # 디바운스 우회
    w1.close()

    w2 = MainWindow()
    qtbot.addWidget(w2)
    w2.open_path(synth_t3d_file)
    assert w2.current_view_state().connected_pins_only is True
    assert w2._view_mode_actions["connected_only"].isChecked() is True


def test_node_position_persists_across_reopen(qtbot, synth_t3d_file) -> None:
    """노드 드래그 위치 → 재오픈 → 같은 위치."""
    w1 = MainWindow()
    qtbot.addWidget(w1)
    w1.open_path(synth_t3d_file)
    item = w1.scene.node_item("N1")
    assert item is not None
    item.setPos(QPointF(123.0, 45.0))
    w1._save_persistent_state()
    w1.close()

    w2 = MainWindow()
    qtbot.addWidget(w2)
    w2.open_path(synth_t3d_file)
    key = w2._current_graph_key()
    pos = w2.layout_overrides.get(key, "N1")
    assert pos == (123.0, 45.0)


def test_expanded_pin_paths_persist(qtbot, synth_t3d_file) -> None:
    """expanded set 라운드트립."""
    w1 = MainWindow()
    qtbot.addWidget(w1)
    w1.open_path(synth_t3d_file)
    w1.current_view_state().expanded_pin_paths.add("N1.SomePin")
    w1._save_persistent_state()
    w1.close()

    w2 = MainWindow()
    qtbot.addWidget(w2)
    w2.open_path(synth_t3d_file)
    assert "N1.SomePin" in w2.current_view_state().expanded_pin_paths


def test_no_state_file_yields_empty_defaults(qtbot, synth_t3d_file) -> None:
    """저장된 state 없으면 디폴트 — 기존 흐름."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_path(synth_t3d_file)
    vs = w.current_view_state()
    assert vs.connected_pins_only is False
    assert vs.expanded_pin_paths == set()
```

- [ ] **Step 2: 실행 — 통과 확인**

Run: `pytest tests/app/test_main_window_persistence.py -v`
Expected: 4 passed

- [ ] **Step 3: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과 (430 baseline + ω 신규 ~12건).

- [ ] **Step 4: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

t3d 파일 열기 → 노드 드래그·토글 → 종료 → 재기동 → 같은 파일 열기. 위치·토글 상태 복원 확인.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_main_window_persistence.py
git commit -m "test(app): persistence round-trip integration (ω)"
```

---

## Self-Review 체크리스트

- Spec §8.2 파일 위치·sha256 키 — Task 1 ✅
- Spec §8.3 PersistentState 자료구조 + to/from_dict — Task 1 ✅
- Spec §8.3 atomic save (tmp + replace) — Task 1 ✅
- Spec §8.3 미존재·손상·미래 버전 폴백 — Task 1 ✅
- Spec §8.4.1 load 시점 (`_apply_persistent_state`) — Task 2 ✅
- Spec §8.4.2 디바운스 save — Task 3 ✅
- Spec §8.4.3 트리거 6곳 — Task 3 ✅
- Spec §8.5 통합 라운드트립 — Task 4 ✅
- υ helper 의존 명시 — Plan 헤더 + Task 2 ✅
- PRESERVE-ALL — 저장된 상태 복원만 ✅

---

## 완료 후

- improver 자동 리뷰 → backlog
- ν-A2 + τ-A2 백로그 해소
- ψ는 같은 main_window를 만지므로 ω 머지 후 rebase 권장
