"""g11 (F31) — 자동 재배치 overlap 해소."""
from t3dgraph.core.app.auto_layout import resolve_overlaps


def test_no_overlap_no_change() -> None:
    """겹치지 않는 노드는 위치 유지."""
    positions = {"A": (0.0, 0.0), "B": (500.0, 0.0)}
    sizes = {"A": (200.0, 100.0), "B": (200.0, 100.0)}
    result = resolve_overlaps(positions, sizes)
    assert result["A"] == (0.0, 0.0)
    assert result["B"] == (500.0, 0.0)


def test_overlap_pushed_apart() -> None:
    """겹치는 노드를 밀어내기."""
    positions = {"A": (0.0, 0.0), "B": (100.0, 50.0)}
    sizes = {"A": (200.0, 100.0), "B": (200.0, 100.0)}
    result = resolve_overlaps(positions, sizes)
    a_x, a_y = result["A"]
    b_x, b_y = result["B"]
    a_w, a_h = sizes["A"]
    b_w, b_h = sizes["B"]
    horizontal_gap = abs(a_x - b_x) >= (a_w + b_w) / 2
    vertical_gap = abs(a_y - b_y) >= (a_h + b_h) / 2
    assert horizontal_gap or vertical_gap


def test_converges_within_iter_cap() -> None:
    """많은 겹침도 iteration cap(100) 안에 수렴 또는 종료."""
    positions = {f"N{i}": (0.0, 0.0) for i in range(10)}
    sizes = {f"N{i}": (200.0, 100.0) for i in range(10)}
    result = resolve_overlaps(positions, sizes, max_iter=100)
    assert len(result) == 10


def test_preserves_keys() -> None:
    positions = {"A": (10.0, 20.0)}
    sizes = {"A": (200.0, 100.0)}
    result = resolve_overlaps(positions, sizes)
    assert set(result.keys()) == {"A"}
