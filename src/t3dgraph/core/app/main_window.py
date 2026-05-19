"""메인 윈도우 — 메뉴·도크·중앙 그래프 캔버스."""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QDockWidget, QLabel, QFileDialog
from ..base.graph_model import GraphModel
from .contracts import AbstractGraphView
from .scene import GraphScene
from .graph_view import GraphView
from .view_state import ViewState
from .inspector_panel import InspectorPanel
from .node_filter_panel import NodeFilterPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        QMainWindow.__init__(self)
        self.setWindowTitle("t3dgraph viewer")
        self.resize(1200, 800)

        self.view_state = ViewState()
        self.graph: GraphModel | None = None

        self.scene = GraphScene()
        self.view = GraphView()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.node_filter = NodeFilterPanel()
        self.inspector = InspectorPanel()
        self.dock_left = self._dock("노드 타입 필터", self.node_filter)
        self.dock_right = self._dock("속성 인스펙터", self.inspector)
        bottom_label = QLabel("(분석 — Phase 2c)")
        bottom_label.setAlignment(Qt.AlignCenter)
        self.dock_bottom = self._dock("분석", bottom_label)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_bottom)

        self._open_handler: Callable[[str], None] | None = None
        self._build_menu()
        self._wire()

    def _dock(self, title: str, widget) -> QDockWidget:
        dock = QDockWidget(title)
        dock.setWidget(widget)
        return dock

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("파일")
        file_menu.addAction("열기…").triggered.connect(self._on_open)
        file_menu.addAction("종료").triggered.connect(self.close)

    def _wire(self) -> None:
        self.scene.selectionChanged.connect(self._on_scene_selection)
        self.node_filter.type_toggled.connect(self._on_type_toggled)
        self.inspector.navigate_requested.connect(self._navigate_to)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "T3D 파일 열기", "", "T3D files (*.t3d *.txt);;All files (*)")
        if path:
            self.open_path(path)

    def set_open_handler(self, handler: Callable[[str], None]) -> None:
        self._open_handler = handler

    def open_path(self, path: str) -> None:
        if self._open_handler is not None:
            self._open_handler(path)

    def _on_scene_selection(self) -> None:
        name = self.scene.selected_node_name()
        self.view_state.select(name)
        if self.graph is not None:
            node = self.graph.node_by_name(name) if name else None
            self.inspector.show_node(node, self.graph)

    def _on_type_toggled(self, type_name: str, hidden: bool) -> None:
        self.view_state.set_type_hidden(type_name, hidden)
        self.scene.apply_hidden_types(self.view_state.hidden_node_types)

    def _navigate_to(self, node_name: str) -> None:
        self.scene.select_node(node_name)
        item = self.scene.node_item(node_name)
        if item is not None:
            self.view.centerOn(item)

    def show_graph(self, graph: GraphModel) -> None:
        self.graph = graph
        self.scene.populate(graph)
        self.node_filter.set_graph(graph)
        self.inspector.show_node(None, graph)
        self.view.fit()
        self.statusBar().showMessage(
            f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}", 5000)

    def show_error(self, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "t3dgraph", message)


AbstractGraphView.register(MainWindow)
