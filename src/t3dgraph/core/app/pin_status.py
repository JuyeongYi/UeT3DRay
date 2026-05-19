"""핀 '변경됨' 휴리스틱 — 타입 zero-value 비교 (spec §7.4, 교체 가능 전략)."""
from __future__ import annotations
from ..base.graph_model import Pin
from ..t3d.values import parse_value, Scalar, Struct, ArrayLiteral, ValueParseError

_NUMERIC = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float", "double",
}


def _all_zero(value) -> bool:
    if isinstance(value, Scalar):
        s = value.text.strip()
        try:
            return float(s) == 0.0
        except ValueError:
            return s in ("", "0")
    if isinstance(value, Struct):
        return bool(value.items) and all(_all_zero(v) for _, v in value.items)
    if isinstance(value, ArrayLiteral):
        return all(_all_zero(v) for v in value.items)
    return False


def _is_zero_struct(v: str) -> bool:
    if not (v.startswith("(") and v.endswith(")")):
        return False
    try:
        return _all_zero(parse_value(v))
    except ValueParseError:
        return False


def is_changed_from_default(pin: Pin) -> bool:
    dv = pin.default_value
    if dv is None:
        return False
    v = dv.strip()
    cpp = pin.cpp_type or ""
    if cpp == "bool":
        return v.lower() not in ("false", "")
    if cpp in _NUMERIC:
        try:
            return float(v) != 0.0
        except ValueError:
            return v not in ("", "0")
    if cpp == "FName":
        return v.lower() not in ("none", "")
    if v in ("", "()", '""'):
        return False
    if _is_zero_struct(v):
        return False
    return True
