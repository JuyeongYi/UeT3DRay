"""F17 — _sort_array_subpins helper unit tests."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import Pin
from t3dgraph.plugins.rigvm.interpreter import _sort_array_subpins


def _pin(name: str, subs: list[Pin] | None = None) -> Pin:
    return Pin(name=name, cpp_type=None, direction=None,
               subpins=subs or [])


def test_all_digit_subpins_sorted_by_int_value() -> None:
    """digit-only subpin name이면 int 순서로."""
    pins = [_pin("10"), _pin("9"), _pin("8"), _pin("7"), _pin("6"),
            _pin("5"), _pin("4"), _pin("3"), _pin("2"), _pin("1"), _pin("0")]
    sorted_pins = _sort_array_subpins(pins)
    assert [p.name for p in sorted_pins] == [str(i) for i in range(11)]


def test_mixed_names_not_sorted() -> None:
    """일부만 digit이면 원순서 유지 — struct 핀 등 비배열."""
    pins = [_pin("X"), _pin("Y"), _pin("Z")]
    sorted_pins = _sort_array_subpins(pins)
    assert [p.name for p in sorted_pins] == ["X", "Y", "Z"]


def test_partial_digit_not_sorted() -> None:
    """digit + 비-digit 섞이면 원순서 — 보수적 동작."""
    pins = [_pin("0"), _pin("X"), _pin("1")]
    sorted_pins = _sort_array_subpins(pins)
    assert [p.name for p in sorted_pins] == ["0", "X", "1"]


def test_empty_list_passthrough() -> None:
    assert _sort_array_subpins([]) == []


def test_single_digit_pin() -> None:
    assert [p.name for p in _sort_array_subpins([_pin("0")])] == ["0"]
