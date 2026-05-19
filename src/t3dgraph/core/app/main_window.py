"""메인 윈도우 — 메뉴·도크·중앙 그래프 캔버스."""
from __future__ import annotations
from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QDockWidget, QLabel, QFileDialog
from ..base.graph_model import GraphModel
from .contracts import AbstractGraphView
from .scene import GraphScene
from .graph_view import GraphView


def _placeholder_dock(title: str) -> QDockWidget:
    dock = QDockWidget(title)
    label = QLabel(f"({title} — Phase 2b)")
    label.setAlignment(Qt.AlignCenter)
    dock.setWidget(label)
    return dock


class MainWindow(QMainWindow):
    """'분석 중심' 레이아웃. Phase 2a는 도크가 빈 placeholder."""

    def __init__(self) -> None:
        QMainWindow.__init__(self)
        self.setWindowTitle("t3dgraph viewer")
        self.resize(1200, 800)

        self.scene = GraphScene()
        self.view = GraphView()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.dock_left = _placeholder_dock("노드 타입 필터")
        self.dock_right = _placeholder_dock("속성 인스펙터")
        self.dock_bottom = _placeholder_dock("분석")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_bottom)

        self._open_handler: Callable[[str], None] | None = None
        self._build_menu()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("파일")
        open_act = file_menu.addAction("열기…")
        open_act.triggered.connect(self._on_open)
        exit_act = file_menu.addAction("종료")
        exit_act.triggered.connect(self.close)

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

    def show_graph(self, graph: GraphModel) -> None:
        self.scene.populate(graph)
        self.view.fit()
        self.statusBar().showMessage(
            f"노드 {len(graph.nodes)} · 링크 {len(graph.links)}", 5000)

    def show_error(self, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "t3dgraph", message)


# QMainWindow uses Shiboken metaclass which conflicts with ABCMeta.
# Register MainWindow as a virtual subclass so isinstance checks still work.
AbstractGraphView.register(MainWindow)
