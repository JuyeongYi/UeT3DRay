"""ψ — GraphModel.find_pin + iter_pin_paths 단위."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin


def _p(name: str, subs: list[Pin] | None = None) -> Pin:
    return Pin(name=name, cpp_type=None, direction=None,
               subpins=subs or [])


def test_find_pin_top_level() -> None:
    a = _p("A")
    n = Node(name="N1", cls="X", pins=[a])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.A") is a


def test_find_pin_subpin() -> None:
    sub = _p("X")
    parent = _p("P", subs=[sub])
    n = Node(name="N1", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.P.X") is sub


def test_find_pin_deeply_nested() -> None:
    leaf = _p("Leaf")
    mid = _p("Mid", subs=[leaf])
    parent = _p("Parent", subs=[mid])
    n = Node(name="N1", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.Parent.Mid.Leaf") is leaf


def test_find_pin_missing_node() -> None:
    g = GraphModel(nodes=[Node(name="N1", cls="X", pins=[_p("A")])])
    assert g.find_pin("Missing.A") is None


def test_find_pin_missing_pin() -> None:
    g = GraphModel(nodes=[Node(name="N1", cls="X", pins=[_p("A")])])
    assert g.find_pin("N1.NotThere") is None


def test_find_pin_empty_path() -> None:
    g = GraphModel()
    assert g.find_pin("") is None


def test_iter_pin_paths_all() -> None:
    n = Node(name="N1", cls="X",
             pins=[_p("P", subs=[_p("X"), _p("Y")]), _p("Q")])
    g = GraphModel(nodes=[n])
    paths = list(g.iter_pin_paths())
    assert paths == ["N1.P", "N1.P.X", "N1.P.Y", "N1.Q"]


def test_iter_pin_paths_filtered_by_node() -> None:
    n1 = Node(name="N1", cls="X", pins=[_p("A")])
    n2 = Node(name="N2", cls="X", pins=[_p("B")])
    g = GraphModel(nodes=[n1, n2])
    paths = list(g.iter_pin_paths(node_name="N2"))
    assert paths == ["N2.B"]


def test_iter_pin_paths_filtered_missing_node_empty() -> None:
    g = GraphModel(nodes=[Node(name="N1", cls="X", pins=[_p("A")])])
    assert list(g.iter_pin_paths(node_name="MissingNode")) == []


def test_pin_iter_paths_no_subpins() -> None:
    p = _p("MyPin")
    assert list(p.iter_paths("Node")) == ["Node.MyPin"]


def test_pin_iter_paths_with_subpins() -> None:
    p = _p("P", subs=[_p("X"), _p("Y")])
    assert list(p.iter_paths("N")) == ["N.P", "N.P.X", "N.P.Y"]


def test_pin_iter_paths_deeply_nested() -> None:
    deep = _p("D")
    mid = _p("M", subs=[deep])
    top = _p("T", subs=[mid])
    assert list(top.iter_paths("N")) == ["N.T", "N.T.M", "N.T.M.D"]
