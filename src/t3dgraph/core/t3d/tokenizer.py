"""T3D 텍스트를 들여쓰기를 보존한 줄 단위로 분해한다."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    number: int   # 1-based 원본 줄 번호
    indent: int   # 선행 공백 수
    text: str     # strip된 줄 내용


def tokenize_lines(src: str) -> list[Line]:
    out: list[Line] = []
    for i, raw in enumerate(src.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        indent = len(raw) - len(raw.lstrip())
        out.append(Line(number=i, indent=indent, text=stripped))
    return out
