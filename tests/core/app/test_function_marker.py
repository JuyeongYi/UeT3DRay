"""g5 (F28) — NodeItem chevron 색 상태 (green/yellow/gray)."""
import pytest
from PySide6.QtWidgets import QApplication, QGraphicsSimpleTextItem
from PySide6.QtGui import QColor
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.items import NodeItem
from t3dgraph.core.app.node_profiles import NodeStyleProfile

_FUNCREF_CLS = "URigVMFunctionReferenceNode"
_GREEN = QColor("#4CAF50")
_YELLOW = QColor("#FFC107")

_PROFILE_CHEVRON = NodeStyleProfile(always_show_chevron=True, chevron_state_aware=True)
_PROFILE_ALWAYS = NodeStyleProfile(always_show_chevron=True, chevron_state_aware=False)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _chevron(item: NodeItem) -> QGraphicsSimpleTextItem | None:
    for c in item.childItems():
        if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "▶":
            return c
    return None


def test_chevron_green_when_has_subgraph(qapp) -> None:
    """subgraph 보유 노드의 chevron은 초록색이어야 한다."""
    node = Node(name="N", cls="URigVMFunctionLibraryNode", subgraph="Sub")
    item = NodeItem(node, profile=_PROFILE_CHEVRON)
    chev = _chevron(item)
    assert chev is not None
    assert chev.brush().color() == _GREEN


def test_chevron_yellow_when_chevron_state_aware_no_subgraph(qapp) -> None:
    """chevron_state_aware=True이고 subgraph 없으면 노란 chevron."""
    node = Node(name="N", cls=_FUNCREF_CLS, subgraph=None)
    item = NodeItem(node, profile=_PROFILE_CHEVRON)
    chev = _chevron(item)
    assert chev is not None
    assert chev.brush().color() == _YELLOW


def test_no_chevron_when_no_profile(qapp) -> None:
    """profile 없으면 (DEFAULT) chevron 표시 안 함."""
    node = Node(name="N", cls="URigVMUnitNode", subgraph=None)
    item = NodeItem(node)
    chev = _chevron(item)
    assert chev is None


def test_chevron_green_overrides_when_has_subgraph(qapp) -> None:
    """always_show_chevron=True이고 subgraph도 있으면 초록 우선."""
    node = Node(name="N", cls=_FUNCREF_CLS, subgraph="Sub")
    item = NodeItem(node, profile=_PROFILE_CHEVRON)
    chev = _chevron(item)
    assert chev is not None
    assert chev.brush().color() == _GREEN


def test_function_entry_state_helper(qapp) -> None:
    """_function_entry_state() 반환값 검증."""
    n_sub = Node(name="A", cls=_FUNCREF_CLS, subgraph="Sub")
    n_ref = Node(name="B", cls=_FUNCREF_CLS, subgraph=None)
    n_plain = Node(name="C", cls="URigVMUnitNode", subgraph=None)
    assert NodeItem(n_sub, profile=_PROFILE_CHEVRON)._function_entry_state() == "subgraph"
    assert NodeItem(n_ref, profile=_PROFILE_CHEVRON)._function_entry_state() == "funcref"
    assert NodeItem(n_plain)._function_entry_state() == "none"
