"""F18 LayoutOverrides 단위 — 그래프 단위 노드 위치 보관."""
from __future__ import annotations

from t3dgraph.core.app.layout_overrides import LayoutOverrides


def test_get_missing_returns_none() -> None:
    lo = LayoutOverrides()
    assert lo.get("graph-A", "Node1") is None


def test_set_then_get() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    assert lo.get("graph-A", "Node1") == (100.0, 50.0)


def test_independent_graphs() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-B", "Node1", 200.0, 80.0)
    assert lo.get("graph-A", "Node1") == (100.0, 50.0)
    assert lo.get("graph-B", "Node1") == (200.0, 80.0)


def test_clear_node() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-A", "Node2", 30.0, 30.0)
    lo.clear_node("graph-A", "Node1")
    assert lo.get("graph-A", "Node1") is None
    assert lo.get("graph-A", "Node2") == (30.0, 30.0)


def test_clear_graph() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-B", "Node1", 200.0, 80.0)
    lo.clear_graph("graph-A")
    assert lo.get("graph-A", "Node1") is None
    assert lo.get("graph-B", "Node1") == (200.0, 80.0)


def test_all_for_graph() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "Node1", 100.0, 50.0)
    lo.set("graph-A", "Node2", 30.0, 30.0)
    assert lo.all_for_graph("graph-A") == {
        "Node1": (100.0, 50.0),
        "Node2": (30.0, 30.0),
    }


def test_all_for_graph_empty() -> None:
    lo = LayoutOverrides()
    assert lo.all_for_graph("none") == {}
