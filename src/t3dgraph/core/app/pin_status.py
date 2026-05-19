"""핀 '변경됨' 휴리스틱 — 타입 zero-value 비교 (spec §7.4, 교체 가능 전략)."""
from __future__ import annotations
from ..base.graph_model import Pin

_NUMERIC = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float", "double",
}


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
    return v not in ("", "()", '""')
