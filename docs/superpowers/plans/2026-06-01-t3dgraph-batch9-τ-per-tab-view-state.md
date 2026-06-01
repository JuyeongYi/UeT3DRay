# batch ⑨ τ (tau) — Per-tab ViewState (F11) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `MainWindow.view_state` 1개를 `_view_states: dict[graph_key, ViewState]`로 분해해 탭별 토글 상태를 분리한다. 동시에 ν-B3(graph_key escape) 백로그를 해소한다.

**Architecture:** ν 슬라이스가 이미 도입한 `_current_graph_key()`를 재사용. `view_state` 직접 접근을 `current_view_state()` getter로 교체. `LayoutOverrides`와 동일 키로 인덱싱. 탭 닫기 시 키 prefix 매칭으로 정리.

**Tech Stack:** PySide6 (`QMainWindow`, `QTabBar`), pytest + pytest-qt. 외부 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` §7

**Pre-condition:** master `bd34968`(또는 그 이후) 기준. Spec 1 ν 완료(`71208c2`)되어 `_current_graph_key`·`LayoutOverrides` 존재.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/main_window.py` | 수정 (`_view_states` dict, `current_view_state()` getter, 모든 `self.view_state` → `self.current_view_state()`, `_on_tab_close`에서 키 정리, `_current_graph_key` escape) |
| `tests/app/test_per_tab_view_state.py` | 신규 |

---

## Task 1: `current_view_state()` 도입 + escape 강화

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 단위 테스트 작성**

`tests/app/test_per_tab_view_state.py`:

```python
"""F11 per-tab ViewState — 탭별 토글 상태 분리."""
from __future__ import annotations
from urllib.parse import quote

from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.view_state import ViewState


def _graph(label: str, parent: str | None = None) -> GraphModel:
    return GraphModel(
        nodes=[Node(name=f"{label}_N", cls="T", pins=[])],
        label=label, parent_node=parent,
    )


def test_view_state_per_tab_isolation(qtbot) -> None:
    """탭1의 connected_only 토글이 탭2 ViewState에 영향 없음."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    # 탭2(B) 활성 상태에서 토글
    vs_b = w.current_view_state()
    vs_b.connected_pins_only = True
    # 탭1로 전환
    w._tab_bar.setCurrentIndex(0)
    vs_a = w.current_view_state()
    assert vs_a.connected_pins_only is False, "탭 간 ViewState 공유 — F11 회귀"


def test_view_state_persists_across_tab_switch(qtbot) -> None:
    """탭1 토글 → 탭2로 갔다 다시 탭1 복귀 시 토글 상태 유지."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    w._tab_bar.setCurrentIndex(0)
    w.current_view_state().connected_pins_only = True
    w._tab_bar.setCurrentIndex(1)
    w._tab_bar.setCurrentIndex(0)
    assert w.current_view_state().connected_pins_only is True


def test_view_state_cleared_on_tab_close(qtbot) -> None:
    """탭 닫으면 해당 ViewState 항목 제거 — 메모리 누수 방지."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    key_b = w._current_graph_key()
    assert key_b in w._view_states
    w._tab_bar.setCurrentIndex(1)
    w._on_tab_close(1)
    assert key_b not in w._view_states


def test_graph_key_escapes_slash_in_label(qtbot) -> None:
    """label에 '/' 들어가도 키 충돌 없음 — ν-B3."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A/with/slash"))
    w.open_graph(_graph("A"))
    keys = list(w._view_states.keys())
    assert len(keys) == 2 and len(set(keys)) == 2, (
        f"label에 '/' 들어가 키 충돌: {keys}"
    )


def test_view_mode_toggle_affects_current_tab_only(qtbot) -> None:
    """toolbar 액션이 활성 탭만 변경."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    w._tab_bar.setCurrentIndex(0)
    w.set_view_mode("connected_only", True)
    # 탭2로 전환
    w._tab_bar.setCurrentIndex(1)
    assert w.current_view_state().connected_pins_only is False, (
        "set_view_mode가 모든 탭에 적용됨 — F11 회귀"
    )
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_per_tab_view_state.py -v`
Expected: FAIL — `current_view_state`/`_view_states` 미존재.

- [ ] **Step 3: `MainWindow` 변경**

`src/t3dgraph/core/app/main_window.py` 상단 import 추가:

```python
from urllib.parse import quote
```

`__init__` 내 `self.view_state = ViewState()` 줄을 다음으로 교체:

```python
self._view_states: dict[str, ViewState] = {}
self._fallback_view_state = ViewState()   # 그래프 없을 때 (브레드크럼·전체 펼침)
```

`__init__` 끝부분 (또는 `_render_current` 직전) 헬퍼 추가:

```python
def current_view_state(self) -> ViewState:
    """현재 그래프 키 기준의 ViewState. 없으면 생성."""
    key = self._current_graph_key()
    if not key:
        return self._fallback_view_state
    if key not in self._view_states:
        self._view_states[key] = ViewState()
    return self._view_states[key]
```

기존 `_current_graph_key()` 함수(ν 슬라이스에 추가됨)를 escape 강화:

```python
def _current_graph_key(self) -> str:
    current = self.graph_stack.current()
    if current is None:
        return ""
    label = quote(current.label or "(unlabeled)", safe="")
    parent = quote(current.parent_node or "", safe="")
    token = self._root_tokens.get(id(self.graph_stack.roots()[
        self._tab_bar.currentIndex()
    ]), "") if self.graph_stack.roots() else ""
    return f"{token}/{label}/{parent}"
```

(주의: 기존 `_current_graph_key`가 `_root_tokens` 등 다른 구조를 쓰면 그 구조 그대로 escape만 추가.)

기존 `self.view_state.*` 접근 모두 `self.current_view_state().*`로 치환. 주요 위치:

- `_on_view_mode` — `setter(checked)` 호출 시 setter가 `self.view_state.set_*` 메서드를 가리키면 fallback 망가짐. 라믕다 캡처를 갱신:
  
  기존:
  ```python
  toggles = (
      ("connected_only", "연결된 핀만",
       self.view_state.set_connected_pins_only, False),
      ("fan_in_highlight", "fan-in 강조",
       self.view_state.set_fan_in_highlight, True),
  )
  ```
  
  변경:
  ```python
  toggles = (
      ("connected_only", "연결된 핀만",
       lambda v: self.current_view_state().set_connected_pins_only(v), False),
      ("fan_in_highlight", "fan-in 강조",
       lambda v: self.current_view_state().set_fan_in_highlight(v), True),
  )
  ```

- `_on_expand_all_pins` / `_on_collapse_all_pins`:
  
  기존:
  ```python
  self.view_state.expand_all_pins(paths)
  self._rebuild_scene()
  ```
  
  변경:
  ```python
  self.current_view_state().expand_all_pins(paths)
  self._rebuild_scene()
  ```

- `_on_pin_toggle`:
  ```python
  self.current_view_state().toggle_pin_expanded(full_path)
  self._rebuild_scene()
  ```

- `_on_node_context_menu` 내 expand/collapse 액션, `_on_scene_selection`, `_on_search_changed`, `_on_type_toggled`, `_navigate_to`, `_render_current`, `_rebuild_scene` 등 — 모두 `current_view_state()` 사용. (한 번에 grep으로 `self.view_state`를 찾아 모두 치환.)

- `_rebuild_scene` / `_render_current`에서 `view_state=self.view_state` 인자를 `view_state=self.current_view_state()`로:
  
  ```python
  def _rebuild_scene(self) -> None:
      if self.graph is not None:
          self.scene.populate(
              self.graph, view_state=self.current_view_state(),
              flow=self._flow, pin_colors=self.pin_colors,
              layout_overrides=self.layout_overrides,
              graph_key=self._current_graph_key())
  ```

- `set_view_mode(mode_id, checked)` — toolbar 동기화 API. 기존 `action.setChecked(checked)`만 하므로 동작은 변경 없으나, 토글이 실제로 적용될 때 `current_view_state()` 사용은 위 `_on_view_mode` 라믕다에서 보장됨.

- `_on_tab_close` 끝부분에 ViewState 정리 추가:
  
  ```python
  def _on_tab_close(self, index: int) -> None:
      # ... 기존 로직 ...
      # 닫힌 탭의 ViewState 키 제거
      # 단순화: closing 시점에 current_graph_key가 닫힌 그래프를 가리키므로 먼저 키 캡처
      key_to_remove = self._current_graph_key()
      # 닫고
      self._tab_bar.blockSignals(True)
      self._tab_bar.removeTab(index)
      self._tab_bar.blockSignals(False)
      self.graph_stack.close_root(index)
      # ViewState 제거 (prefix 매칭 — 서브그래프 키도 같이 정리)
      stale = [k for k in self._view_states if k.startswith(key_to_remove + "/")
               or k == key_to_remove]
      for k in stale:
          del self._view_states[k]
      if self.graph_stack.current() is None:
          self.scene.clear()
          self.breadcrumb.set_segments([])
      else:
          self._render_current()
  ```

(주의: 기존 `_on_tab_close` 구조에 맞춰 변형. 핵심은 닫힌 graph_key를 기억해 `_view_states`에서 prefix 매칭 정리.)

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_per_tab_view_state.py -v`
Expected: 5 passed

- [ ] **Step 5: 회귀 풀스위트**

Run: `pytest tests -v`
Expected: 전체 통과. 특히 batch ② F1~F9 통합 흐름과 batch ⑨ ν의 노드 컨텍스트 메뉴 테스트가 살아있어야 함.

만약 회귀: `self.view_state` 잔존 위치 grep 또는 `current_view_state()`가 None을 반환하는 경로 점검.

- [ ] **Step 6: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

두 t3d 파일 열어 탭1·탭2 만든 뒤:
- 탭1에서 "연결된 핀만" ON → 탭2로 전환 → 토글 OFF 상태
- 탭1로 복귀 → 토글 ON 유지
- 탭1 닫기 → 탭2만 남고 메모리 누수 없음

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_per_tab_view_state.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): per-tab ViewState + graph_key URL-escape (F11, ν-B3)"
```

---

## Self-Review 체크리스트

- Spec §7.1 디자인: `_view_states: dict[graph_key, ViewState]` — Task 1 Step 3 ✅
- Spec §7.1 `current_view_state()` getter — Task 1 Step 3 ✅
- Spec §7.2 graph_key 통일 — `_current_graph_key()` 재사용 ✅
- Spec §7.2 ν-B3 escape — `urllib.parse.quote` 적용 + `test_graph_key_escapes_slash_in_label` ✅
- Spec §7.3 main_window 변경: 모든 `self.view_state` → `current_view_state()` ✅
- Spec §7.4 탭 닫기 시 정리 — `_on_tab_close`에서 prefix 매칭 ✅
- Spec §7.5 회귀 가드 + 신규 통합 테스트 5건 — Task 1 ✅
- PRESERVE-ALL — 상태 분리만 ✅

---

## 완료 후

머지 후:
- improver 자동 리뷰 → backlog
- ν-B3(graph_key escape) 백로그 항목 해소 — backlog 표시 갱신
- 본 슬라이스는 π·φ와 독립 — 1차 사이클 종료 단계
