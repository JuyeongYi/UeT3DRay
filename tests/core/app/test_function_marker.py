"""g5 (F28) — NodeItem chevron 색 상태 (green/yellow/gray)."""
import pytest
from PySide6.QtWidgets import QApplication, QGraphicsSimpleTextItem
from PySide6.QtGui import QColor
from t3dgraph.core.base.graph_model import GraphModel, Node
from t3dgraph.core.app.items import NodeItem

_FUNCREF_CLS = "URigVMFunctionReferenceNode"
_GREEN = QColor("#4CAF50")
_YELLOW = QColor("#FFC107")
_GRAY = QColor("#C8C8C8")


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
    item = NodeItem(node)
    chev = _chevron(item)
    assert chev is not None
    assert chev.brush().color() == _GREEN


def test_chevron_yellow_when_funcref_no_subgraph(qapp) -> None:
    """funcref 클래스이지만 subgraph가 없는 노드의 chevron은 노랑이어야 한다."""
    node = Node(name="N", cls=_FUNCREF_CLS, subgraph=None)
    item = NodeItem(node)
    chev = _chevron(item)
    assert chev is not None
    assert chev.brush().color() == _YELLOW


def test_no_chevron_when_no_subgraph_and_not_funcref(qapp) -> None:
    """일반 노드(funcref 아님, subgraph 없음)에는 chevron이 없어야 한다."""
    node = Node(name="N", cls="URigVMUnitNode", subgraph=None)
    item = NodeItem(node)
    chev = _chevron(item)
    assert chev is None


def test_chevron_green_overrides_funcref(qapp) -> None:
    """funcref 클래스이고 subgraph도 있으면 초록이 우선한다."""
    node = Node(name="N", cls=_FUNCREF_CLS, subgraph="Sub")
    item = NodeItem(node)
    chev = _chevron(item)
    assert chev is not None
    assert chev.brush().color() == _GREEN


def test_function_entry_state_helper(qapp) -> None:
    """_function_entry_state() 반환값 검증."""
    n_sub = Node(name="A", cls=_FUNCREF_CLS, subgraph="Sub")
    n_ref = Node(name="B", cls=_FUNCREF_CLS, subgraph=None)
    n_plain = Node(name="C", cls="URigVMUnitNode", subgraph=None)
    assert NodeItem(n_sub)._function_entry_state() == "subgraph"
    assert NodeItem(n_ref)._function_entry_state() == "funcref"
    assert NodeItem(n_plain)._function_entry_state() == "none"
