"""계산(데이터) 흐름 패널 — sink별 의존 트리 + 핀 라벨 + 다중 인덱싱."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from ..analysis.data_flow import DataFlowResult, DataFlowEdge, dependency_tree, DepNode
from .navigable_panel import NavigablePanel

_NODE_ROLE = Qt.UserRole + 1
_BACK_REF_SUFFIX = "  [위 참조]"


class DataFlowPanel(NavigablePanel):

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._summary = QLabel("(그래프를 열어주세요)")
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["sink/노드 ← 의존 (핀)"])
        layout.addWidget(self._summary)
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)
        # D-A2: 한 노드의 모든 등장 위치
        self._items: dict[str, list[QTreeWidgetItem]] = {}

    def show_result(self, r: DataFlowResult) -> None:
        self._tree.clear()
        self._items = {}
        if not r.all_nodes:
            self._summary.setText("(노드 없음)")
            return
        self._summary.setText(
            f"sinks {len(r.sinks)} · sources {len(r.sources)} · isolated {len(r.isolated)}")

        for sink in r.sinks:
            tree = dependency_tree(sink, r.incoming_nodes)
            top = self._add_tree(tree, self._tree.invisibleRootItem(), inbound=r.inputs_of)
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
                self._items.setdefault(name, []).append(child)

    def _add_tree(self, dep: DepNode, parent: QTreeWidgetItem,
                  *, inbound: dict[str, list[DataFlowEdge]]) -> QTreeWidgetItem:
        is_back_ref = dep.node in self._items
        label = self._label_for(dep.node, inbound)
        if is_back_ref:
            label = label + _BACK_REF_SUFFIX
        item = QTreeWidgetItem([label])
        item.setData(0, _NODE_ROLE, dep.node)
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)
        self._items.setdefault(dep.node, []).append(item)
        if not is_back_ref:
            for c in dep.children:
                self._add_tree(c, item, inbound=inbound)
        return item

    @staticmethod
    def _label_for(node: str, inbound: dict[str, list[DataFlowEdge]]) -> str:
        edges = inbound.get(node, [])
        if not edges:
            return node
        srcs = ", ".join(
            f"{e.source_node}.{e.source.pin_path}→{e.target.pin_path}"
            if e.source.pin_path and e.target.pin_path
            else f"{e.source_node}.{e.source.pin_path}" if e.source.pin_path
            else e.source_node
            for e in edges
        )
        return f"{node} ← {srcs}" if srcs else node

    def _on_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        name = item.data(0, _NODE_ROLE)
        if name:
            self.navigate_requested.emit(name)

    def activate_node(self, name: str) -> None:
        items = self._items.get(name)
        if items:
            self._on_activated(items[0], 0)

    def items_for(self, name: str) -> list[QTreeWidgetItem]:
        return list(self._items.get(name, []))

    def all_labels(self) -> list[str]:
        out: list[str] = []
        for items in self._items.values():
            out.extend(it.text(0) for it in items)
        return out

    def top_level_labels(self) -> list[str]:
        out: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            out.append(self._tree.topLevelItem(i).text(0))
        return out

    def shown_node_names(self) -> set[str]:
        return set(self._items.keys())

    def _lookup_item(self, name: str):
        items = self._items.get(name)
        return items[0] if items else None

    def _clear_highlight(self) -> None:
        self._tree.clearSelection()

    def highlighted_node(self) -> str | None:
        item = self._tree.currentItem()
        return item.data(0, _NODE_ROLE) if item is not None else None
