from t3dgraph.core.app.items import collect_pin_rows
from t3dgraph.core.base.graph_model import Node, Pin


def _make_node():
    return Node(
        name="N",
        cls=None,
        pins=[
            Pin(name="ExecIn", cpp_type="FRigVMExecuteContext", direction="Input"),
            Pin(name="Struct", cpp_type="FVector", direction="Input",
                subpins=[
                    Pin(name="X", cpp_type="float", direction="Input"),
                    Pin(name="Y", cpp_type="float", direction="Input"),
                ]),
        ],
    )


def test_collect_rows_default_top_level_only():
    node = _make_node()
    rows = collect_pin_rows(node, connected_subtree=frozenset(),
                            connected_only=False, expanded=frozenset())
    paths = [r.path for r in rows]
    assert paths == ["N.ExecIn", "N.Struct"]
    assert all(r.has_dot for r in rows)


def test_collect_rows_expanded_parent_has_no_dot():
    node = _make_node()
    rows = collect_pin_rows(node, connected_subtree=frozenset(),
                            connected_only=False,
                            expanded=frozenset({"N.Struct"}))
    paths = [r.path for r in rows]
    assert paths == ["N.ExecIn", "N.Struct", "N.Struct.X", "N.Struct.Y"]
    by_path = {r.path: r for r in rows}
    assert by_path["N.Struct"].has_dot is False
    assert by_path["N.Struct.X"].has_dot is True
    assert by_path["N.Struct.Y"].has_dot is True


def test_connected_only_includes_parent_when_sub_connected():
    node = _make_node()
    rows = collect_pin_rows(
        node,
        connected_subtree=frozenset({"N.Struct", "N.Struct.X"}),
        connected_only=True,
        expanded=frozenset(),
    )
    paths = [r.path for r in rows]
    assert paths == ["N.Struct"]


def test_connected_only_with_expand_shows_both_but_no_dup_dot():
    node = _make_node()
    rows = collect_pin_rows(
        node,
        connected_subtree=frozenset({"N.Struct", "N.Struct.X"}),
        connected_only=True,
        expanded=frozenset({"N.Struct"}),
    )
    paths = [r.path for r in rows]
    assert paths == ["N.Struct", "N.Struct.X"]
    by_path = {r.path: r for r in rows}
    assert by_path["N.Struct"].has_dot is False
    assert by_path["N.Struct.X"].has_dot is True
