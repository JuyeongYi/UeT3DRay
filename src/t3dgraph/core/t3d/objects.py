"""Begin/End Object 트리와 Key=Value 속성 파싱."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from .tokenizer import tokenize_lines, Line
from .values import Value, parse_value, ValueParseError


class T3DParseError(Exception):
    def __init__(self, line: int, col: int, message: str):
        self.line, self.col = line, col
        super().__init__(f"line {line}:{col}: {message}")


@dataclass
class T3DObject:
    cls: str | None
    name: str | None
    export_path: str | None
    header_raw: str
    properties: dict[str, Value] = field(default_factory=dict)
    children: list["T3DObject"] = field(default_factory=list)
    line: int = 0


_HEADER_ATTR = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')
_CUSTOM_PROPERTIES_DIRECTIVE = re.compile(r'^CustomProperties\s+\w+\s*\(')


def _header_attrs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _HEADER_ATTR.finditer(text):
        key, val = m.group(1), m.group(2)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        out[key] = val
    return out


def parse_objects(src: str) -> list[T3DObject]:
    lines = tokenize_lines(src)
    pos = 0

    def parse_block(open_line: Line) -> tuple[T3DObject, int]:
        nonlocal pos
        attrs = _header_attrs(open_line.text)
        obj = T3DObject(
            cls=attrs.get("Class"),
            name=attrs.get("Name"),
            export_path=attrs.get("ExportPath"),
            header_raw=open_line.text,
            line=open_line.number,
        )
        while pos < len(lines):
            ln = lines[pos]
            if ln.text.startswith("Begin Object"):
                pos += 1
                child, _ = parse_block(ln)
                obj.children.append(child)
            elif ln.text == "End Object":
                pos += 1
                return obj, pos
            elif _CUSTOM_PROPERTIES_DIRECTIVE.match(ln.text):
                # UE EdGraph inline pin metadata — RigVM model 인터프리트와 무관, skip.
                # 그대로 attribute parser에 넘기면 '값 뒤에 남은 입력' 폭발.
                pos += 1
            elif "=" in ln.text:
                key, _, raw = ln.text.partition("=")
                try:
                    value = parse_value(raw.strip())
                except ValueParseError as e:
                    col = ln.indent + len(key) + 1 + e.pos
                    raise T3DParseError(ln.number, col, f"속성값 파싱 실패: {e}") from e
                obj.properties[key.strip()] = value
                pos += 1
            else:
                pos += 1
        raise T3DParseError(open_line.number, 0, "End Object 없이 입력 종료")

    objs: list[T3DObject] = []
    while pos < len(lines):
        ln = lines[pos]
        if ln.text.startswith("Begin Object"):
            pos += 1
            obj, pos = parse_block(ln)
            objs.append(obj)
        else:
            pos += 1
    return objs
