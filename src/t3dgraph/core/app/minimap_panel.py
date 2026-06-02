from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QVBoxLayout, QTreeWidget, QTreeWidgetItem
from .navigable_panel import NavigablePanel
from .graph_stack import GraphStack
from ..base.graph_model import GraphModel

_ROOT_ROLE = Qt.UserRole + 1
_DEPTH_ROLE = Qt.UserRole + 2
_SUBGRAPH_ROLE = Qt.UserRole + 3


class MinimapPanel(NavigablePanel):
    location_clicked = Signal(int, object)   # (root_index, GraphModel)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['그래프 위치'])
        layout.addWidget(self._tree)
        self._tree.itemActivated.connect(self._on_activated)

    def show_stack(self, stack: GraphStack) -> None:
        self._tree.clear()
        current_root = stack._cur_root if stack.roots() else -1
        current_path = stack._paths[current_root] if current_root >= 0 else []
        current_depth = len(current_path) - 1
        for ri, root in enumerate(stack.roots()):
            root_item = QTreeWidgetItem([root.label or '(이름 없음)'])
            root_item.setData(0, _ROOT_ROLE, ri)
            root_item.setData(0, _DEPTH_ROLE, 0)
            root_item.setData(0, _SUBGRAPH_ROLE, root)
            self._tree.addTopLevelItem(root_item)
            if ri == current_root and current_depth == 0:
                root_item.setSelected(True)
            self._render_children(
                root, root_item, ri, depth=1,
                active_path=current_path if ri == current_root else None,
                current_depth=current_depth,
            )
            root_item.setExpanded(True)

    def _render_children(self, graph, parent_item, root_index, depth,
                         active_path, current_depth):
        for n in graph.nodes:
            subs = []
            if n.subgraph is not None:
                subs.append(n.subgraph)
            subs.extend(n.extra_subgraphs)
            for sub in subs:
                label = n.display_name or n.name
                if len(subs) > 1:
                    label = f"{label} ({sub.label or 'graph'})"
                item = QTreeWidgetItem([label])
                item.setData(0, _ROOT_ROLE, root_index)
                item.setData(0, _DEPTH_ROLE, depth)
                item.setData(0, _SUBGRAPH_ROLE, sub)
                parent_item.addChild(item)
                if active_path is not None and depth <= current_depth:
                    if active_path[depth] is sub:
                        item.setSelected(True)
                        item.setExpanded(True)
                        self._render_children(sub, item, root_index, depth + 1,
                                              active_path, current_depth)
                        continue
                self._render_children(sub, item, root_index, depth + 1, None, current_depth)

    def _on_activated(self, item, _col):
        ri = item.data(0, _ROOT_ROLE)
        sub = item.data(0, _SUBGRAPH_ROLE)
        if ri is not None and sub is not None:
            self.location_clicked.emit(ri, sub)

    def _click_for_test(self, root_index: int, subgraph) -> None:
        self.location_clicked.emit(root_index, subgraph)

    def all_labels(self) -> list[str]:
        out = []

        def walk(it):
            out.append(it.text(0))
            for i in range(it.childCount()):
                walk(it.child(i))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))
        return out
