# batch ⑪ h4 — 팔레트 다이얼로그 타이밍 (ο-A2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `MainWindow.__init__`의 즉시 `QMessageBox.warning(...)`을 `QTimer.singleShot(0, ...)`로 메인 이벤트 루프 첫 반복 시점으로 지연. 윈도우 보인 뒤 다이얼로그.

**Architecture:** `__init__`에서 실패 시 `pin_colors`를 번들 디폴트로 설정 + 예외 보관. 이벤트 루프 진입 직후 `_show_palette_load_failure_dialog`로 다이얼로그.

**Spec:** §6

**Pre-condition:** master `6ebd03d` 이상. h1/h2/h3와 병렬.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/main_window.py` | 수정 (`__init__` 타이밍 + 다이얼로그 분리) |
| `tests/app/test_main_window_palette_failure.py` | 갱신 (qtbot의 event loop 진행) |

---

## Task 1: 다이얼로그 지연

- [ ] **Step 1: 기존 테스트 갱신 (qtbot wait)**

`tests/app/test_main_window_palette_failure.py`에서 다이얼로그가 `__init__` 직후가 아니라 이벤트 루프 첫 반복에서 뜨도록 변경:

```python
def test_handles_broken_palette_with_user_no(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: QMessageBox.No)
    w = MainWindow()
    qtbot.addWidget(w)
    # 이벤트 루프 단계 진행 — singleShot(0) 발사
    qtbot.wait(50)
    assert w.pin_colors is not None
    assert "[[broken" in (tmp_path / "pin_colors.toml").read_text(encoding="utf-8")
    # statusBar 메시지 확인
    assert "팔레트" in w.statusBar().currentMessage()


def test_handles_broken_palette_with_user_reset(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: QMessageBox.Yes)
    w = MainWindow()
    qtbot.addWidget(w)
    qtbot.wait(50)
    user_text = (tmp_path / "pin_colors.toml").read_text(encoding="utf-8")
    assert "[palette]" in user_text


def test_dialog_not_called_during_init(qtbot, tmp_path, monkeypatch) -> None:
    """다이얼로그가 __init__ 중에는 호출 안 됨 — h4 핵심."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    calls = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: calls.append(1) or QMessageBox.No)
    w = MainWindow()
    qtbot.addWidget(w)
    # __init__ 직후엔 다이얼로그 미호출 (singleShot pending)
    assert calls == [], "다이얼로그가 __init__ 중 호출됨 — ο-A2 회귀"
    qtbot.wait(50)
    assert calls == [1]  # 이벤트 루프 후 호출
```

- [ ] **Step 2: MainWindow 변경**

`__init__`의 try/except 블록 + 다이얼로그 호출:

```python
self.pin_colors = PinColorTable._load_bundled_defaults()
self._palette_load_exc = None
try:
    self.pin_colors = PinColorTable.load()
except (tomllib.TOMLDecodeError, ValueError, OSError) as exc:
    self._palette_load_exc = exc
    # pin_colors는 이미 bundled defaults
...
# 이벤트 루프 첫 반복 시점에 다이얼로그
if self._palette_load_exc is not None:
    QTimer.singleShot(0, self._show_palette_load_failure_dialog)
```

`_handle_palette_load_failure` 메서드를 `_show_palette_load_failure_dialog`로 변경:

```python
def _show_palette_load_failure_dialog(self) -> None:
    exc = self._palette_load_exc
    if exc is None:
        return
    msg = (
        f"핀 색 팔레트 파일을 읽지 못했습니다.\n"
        f"오류: {exc}\n\n"
        f"디폴트 팔레트로 리셋하시겠습니까?\n"
        f"(예: 사용자 파일을 번들 디폴트로 덮어쓰기)\n"
        f"(아니오: 이번 세션만 디폴트로 동작, 사용자 파일 보존)"
    )
    reply = QMessageBox.warning(
        self, "팔레트 로드 실패", msg,
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply == QMessageBox.Yes:
        PinColorTable.reset_user_file()
        self.pin_colors = PinColorTable.load()
        self._rebuild_scene()
    else:
        self.statusBar().showMessage(
            f"팔레트 로드 실패 — 디폴트로 폴백: {exc}", 10000
        )
    self._palette_load_exc = None
```

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_main_window_palette_failure.py -v`
Expected: 전 통과 (기존 + 신규 1건).

- [ ] **Step 4: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_main_window_palette_failure.py src/t3dgraph/core/app/main_window.py
git commit -m "fix(app): defer palette load failure dialog to event loop tick (ο-A2)"
```

## 완료 후

ο-A2 해소.
