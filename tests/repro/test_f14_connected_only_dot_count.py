"""F14 재현 — connected_only 토글 시 dot 개수 증가 금지.

σ 슬라이스가 본 어서션을 통과시켜야 한다.
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QGraphicsEllipseItem

from t3dgraph.core.app.scene import GraphScene
from t3dgraph.core.app.view_state import ViewState
from t3dgraph.core.t3d.document import T3DDocument
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def _count_dots(node_item) -> int:
    """NodeItem 자식 중 QGraphicsEllipseItem(핀 dot) 개수."""
    return sum(
        1 for c in node_item.childItems() if isinstance(c, QGraphicsEllipseItem)
    )


def _total_dots(scene: GraphScene) -> int:
    return sum(_count_dots(n) for n in scene._nodes.values())


def test_connected_only_toggle_does_not_double_dots(
        qtbot, orion_doc: T3DDocument) -> None:
    """connected_only 토글 후 dot 개수가 증가하지 않는다."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    scene = GraphScene()
    vs = ViewState()
    scene.populate(graph, view_state=vs)
    dots_off = _total_dots(scene)
    assert dots_off > 0  # extractor sanity

    vs.connected_pins_only = True
    scene.populate(graph, view_state=vs)
    dots_on = _total_dots(scene)

    assert dots_on <= dots_off, (
        f"F14 회귀: connected_only=True에서 dot 증가 — off={dots_off}, on={dots_on}"
    )


def test_connected_only_reduces_or_keeps_dots(
        qtbot, orion_doc: T3DDocument) -> None:
    """추가 보강 — 연결된 핀이 전체보다 적거나 같다는 단조성."""
    graph = RigVMGraphInterpreter().interpret(orion_doc)
    scene = GraphScene()
    vs_off = ViewState()
    vs_on = ViewState()
    vs_on.connected_pins_only = True
    scene.populate(graph, view_state=vs_off)
    off = _total_dots(scene)
    scene.populate(graph, view_state=vs_on)
    on = _total_dots(scene)
    assert on <= off, f"단조성 위배: off={off}, on={on}"
