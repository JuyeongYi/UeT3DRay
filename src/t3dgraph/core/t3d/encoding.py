"""T3D 파일 텍스트 읽기 — BOM·UTF-16 인코딩 견고화 (cli·viewer 공유)."""
from __future__ import annotations
from pathlib import Path


def read_t3d_text(path: Path) -> str:
    """BOM·UTF-16 익스포트도 처리하는 견고한 텍스트 읽기."""
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")
