"""g2 (F22) — 실행 핀 우선 정렬."""
from t3dgraph.core.base.graph_model import Pin
from t3dgraph.plugins.rigvm.interpreter import _sort_pins_exec_first


def _p(name: str, exec_: bool = False) -> Pin:
    return Pin(name=name, cpp_type=None, direction=None, is_execution=exec_)


def test_exec_pin_moves_to_front() -> None:
    pins = [_p("A"), _p("B"), _p("Exec", exec_=True), _p("C")]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["Exec", "A", "B", "C"]


def test_multiple_execs_preserve_relative_order() -> None:
    pins = [_p("A"), _p("Main", exec_=True), _p("B"), _p("Completed", exec_=True)]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["Main", "Completed", "A", "B"]


def test_no_exec_pins_no_change() -> None:
    pins = [_p("A"), _p("B"), _p("C")]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["A", "B", "C"]


def test_all_exec_pins_no_change() -> None:
    pins = [_p("Main", True), _p("Loop", True)]
    result = _sort_pins_exec_first(pins)
    assert [p.name for p in result] == ["Main", "Loop"]


def test_empty_list() -> None:
    assert _sort_pins_exec_first([]) == []
