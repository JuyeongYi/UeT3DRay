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


def test_prefixed_digits_sorted() -> None:
    """Item_N 패턴 — digit 순서로 정렬."""
    pins = [_pin("Item_10"), _pin("Item_2"), _pin("Item_0"), _pin("Item_1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Item_0", "Item_1", "Item_2", "Item_10"]


def test_mixed_prefix_preserves_order() -> None:
    """prefix가 일관 안 하면 원순서 — 보수적 동작."""
    pins = [_pin("Item_0"), _pin("Element_0"), _pin("Item_1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Item_0", "Element_0", "Item_1"]


def test_underscore_only_prefix() -> None:
    pins = [_pin("Element_2"), _pin("Element_1"), _pin("Element_0")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Element_0", "Element_1", "Element_2"]


def test_camel_prefix() -> None:
    pins = [_pin("ItemAt2"), _pin("ItemAt0"), _pin("ItemAt1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["ItemAt0", "ItemAt1", "ItemAt2"]


def test_pure_digits_still_sorted() -> None:
    """기존 digit-only 동작 회귀 없음 (σ 슬라이스 결과 보존)."""
    pins = [_pin("10"), _pin("9"), _pin("0")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["0", "9", "10"]


def test_no_digit_suffix_preserves_order() -> None:
    """이름 끝이 digit이 아니면 원순서."""
    pins = [_pin("Alpha"), _pin("Beta"), _pin("Gamma")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Alpha", "Beta", "Gamma"]
