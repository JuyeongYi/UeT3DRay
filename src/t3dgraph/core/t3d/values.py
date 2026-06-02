"""T3D 속성값의 재귀 하강 파서."""
from __future__ import annotations
from dataclasses import dataclass


class Value:
    """모든 값 노드의 베이스."""


@dataclass(frozen=True)
class Scalar(Value):
    text: str


@dataclass(frozen=True)
class QuotedString(Value):
    text: str


@dataclass(frozen=True)
class Struct(Value):
    items: list[tuple[str, "Value"]]

    def find_path(self, *keys: str) -> str | None:
        """키 경로를 따라 중첩 Struct를 탐색해 최종 리프 텍스트 반환. 없으면 None."""
        cur: Value = self
        for key in keys:
            if not isinstance(cur, Struct):
                return None
            cur = next((v for k, v in cur.items if k == key), None)  # type: ignore[assignment]
            if cur is None:
                return None
        if isinstance(cur, (Scalar, QuotedString)):
            return cur.text
        return None

    def find_first(self, target_key: str, max_depth: int = 8) -> str | None:
        """DFS로 target_key를 최대 max_depth 수준까지 탐색해 텍스트 반환. 없으면 None."""
        for k, v in self.items:
            if k == target_key and isinstance(v, (Scalar, QuotedString)):
                return v.text
            if isinstance(v, Struct) and max_depth > 0:
                found = v.find_first(target_key, max_depth=max_depth - 1)
                if found is not None:
                    return found
        return None


@dataclass(frozen=True)
class ArrayLiteral(Value):
    items: list["Value"]


class ValueParseError(ValueError):
    def __init__(self, message: str, pos: int = 0):
        self.pos = pos
        super().__init__(message)


def parse_value(text: str) -> Value:
    p = _Parser(text)
    v = p.parse()
    p.skip_ws()
    if not p.at_end():
        raise ValueParseError(f"값 뒤에 남은 입력: {text!r}", p.i)
    return v


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0

    def at_end(self) -> bool:
        return self.i >= len(self.s)

    def skip_ws(self) -> None:
        while not self.at_end() and self.s[self.i] in " \t":
            self.i += 1

    def parse(self) -> Value:
        self.skip_ws()
        if self.at_end():
            return Scalar("")
        c = self.s[self.i]
        if c == '"':
            return self._quoted()
        if c == "(":
            return self._paren()
        return self._scalar()

    def _quoted(self) -> QuotedString:
        assert self.s[self.i] == '"'
        self.i += 1
        buf = []
        while not self.at_end():
            c = self.s[self.i]
            if c == "\\" and self.i + 1 < len(self.s):
                buf.append(self.s[self.i + 1])
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                return QuotedString("".join(buf))
            buf.append(c)
            self.i += 1
        raise ValueParseError("닫히지 않은 따옴표 문자열", self.i)

    def _scalar(self) -> Scalar:
        """Paren-balanced scalar: `(...)` block을 통째 흡수하면서
        outer terminator(`,` at depth 0, `)` at depth 0)에서만 종료.
        따옴표 내부는 모든 paren/comma 무시.
        """
        start = self.i
        depth = 0
        while not self.at_end():
            c = self.s[self.i]
            if c == '"':
                # quoted segment 안전 통과
                self.i += 1
                while not self.at_end() and self.s[self.i] != '"':
                    if self.s[self.i] == "\\" and self.i + 1 < len(self.s):
                        self.i += 2
                        continue
                    self.i += 1
                if not self.at_end():
                    self.i += 1   # 닫는 "
                continue
            if c == "(":
                depth += 1
                self.i += 1
                continue
            if c == ")":
                if depth == 0:
                    break
                depth -= 1
                self.i += 1
                continue
            if c == "," and depth == 0:
                break
            self.i += 1
        return Scalar(self.s[start:self.i].strip())

    def _paren(self) -> Value:
        assert self.s[self.i] == "("
        self.i += 1
        self.skip_ws()
        if not self.at_end() and self.s[self.i] == ")":
            self.i += 1
            return Struct([])
        if self._looks_like_struct():
            return self._struct_body()
        return self._array_body()

    def _looks_like_struct(self) -> bool:
        j = self.i
        while j < len(self.s) and (self.s[j].isalnum() or self.s[j] in "_"):
            j += 1
        while j < len(self.s) and self.s[j] in " \t":
            j += 1
        return j < len(self.s) and self.s[j] == "="

    def _read_ident(self) -> str:
        start = self.i
        while not self.at_end() and (self.s[self.i].isalnum() or self.s[self.i] == "_"):
            self.i += 1
        return self.s[start:self.i]

    def _struct_body(self) -> Struct:
        items: list[tuple[str, Value]] = []
        while True:
            self.skip_ws()
            key = self._read_ident()
            self.skip_ws()
            if self.at_end() or self.s[self.i] != "=":
                raise ValueParseError("구조체 키 뒤 '=' 기대", self.i)
            self.i += 1
            val = self.parse()
            items.append((key, val))
            self.skip_ws()
            if self.at_end():
                raise ValueParseError("닫히지 않은 구조체", self.i)
            if self.s[self.i] == ",":
                self.i += 1
                continue
            if self.s[self.i] == ")":
                self.i += 1
                return Struct(items)
            raise ValueParseError("구조체에서 ',' 또는 ')' 기대", self.i)

    def _array_body(self) -> ArrayLiteral:
        items: list[Value] = []
        while True:
            val = self.parse()
            items.append(val)
            self.skip_ws()
            if self.at_end():
                raise ValueParseError("닫히지 않은 배열", self.i)
            if self.s[self.i] == ",":
                self.i += 1
                continue
            if self.s[self.i] == ")":
                self.i += 1
                return ArrayLiteral(items)
            raise ValueParseError("배열에서 ',' 또는 ')' 기대", self.i)
