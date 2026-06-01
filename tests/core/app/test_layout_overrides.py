"""⑪-A1 — LayoutOverrides.graph_keys() public API."""
from t3dgraph.core.app.layout_overrides import LayoutOverrides


def test_graph_keys_returns_current_keys() -> None:
    lo = LayoutOverrides()
    lo.set("graph-A", "N1", 1.0, 2.0)
    lo.set("graph-B", "N1", 3.0, 4.0)
    assert set(lo.graph_keys()) == {"graph-A", "graph-B"}


def test_graph_keys_empty_when_no_overrides() -> None:
    assert list(LayoutOverrides().graph_keys()) == []
