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
    qtbot.wait(50)
    assert w.pin_colors is not None
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
    qtbot.wait(50)
    assert w.pin_colors is not None
    assert "[[broken" in (tmp_path / "pin_colors.toml").read_text(encoding="utf-8")
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
    qtbot.wait(50)
    assert called == []


def test_dialog_not_called_during_init(qtbot, tmp_path, monkeypatch) -> None:
    """다이얼로그가 __init__ 중에는 호출 안 됨 — h4 핵심 (ο-A2)."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    calls = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **kw: calls.append(1) or QMessageBox.No)
    w = MainWindow()
    qtbot.addWidget(w)
    assert calls == [], "다이얼로그가 __init__ 중 호출됨 — ο-A2 회귀"
    qtbot.wait(50)
    assert calls == [1]
