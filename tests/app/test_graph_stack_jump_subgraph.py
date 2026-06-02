"""u2 — GraphStack.jump_to_subgraph로 임의 subgraph 활성화."""
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.graph_stack import GraphStack


def test_jump_to_subgraph_at_root() -> None:
    root = GraphModel(label="root")
    stack = GraphStack()
    stack.open_root(root)
    ok = stack.jump_to_subgraph(root)
    assert ok is True
    assert stack.current() is root


def test_jump_to_nested_subgraph() -> None:
    leaf = GraphModel(label="leaf")
    mid = GraphModel(label="mid",
                     nodes=[Node(name="LeafContainer", cls="X", subgraph=leaf)])
    root = GraphModel(label="root",
                      nodes=[Node(name="MidContainer", cls="X", subgraph=mid)])
    stack = GraphStack()
    stack.open_root(root)
    assert stack.jump_to_subgraph(leaf) is True
    assert stack.current() is leaf
    # 경로 확인
    segments = stack.segments()
    assert len(segments) == 3  # root -> mid -> leaf


def test_jump_to_extra_subgraph() -> None:
    extra = GraphModel(label="extra")
    main = GraphModel(label="main")
    container = Node(name="C", cls="X", subgraph=main, extra_subgraphs=[extra])
    root = GraphModel(label="root", nodes=[container])
    stack = GraphStack()
    stack.open_root(root)
    assert stack.jump_to_subgraph(extra) is True
    assert stack.current() is extra


def test_jump_to_unknown_returns_false() -> None:
    root = GraphModel(label="root")
    stranger = GraphModel(label="stranger")
    stack = GraphStack()
    stack.open_root(root)
    assert stack.jump_to_subgraph(stranger) is False
    assert stack.current() is root   # 변화 없음


def test_jump_to_sibling_subgraph() -> None:
    """다른 path의 형제 subgraph로 이동."""
    leaf_a = GraphModel(label="A")
    leaf_b = GraphModel(label="B")
    root = GraphModel(
        label="root",
        nodes=[
            Node(name="ContainerA", cls="X", subgraph=leaf_a),
            Node(name="ContainerB", cls="X", subgraph=leaf_b),
        ],
    )
    stack = GraphStack()
    stack.open_root(root)
    # leaf_a로 이동 후 leaf_b로 직접 이동
    assert stack.jump_to_subgraph(leaf_a) is True
    assert stack.current() is leaf_a
    assert stack.jump_to_subgraph(leaf_b) is True
    assert stack.current() is leaf_b
