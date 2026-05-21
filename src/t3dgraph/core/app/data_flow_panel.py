"""계산(데이터) 흐름 패널 — sink별 의존 트리 + 고립 노드 그룹."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from ..analysis.data_flow import DataFlowResult, dependency_tree, DepNode
from .navigable_panel import NavigablePanel

_NODE_ROLE = Qt.UserRole + 1


class DataFlowPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._summary = QLabel("(그래프를 열어주세요)")
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["sink/노드 ← 의존"])
        layout.addWidget(self._summary)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        self._items: dict[str, QTreeWidgetItem] = {}

    def show_result(self, r: DataFlowResult) -> None:
        self._tree.clear()
        self._items = {}
        if not r.all_nodes:
            self._summary.setText("(노드 없음)")
            return
        self._summary.setText(
            f"sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")

        for sink in r.sinks:
            tree = dependency_tree(sink, r.inputs_of)
            top = self._add_dep_tree(tree, self._tree.invisibleRootItem())
            top.setExpanded(True)

        shown = set(self._items.keys())
        unshown = [n for n in r.all_nodes if n not in shown]
        if unshown:
            group = QTreeWidgetItem(["고립/미연결"])
            self._tree.addTopLevelItem(group)
            for name in unshown:
                child = QTreeWidgetItem([name])
                child.setData(0, _NODE_ROLE, name)
                group.addChild(child)
                self._items[name] = child

    def _add_dep_tree(self, dep: DepNode, parent: QTreeWidgetItem) -> QTreeWidgetItem:
        item = QTreeWidgetItem([dep.node])
        item.setData(0, _NODE_ROLE, dep.node)
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)
        self._items.setdefault(dep.node, item)
        for c in dep.children:
            self._add_dep_tree(c, item)
        return item

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        name = item.data(0, _NODE_ROLE)
        if name:
            self.navigate_requested.emit(name)

    def activate_node(self, name: str) -> None:
        item = self._items.get(name)
        if item is not None:
            self._on_activated(item, 0)

    def top_level_labels(self) -> list[str]:
        out: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            out.append(self._tree.topLevelItem(i).text(0))
        return out

    def shown_node_names(self) -> set[str]:
        return set(self._items.keys())

    def highlight_node(self, node: str | None) -> None:
        item = self._items.get(node) if node else None
        if item is not None:
            self._tree.setCurrentItem(item)
        else:
            self._tree.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._tree.currentItem()
        return item.data(0, _NODE_ROLE) if item is not None else None
