"""ValueParseError.pos 속성 (P1.5-A1)."""
from __future__ import annotations
import pytest
from t3dgraph.core.t3d.values import parse_value, ValueParseError


def test_value_parse_error_carries_pos():
    # "(X=1, Y)" — Y 뒤에 "=" 없음 → 구조체 파싱 에러
    with pytest.raises(ValueParseError) as exc_info:
        parse_value("(X=1, Y)")
    err = exc_info.value
    assert hasattr(err, "pos")
    assert isinstance(err.pos, int)
    assert err.pos >= 0


def test_pos_points_to_offending_position():
    src = "(X=1, Y=garbage"
    with pytest.raises(ValueParseError) as exc_info:
        parse_value(src)
    assert exc_info.value.pos >= src.index("Y")
