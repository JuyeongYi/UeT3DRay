# batch ⑩ ο (omicron) — 팔레트 무음 처리 (μ-A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PinColorTable.load()` 실패 시 silent하게 노랑 fallback이 되는 함정 제거 — 다이얼로그·statusBar·번들 폴백으로 사용자에게 가시화.

**Architecture:** `PinColorTable._load_bundled_defaults()` 신설로 사용자 파일 무시 번들 직접 로드 경로 노출. `MainWindow.__init__`가 `PinColorTable.load()` 예외 잡아 다이얼로그(Yes=리셋, No=in-memory 디폴트 + statusBar).

**Tech Stack:** Python 3.11 (`tomllib`), PySide6 (`QMessageBox`), pytest + pytest-qt.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-10-hotfix-design.md` §4

**Pre-condition:** master `d07a130` 이상. 다른 슬라이스와 파일 충돌 없음 (`main_window.py`·`pin_colors.py` 만짐, 다른 슬라이스 영역과 별개).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/pin_colors.py` | 수정 (`_load_bundled_defaults` 신설) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`__init__`에서 try/except + `_handle_palette_load_failure`) |
| `tests/app/test_pin_colors.py` | 확장 (실패 케이스) |
| `tests/app/test_main_window_palette_failure.py` | 신규 |

---

## Task 1: `_load_bundled_defaults` — TDD

**Files:**
- Modify: `tests/app/test_pin_colors.py` (또는 신규 별도 파일)
- Modify: `src/t3dgraph/core/app/pin_colors.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/app/test_pin_colors.py` (μ에서 생성된 파일)에 추가. 실제 위치는 μ 결과에 따라 `tests/core/app/test_pin_colors.py`일 수도 있음 — 둘 중 존재하는 곳에 추가:

```python
def test_load_failure_raises(tmp_path, monkeypatch) -> None:
    """깨진 TOML이면 PinColorTable.load()가 예외 raise — silent 폴백 X."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[[broken syntax", encoding="utf-8")
    with pytest.raises(Exception):  # tomllib.TOMLDecodeError 또는 그 부모
        PinColorTable.load()


def test_load_bundled_defaults_ignores_user_file(tmp_path, monkeypatch) -> None:
    """_load_bundled_defaults는 사용자 파일 무시하고 번들에서 직접 로드."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[[broken", encoding="utf-8")
    table = PinColorTable._load_bundled_defaults()
    # 번들 디폴트의 bool 색 확인
    assert table.resolve("bool").color.name().upper() == "#A02020"


def test_load_bundled_defaults_when_user_file_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    # 사용자 파일 없음
    table = PinColorTable._load_bundled_defaults()
    assert table.resolve("float").color.name().upper() == "#7AC74F"
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_pin_colors.py::test_load_bundled_defaults_ignores_user_file -v`
Expected: FAIL — `_load_bundled_defaults` 미존재.

(`test_load_failure_raises`는 이미 PASS일 가능성 — `load()`가 자동 fallback하지 않으면 예외 그대로 propagate. 그러면 OK.)

- [ ] **Step 3: `_load_bundled_defaults` 추가**

`src/t3dgraph/core/app/pin_colors.py`의 `PinColorTable` 클래스에 classmethod 추가 (`reset_user_file` 다음):

```python
@classmethod
def _load_bundled_defaults(cls) -> "PinColorTable":
    """번들 디폴트를 사용자 파일 무시하고 직접 로드한다 — load 실패 폴백용."""
    with cls._bundle_path().open("rb") as f:
        data = tomllib.load(f)
    palette = {k: QColor(v) for k, v in data.get("palette", {}).items()}
    bucket = dict(data.get("bucket", {}))
    special = data.get("special", {})
    return cls(
        palette=palette,
        bucket=bucket,
        exec_marker=special.get("exec_marker", "ExecuteContext"),
        array_marker=special.get("array_marker", "TArray<"),
    )
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_pin_colors.py -v`
Expected: 전 통과 (기존 + 신규 2-3건).

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_pin_colors.py src/t3dgraph/core/app/pin_colors.py
git commit -m "feat(app): PinColorTable._load_bundled_defaults for failure fallback (μ-A1 prep)"
```

---

## Task 2: MainWindow 다이얼로그 + statusBar fallback

**Files:**
- Create: `tests/app/test_main_window_palette_failure.py`
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_main_window_palette_failure.py`:

```python
"""ο (μ-A1) — MainWindow가 팔레트 로드 실패를 가시화."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QMessageBox

from t3dgraph.core.app.main_window import MainWindow
from t3dgraph.core.app.pin_colors import PinColorTable


def test_handles_broken_palette_with_user_reset(qtbot, tmp_path, monkeypatch) -> None:
    """다이얼로그에서 Yes(리셋) 선택 시 사용자 파일이 번들로 덮어쓰기."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: QMessageBox.Yes)
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.pin_colors is not None
    # 사용자 파일이 정상 (덮어쓰기됨)
    user_text = (tmp_path / "pin_colors.toml").read_text(encoding="utf-8")
    assert "[palette]" in user_text


def test_handles_broken_palette_with_user_no(qtbot, tmp_path, monkeypatch) -> None:
    """No 선택 시 in-memory 번들 폴백 + statusBar 메시지. 사용자 파일 보존."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: QMessageBox.No)
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.pin_colors is not None
    # 사용자 파일은 그대로 깨진 상태
    assert "[[broken" in (tmp_path / "pin_colors.toml").read_text(encoding="utf-8")
    # statusBar 메시지 확인
    assert "팔레트" in w.statusBar().currentMessage()


def test_normal_palette_no_dialog(qtbot, tmp_path, monkeypatch) -> None:
    """정상 TOML이면 다이얼로그 호출 없음."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    called = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: called.append(1) or QMessageBox.Yes)
    w = MainWindow()
    qtbot.addWidget(w)
    assert called == []  # 다이얼로그 미호출
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/app/test_main_window_palette_failure.py -v`
Expected: FAIL — `__init__`에서 load 실패 시 그냥 raise (또는 silent fallback).

- [ ] **Step 3: MainWindow 변경**

`src/t3dgraph/core/app/main_window.py` 상단 import 추가:

```python
import tomllib
from PySide6.QtWidgets import QMessageBox
```

(둘 다 이미 있을 수 있음 — 중복 OK.)

`__init__`의 `self.pin_colors = PinColorTable.load()` 줄을 다음으로 교체:

```python
try:
    self.pin_colors = PinColorTable.load()
except (tomllib.TOMLDecodeError, ValueError, OSError) as exc:
    self.pin_colors = self._handle_palette_load_failure(exc)
```

`_on_reset_palette` 또는 `_build_menu` 근처에 helper 메서드 추가:

```python
def _handle_palette_load_failure(self, exc: Exception) -> "PinColorTable":
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
        return PinColorTable.load()
    self.statusBar().showMessage(
        f"팔레트 로드 실패 — 디폴트로 폴백 (사용자 파일 미변경): {exc}", 10000
    )
    return PinColorTable._load_bundled_defaults()
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/app/test_main_window_palette_failure.py -v`
Expected: 3 passed

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과. 기존 MainWindow 통합 테스트(정상 TOML)는 다이얼로그 호출 없이 그대로 작동.

- [ ] **Step 6: 수동 검증 (선택)**

```bash
# 사용자 팔레트 일부러 깨기
# (Windows) %APPDATA%/t3dgraph/pin_colors.toml에 "[[broken" 추가
uv run t3dgraph-gui
```

다이얼로그가 뜨고, Yes/No에 따라 동작 확인.

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_main_window_palette_failure.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): MainWindow surfaces palette load failure with dialog (μ-A1)"
```

---

## Self-Review 체크리스트

- Spec §4.1 다이얼로그 + statusBar 폴백 — Task 2 ✅
- Spec §4.1 `_load_bundled_defaults` 신설 — Task 1 ✅
- Spec §4.2 테스트 (load fail · bundled load · MainWindow dialog Yes/No) — Task 1·2 ✅
- PRESERVE-ALL — 시각만 ✅

---

## 완료 후

- improver 자동 리뷰 → backlog
- μ-A1 백로그 해소
