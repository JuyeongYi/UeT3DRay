"""g4 (F25) — exec 핀 dot 크기(6px) + 레이블 bold."""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin
from t3dgraph.core.app.items import NodeItem, PIN_RADIUS

EXEC_RADIUS = 6.0


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _exec_node() -> Node:
    return Node(
        name="N",
        cls=None,
        pins=[
            Pin(name="Execute", cpp_type="FRigVMExecuteContext",
                direction="input", is_execution=True),
            Pin(name="Value", cpp_type="float", direction="input"),
        ],
    )


def test_exec_pin_dot_larger(qapp) -> None:
    """is_execution=True인 핀의 dot 반지름은 EXEC_RADIUS(6)이어야 한다."""
    node = _exec_node()
    item = NodeItem(Node(name="N", cls=None, pins=[
        Pin(name="Execute", cpp_type="FRigVMExecuteContext",
            direction="input", is_execution=True),
    ]))
    # dot QGraphicsEllipseItem의 rect width로 반지름 추론
    from PySide6.QtWidgets import QGraphicsEllipseItem
    dots = [c for c in item.childItems() if isinstance(c, QGraphicsEllipseItem)]
    assert len(dots) == 1
    r = dots[0].rect().width() / 2
    assert r == EXEC_RADIUS


def test_non_exec_pin_dot_normal(qapp) -> None:
    """is_execution=False인 핀의 dot 반지름은 PIN_RADIUS(4)이어야 한다."""
    item = NodeItem(Node(name="N", cls=None, pins=[
        Pin(name="Value", cpp_type="float", direction="input"),
    ]))
    from PySide6.QtWidgets import QGraphicsEllipseItem
    dots = [c for c in item.childItems() if isinstance(c, QGraphicsEllipseItem)]
    assert len(dots) == 1
    r = dots[0].rect().width() / 2
    assert r == PIN_RADIUS


def test_exec_pin_label_bold(qapp) -> None:
    """is_execution=True 핀의 레이블은 bold이어야 한다."""
    item = NodeItem(Node(name="N", cls=None, pins=[
        Pin(name="Execute", cpp_type="FRigVMExecuteContext",
            direction="input", is_execution=True),
    ]))
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    labels = [c for c in item.childItems()
              if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "Execute"]
    assert len(labels) == 1
    assert labels[0].font().bold()


def test_non_exec_pin_label_not_bold(qapp) -> None:
    """is_execution=False 핀의 레이블은 bold가 아니어야 한다."""
    item = NodeItem(Node(name="N", cls=None, pins=[
        Pin(name="Value", cpp_type="float", direction="input"),
    ]))
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    labels = [c for c in item.childItems()
              if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "Value"]
    assert len(labels) == 1
    assert not labels[0].font().bold()
