"""PinColorTable 단위 테스트 — TOML 룩업·폴백."""
from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtGui import QColor

from t3dgraph.core.app.pin_colors import PinColorTable, ResolvedColor


@pytest.fixture
def bundled_table(tmp_path: Path, monkeypatch) -> PinColorTable:
    """번들 디폴트를 임시 사용자 dir로 로드."""
    monkeypatch.setattr(PinColorTable, "_user_dir", classmethod(lambda cls: tmp_path))
    return PinColorTable.load()


def test_bucket_lookup_bool(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("bool")
    assert r.color == QColor("#A02020")
    assert r.is_array is False


def test_bucket_lookup_int32(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("int32")
    assert r.color == QColor("#1FBEB6")


def test_bucket_lookup_struct(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("FRotator")
    assert r.color == QColor("#5B8FF9")


def test_special_exec_marker(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("FRigVMExecuteContext")
    assert r.color == QColor("#FFFFFF")


def test_special_array_inner_lookup(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("TArray<bool>")
    assert r.color == QColor("#A02020")
    assert r.is_array is True


def test_special_array_struct_inner(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("TArray<FRigElementKey>")
    assert r.color == QColor("#5B8FF9")
    assert r.is_array is True


def test_unknown_falls_back_to_default(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("FNotInBucket")
    assert r.color == QColor("#C8C878")
    assert r.is_array is False


def test_none_falls_back_to_default(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve(None)
    assert r.color == QColor("#C8C878")


def test_first_load_copies_bundle_to_user_dir(tmp_path: Path, monkeypatch) -> None:
    from importlib import resources as _res
    monkeypatch.setattr(PinColorTable, "_user_dir", classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    assert not user_file.exists()
    PinColorTable.load()
    assert user_file.exists()
    # 번들과 바이트 동일
    bundle_bytes = _res.files("t3dgraph.core.app.resources").joinpath("pin_colors.toml").read_bytes()
    assert user_file.read_bytes() == bundle_bytes


def test_reset_user_file_overwrites(tmp_path: Path, monkeypatch) -> None:
    from importlib import resources as _res
    monkeypatch.setattr(PinColorTable, "_user_dir", classmethod(lambda cls: tmp_path))
    PinColorTable.load()
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[palette]\ndefault = \"#000000\"\n", encoding="utf-8")
    PinColorTable.reset_user_file()
    bundle_bytes = _res.files("t3dgraph.core.app.resources").joinpath("pin_colors.toml").read_bytes()
    assert user_file.read_bytes() == bundle_bytes


def test_load_failure_raises(tmp_path: Path, monkeypatch) -> None:
    """깨진 TOML이면 PinColorTable.load()가 예외 raise — silent 폴백 X."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[[broken syntax", encoding="utf-8")
    with pytest.raises(Exception):  # tomllib.TOMLDecodeError 또는 그 부모
        PinColorTable.load()


def test_load_bundled_defaults_ignores_user_file(tmp_path: Path, monkeypatch) -> None:
    """_load_bundled_defaults는 사용자 파일 무시하고 번들에서 직접 로드."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[[broken", encoding="utf-8")
    table = PinColorTable._load_bundled_defaults()
    # 번들 디폴트의 bool 색 확인
    assert table.resolve("bool").color.name().upper() == "#A02020"


def test_load_bundled_defaults_when_user_file_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    # 사용자 파일 없음
    table = PinColorTable._load_bundled_defaults()
    assert table.resolve("float").color.name().upper() == "#7AC74F"
