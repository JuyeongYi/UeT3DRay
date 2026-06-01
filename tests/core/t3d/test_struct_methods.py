"""⑫-c3 — Struct.find_path / find_first 메서드."""
from __future__ import annotations
from t3dgraph.core.t3d.values import Struct, Scalar, parse_value


def _s(text: str) -> Struct:
    v = parse_value(text)
    assert isinstance(v, Struct)
    return v


def test_find_path_hits() -> None:
    s = _s("(A=(B=hello))")
    assert s.find_path("A", "B") == "hello"


def test_find_path_misses_when_intermediate_missing() -> None:
    s = _s("(A=(C=hello))")
    assert s.find_path("A", "B") is None


def test_find_path_misses_when_leaf_not_scalar() -> None:
    s = _s("(A=(B=(X=1)))")
    assert s.find_path("A", "B") is None


def test_find_path_single_key() -> None:
    s = _s("(Foo=bar)")
    assert s.find_path("Foo") == "bar"


def test_find_first_hits_shallow() -> None:
    s = _s("(X=found)")
    assert s.find_first("X") == "found"


def test_find_first_hits_deep() -> None:
    s = _s("(A=(B=(Target=deep)))")
    assert s.find_first("Target") == "deep"


def test_find_first_misses_beyond_max_depth() -> None:
    # depth=0 → finds only direct children (max_depth=1 would need depth tracking)
    s = _s("(A=(B=(C=(Target=tooDeep))))")
    assert s.find_first("Target", max_depth=1) is None


def test_find_first_returns_first_match() -> None:
    s = _s("(A=(Target=first), B=(Target=second))")
    assert s.find_first("Target") == "first"
