# batch ⑩ υ (upsilon) — 툴바 desync 해소 (τ-A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 탭 전환 시 toolbar 액션(`connected_only`/`fan_in_highlight`) 체크 상태가 현재 탭 ViewState로 동기화. 사용자 다음 클릭이 의도와 반대로 가는 latent UX 결함 해소.

**Architecture:** `_on_tab_change` 끝에서 `_sync_toolbar_to_current_view_state` 호출. helper는 `QSignalBlocker`로 토글 핸들러 중복 발사 차단.

**Tech Stack:** PySide6 (`QSignalBlocker`, `QAction`), pytest + pytest-qt.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-10-hotfix-design.md` §5

**Pre-condition:** master `d07a130` 이상. ω가 본 슬라이스의 helper에 의존 — υ를 먼저 머지.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/main_window.py` | 수정 (`_sync_toolbar_to_current_view_state` helper + `_on_tab_change` 호출) |
| `tests/app/test_per_tab_view_state.py` | 확장 (toolbar 동기화 2건) |

---

## Task 1: `_sync_toolbar_to_current_view_state` helper + `_on_tab_change` 통합

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `tests/app/test_per_tab_view_state.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/app/test_per_tab_view_state.py` (또는 τ가 만든 위치) 끝에 추가:

```python
def test_toolbar_action_synced_on_tab_switch(qtbot) -> None:
    """탭 전환 시 toolbar QAction 체크 상태가 현재 탭 ViewState로 동기화."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    # 탭1(A) 활성에서 connected_only ON
    w._tab_bar.setCurrentIndex(0)
    w.set_view_mode("connected_only", True)
    action = w._view_mode_actions["connected_only"]
    assert action.isChecked() is True
    # 탭2(B)로 전환 — 액션 체크 OFF (B의 ViewState는 디폴트)
    w._tab_bar.setCurrentIndex(1)
    assert action.isChecked() is False, "툴바 desync — τ-A1 회귀"
    # 탭1로 복귀 — 액션 체크 다시 ON
    w._tab_bar.setCurrentIndex(0)
    assert action.isChecked() is True


def test_toolbar_sync_does_not_trigger_double_toggle(qtbot) -> None:
    """탭 전환의 setChecked 동기화가 _on_view_mode를 발사하지 않음."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    w._tab_bar.setCurrentIndex(0)
    w.set_view_mode("connected_only", True)
    # 탭2로 전환 — 동기화가 B의 ViewState를 토글하지 않음
    w._tab_bar.setCurrentIndex(1)
    assert w.current_view_state().connected_pins_only is False
    # 탭1로 복귀 — A의 ViewState도 그대로 (도로 켜진 채)
    w._tab_bar.setCurrentIndex(0)
    assert w.current_view_state().connected_pins_only is True
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_per_tab_view_state.py::test_toolbar_action_synced_on_tab_switch -v`
Expected: FAIL — action.isChecked()가 탭 전환 후 동기화 안 됨.

- [ ] **Step 3: helper + `_on_tab_change` 통합**

`src/t3dgraph/core/app/main_window.py` 상단 import 추가:

```python
from PySide6.QtCore import Qt, QSignalBlocker
```

(`QSignalBlocker` 추가 — `Qt` 이미 있음.)

`_on_tab_change` 메서드 끝부분에 추가 (return 또는 함수 끝 직전):

```python
def _on_tab_change(self, index: int) -> None:
    if index < 0 or index >= len(self.graph_stack.roots()):
        return
    self.graph_stack.select_root(index)
    self._render_current()
    self._sync_toolbar_to_current_view_state()
```

helper 메서드 추가 (`_render_current` 근처 또는 `_on_tab_change` 다음):

```python
def _sync_toolbar_to_current_view_state(self) -> None:
    """toolbar 액션 체크 상태를 현재 탭 ViewState로 동기화.

    QSignalBlocker로 setChecked가 toggled 시그널을 트리거해
    _on_view_mode가 다시 호출되는 중복 발사를 차단한다.
    """
    vs = self.current_view_state()
    for mode_id, value in (
        ("connected_only", vs.connected_pins_only),
        ("fan_in_highlight", vs.fan_in_highlight),
    ):
        action = self._view_mode_actions.get(mode_id)
        if action is None:
            continue
        blocker = QSignalBlocker(action)
        action.setChecked(value)
        del blocker  # 명시적 해제 — context manager 대안
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_per_tab_view_state.py -v`
Expected: 전 통과 (기존 τ 테스트 + 신규 2건).

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 6: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

두 t3d 파일 열어 탭1·탭2 생성. 탭1에서 "연결된 핀만" ON → 탭2 전환 시 액션 체크 OFF (탭2 ViewState 디폴트) → 탭1 복귀 시 액션 다시 ON.

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_per_tab_view_state.py src/t3dgraph/core/app/main_window.py
git commit -m "fix(app): sync toolbar action checked state on tab change (τ-A1)"
```

---

## Self-Review 체크리스트

- Spec §5.1 `_sync_toolbar_to_current_view_state` helper — Task 1 ✅
- Spec §5.1 `QSignalBlocker`로 중복 발사 차단 — Task 1 ✅
- Spec §5.2 두 신규 테스트 (sync + no-double-toggle) — Task 1 ✅
- PRESERVE-ALL — UI 상태만 ✅
- ω 의존성: ω가 본 helper 사용 가능 (머지 후) — 본 plan 머지 후 ω 진입 OK

---

## 완료 후

- improver 자동 리뷰 → backlog
- τ-A1 백로그 해소
- ω 슬라이스 진입 조건 충족 (`_sync_toolbar_to_current_view_state` master에 있음)
