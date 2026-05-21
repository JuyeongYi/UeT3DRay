"""GraphStack — multi-root + drilldown."""
from __future__ import annotations

from t3dgraph.core.app.graph_stack import GraphStack
from t3dgraph.core.base.graph_model import GraphModel


def test_initial_empty():
    s = GraphStack()
    assert s.current() is None
    assert s.segments() == []
    assert s.roots() == []


def test_push_and_current():
    g = GraphModel(label="root")
    s = GraphStack()
    s.open_root(g)
    assert s.current() is g
    assert s.segments() == ["root"]


def test_push_child_and_pop():
    a = GraphModel(label="A")
    b = GraphModel(label="A/B", parent_node="N")
    s = GraphStack()
    s.open_root(a)
    s.push(b)
    assert s.current() is b
    assert s.segments() == ["A", "A/B"]
    s.pop()
    assert s.current() is a


def test_pop_at_root_noop():
    g = GraphModel(label="A")
    s = GraphStack()
    s.open_root(g)
    s.pop()                       # 루트는 유지
    assert s.current() is g


def test_jump_to_index():
    s = GraphStack()
    a = GraphModel(label="A")
    b = GraphModel(label="B")
    c = GraphModel(label="C")
    s.open_root(a); s.push(b); s.push(c)
    s.jump_to(0)
    assert s.current() is a
    assert s.segments() == ["A"]


def test_push_on_empty_stack_raises():
    import pytest
    s = GraphStack()
    with pytest.raises(RuntimeError, match="open_root"):
        s.push(GraphModel(label="x"))


def test_push_after_open_root_works():
    s = GraphStack()
    s.open_root(GraphModel(label="root"))
    s.push(GraphModel(label="child"))
    assert s.current().label == "child"


def test_close_root_removes_and_adjusts_index():
    s = GraphStack()
    s.open_root(GraphModel(label='A'))
    s.open_root(GraphModel(label='B'))
    s.open_root(GraphModel(label='C'))
    s.select_root(1)
    s.close_root(0)
    assert [r.label for r in s.roots()] == ['B', 'C']
    assert s.current().label == 'B'


def test_close_current_root_falls_back_to_neighbor():
    s = GraphStack()
    s.open_root(GraphModel(label='A'))
    s.open_root(GraphModel(label='B'))
    s.close_root(1)
    assert s.current().label == 'A'


def test_close_last_root_makes_current_none():
    s = GraphStack()
    s.open_root(GraphModel(label='A'))
    s.close_root(0)
    assert s.current() is None
    assert s.roots() == []


def test_open_new_root_adds_to_stack_list():
    """파일 여러 개 열기 — 별도 루트를 스택 리스트에 추가."""
    s = GraphStack()
    s.open_root(GraphModel(label="file1"))
    s.open_root(GraphModel(label="file2"))
    roots = s.roots()
    assert [r.label for r in roots] == ["file1", "file2"]
    assert s.current().label == "file2"
