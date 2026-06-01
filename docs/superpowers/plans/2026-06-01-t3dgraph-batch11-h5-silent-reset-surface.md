# batch ⑪ h5 — 영속 상태 silent reset 가시화 (ω-A2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `load_state`가 폴백할 때(decode error / schema mismatch) 사용자에게 statusBar로 통지. 손상 파일은 `.bak`로 백업.

**Architecture:** `load_state(path) -> tuple[PersistentState, str | None]` — 두 번째 요소는 에러 사유. MainWindow가 사유 있으면 statusBar에 표시.

**Spec:** §7

**Pre-condition:** master에 **h1 머지 완료** — schema_version 2 도입 후 진입. `persistent_state.py` 공유.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/persistent_state.py` | 수정 (`load_state` 시그니처 튜플) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`_apply_persistent_state`가 사유 사용) |
| `tests/app/test_persistent_state.py` | 갱신 |

---

## Task 1: `load_state` 튜플 반환 + `.bak` 백업 — TDD

- [ ] **Step 1: 테스트 변경 + 신규**

```python
def test_load_state_returns_tuple_normal() -> None:
    save_state("/test/x.t3d.txt", PersistentState(connected_pins_only=True))
    state, error = load_state("/test/x.t3d.txt")
    assert error is None
    assert state.connected_pins_only is True  # v1 호환 (h1) 또는 per_graph (h1 머지 후 변환)


def test_load_state_missing_returns_empty_no_error() -> None:
    state, error = load_state("/non/existent/file.t3d.txt")
    assert state == PersistentState()
    assert error is None


def test_load_corrupted_json_backs_up_and_returns_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ broken", encoding="utf-8")
    state, error = load_state("/test/x.t3d.txt")
    assert state == PersistentState()
    assert error is not None and "JSON" in error
    # .bak 파일 생성
    bak = p.with_suffix(p.suffix + ".bak")
    assert bak.exists()


def test_load_future_version_returns_error_without_backup(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 999}', encoding="utf-8")
    state, error = load_state("/test/x.t3d.txt")
    assert state == PersistentState()
    assert error is not None and "schema_version" in error
    # 백업 안 함 (구조 자체는 멀쩡)
    bak = p.with_suffix(p.suffix + ".bak")
    assert not bak.exists()
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_persistent_state.py -v`
Expected: FAIL — `load_state` 단일 반환.

- [ ] **Step 3: `load_state` 갱신**

`src/t3dgraph/core/app/persistent_state.py`:

```python
def load_state(file_path: str) -> tuple[PersistentState, str | None]:
    """영속 상태 로드. 폴백 시 (빈 state, 사유) — 사유 None이면 정상."""
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState(), None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        bak = p.with_suffix(p.suffix + ".bak")
        try:
            p.replace(bak)
        except OSError:
            pass
        return PersistentState(), f"JSON 해독 실패 — {bak.name}으로 백업: {exc}"
    version = data.get("schema_version", _SCHEMA_VERSION)
    if version not in (1, _SCHEMA_VERSION):
        return PersistentState(), f"미지원 schema_version={version} — 무시"
    try:
        return PersistentState.from_dict(data), None
    except (KeyError, TypeError, ValueError) as exc:
        return PersistentState(), f"구조 오류 — 무시: {exc}"
```

- [ ] **Step 4: MainWindow 갱신**

`_apply_persistent_state`:

```python
def _apply_persistent_state(self, path: str) -> None:
    state, error = load_state(path)
    if error:
        self.statusBar().showMessage(
            f"영속 상태 로드 실패 — 디폴트로 폴백: {error}", 10000
        )
    # ... 기존 v1 흡수 + per_graph 적용
```

다른 호출부(`MainWindow._save_persistent_state` 등)는 load_state 미사용 — 변경 불필요.

- [ ] **Step 5: 실행**

Run: `pytest tests -v`
Expected: 전 통과 (튜플 시그니처로 갱신된 테스트 + 통합).

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_persistent_state.py src/t3dgraph/core/app/persistent_state.py src/t3dgraph/core/app/main_window.py
git commit -m "fix(app): surface load_state errors via statusBar + .bak backup (ω-A2)"
```

## 완료 후

ω-A2 해소. batch ⑪ 마감 후보.
