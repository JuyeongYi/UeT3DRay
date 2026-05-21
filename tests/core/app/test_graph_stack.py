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
    s.push(g)
    assert s.current() is g
    assert s.segments() == ["root"]


def test_push_child_and_pop():
    a = GraphModel(label="A")
    b = GraphModel(label="A/B", parent_node="N")
    s = GraphStack()
    s.push(a)
    s.push(b)
    assert s.current() is b
    assert s.segments() == ["A", "A/B"]
    s.pop()
    assert s.current() is a


def test_pop_at_root_noop():
    g = GraphModel(label="A")
    s = GraphStack()
    s.push(g)
    s.pop()                       # 루트는 유지
    assert s.current() is g


def test_jump_to_index():
    s = GraphStack()
    a = GraphModel(label="A")
    b = GraphModel(label="B")
    c = GraphModel(label="C")
    s.push(a); s.push(b); s.push(c)
    s.jump_to(0)
    assert s.current() is a
    assert s.segments() == ["A"]


def test_open_new_root_adds_to_stack_list():
    """파일 여러 개 열기 — 별도 루트를 스택 리스트에 추가."""
    s = GraphStack()
    s.open_root(GraphModel(label="file1"))
    s.open_root(GraphModel(label="file2"))
    roots = s.roots()
    assert [r.label for r in roots] == ["file1", "file2"]
    assert s.current().label == "file2"
