"""네비게이션 가능한 도크 패널의 공용 베이스."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class NavigablePanel(QWidget):
    """`navigate_requested(node_name)` 시그널을 공유하는 패널 베이스."""
    navigate_requested = Signal(str)

    # --- template method ---

    def highlight_node(self, node: str | None) -> None:
        """노드 이름으로 패널 항목을 선택/해제한다 (템플릿 메서드)."""
        item = self._lookup_item(node) if node else None
        if item is not None:
            for attr in ("treeWidget", "listWidget"):
                get_w = getattr(item, attr, None)
                if callable(get_w):
                    w = get_w()
                    if w is not None:
                        w.setCurrentItem(item)
                        return
        else:
            self._clear_highlight()

    # --- hooks (subclasses override) ---

    def _lookup_item(self, name: str):
        """name에 해당하는 Qt 위젯 아이템 반환. 없으면 None."""
        return None

    def _clear_highlight(self) -> None:
        """패널의 선택을 해제한다."""
