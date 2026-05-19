"""네비게이션 가능한 도크 패널의 공용 베이스."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class NavigablePanel(QWidget):
    """`navigate_requested(node_name)` 시그널을 공유하는 패널 베이스."""
    navigate_requested = Signal(str)
