"""메인 윈도우 — 메뉴·도크·중앙 그래프 캔버스."""
from __future__ import annotations
from typing import Callable
from urllib.parse import quote
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QFileDialog, QTabBar, QTabWidget, QVBoxLayout, QWidget,
)
from ..base.graph_model import GraphModel
from .contracts import AbstractGraphView
from .scene import GraphScene
from .graph_view import GraphView
from .graph_stack import GraphStack
from .breadcrumb_bar import BreadcrumbBar
from .view_state import ViewState
from .inspector_panel import InspectorPanel
from .node_filter_panel import NodeFilterPanel
from .analysis_panel import AnalysisPanel
from .execution_order_panel import ExecutionOrderPanel
from .data_flow_panel import DataFlowPanel
from .minimap_panel import MinimapPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        QMainWindow.__init__(self)
        self.setWindowTitle("t3dgraph viewer")
        self.resize(1200, 800)

        self._view_states: dict[str, ViewState] = {}
        self._fallback_view_state = ViewState()   # 그래프 없을 때 (브레드크럼·전체 펼침)
        self._root_tokens: dict[int, str] = {}  # id(root_graph) → stable token
        self._next_token = 0
        self.graph: GraphModel | None = None
        self._flow = None

        self.scene = GraphScene()
        self.view = GraphView()
        self.view.setScene(self.scene)

        # F5: 그래프 스택 + 브레드크럼 바를 뷰 상단에 배치.
        self.graph_stack = GraphStack()
        self.breadcrumb = BreadcrumbBar()
        self._tab_bar = QTabBar()
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setExpanding(False)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabCloseRequested.connect(self._on_tab_close)
        central = QWidget()
        vlay = QVBoxLayout(central)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)
        vlay.addWidget(self._tab_bar)
        vlay.addWidget(self.breadcrumb)
        vlay.addWidget(self.view)
        self.setCentralWidget(central)

        self.node_filter = NodeFilterPanel()
        self.inspector = InspectorPanel()
        self.analysis_panel = AnalysisPanel()
        self.exec_order_panel = ExecutionOrderPanel()
        self.data_flow_panel = DataFlowPanel()

        bottom_tabs = QTabWidget()
        bottom_tabs.addTab(self.analysis_panel, "수렴점")
        bottom_tabs.addTab(self.exec_order_panel, "실행 순서")
        bottom_tabs.addTab(self.data_flow_panel, "계산 흐름")

        self.minimap = MinimapPanel()

        self.dock_left = self._dock("노드 타입 필터", self.node_filter)
        self.dock_minimap = self._dock("미니맵", self.minimap)
        self.dock_right = self._dock("속성 인스펙터", self.inspector)
        self.dock_bottom = self._dock("분석", bottom_tabs)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_minimap)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_bottom)

        self._open_handler: Callable[[str], None] | None = None
        self._resolver = None
        self._build_menu()
        self._build_view_mode_toolbar()
        self._wire()
        self._build_shortcuts()

    def _dock(self, title: str, widget) -> QDockWidget:
        dock = QDockWidget(title)
        dock.setWidget(widget)
        return dock

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("파일")
        file_menu.addAction("열기…").triggered.connect(self._on_open)
        file_menu.addAction("에셋 폴더 열기…").triggered.connect(self._on_open_folder)
        file_menu.addAction("종료").triggered.connect(self.close)

    def _on_open_folder(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path
        from ..t3d.resolver import AssetResolver
        folder = QFileDialog.getExistingDirectory(self, '에셋 폴더 선택')
        if not folder:
            return
        self._resolver = AssetResolver()
        self._resolver.load_folder(Path(folder))
        for path in sorted(Path(folder).glob('*.t3d.txt')):
            if self._open_handler:
                self._open_handler(str(path))

    def _build_view_mode_toolbar(self) -> None:
        from PySide6.QtGui import QAction
        toolbar = self.addToolBar("뷰 모드")
        self._view_mode_actions: dict[str, QAction] = {}
        toggles = (
            ("connected_only", "연결된 핀만",
             lambda v: self.current_view_state().set_connected_pins_only(v), False),
            ("fan_in_highlight", "fan-in 강조",
             lambda v: self.current_view_state().set_fan_in_highlight(v), True),
        )
        for mode_id, label, setter, in_place in toggles:
            action = QAction(label, self)
            action.setCheckable(True)
            action.toggled.connect(
                lambda checked, s=setter, ip=in_place: self._on_view_mode(s, checked, ip))
            toolbar.addAction(action)
            self._view_mode_actions[mode_id] = action

        expand_all = QAction("전체 펼침", self)
        expand_all.triggered.connect(self._on_expand_all_pins)
        toolbar.addAction(expand_all)
        self._view_mode_actions["expand_all"] = expand_all

        collapse_all = QAction("전체 접기", self)
        collapse_all.triggered.connect(self._on_collapse_all_pins)
        toolbar.addAction(collapse_all)
        self._view_mode_actions["collapse_all"] = collapse_all

    def _on_expand_all_pins(self) -> None:
        if self.graph is None:
            return
        paths: list[str] = []

        def walk(node_name, pin, prefix):
            path = f"{prefix}.{pin.name}"
            paths.append(path)
            for sp in pin.subpins:
                walk(node_name, sp, path)

        for n in self.graph.nodes:
            for p in n.pins:
                walk(n.name, p, n.name)
        self.current_view_state().expand_all_pins(paths)
        self._rebuild_scene()

    def _on_collapse_all_pins(self) -> None:
        self.current_view_state().collapse_all_pins()
        self._rebuild_scene()

    def _on_view_mode(self, setter, checked: bool, in_place: bool = False) -> None:
        setter(checked)
        if in_place and self._flow is not None:
            self.scene.apply_fan_in_highlight(
                set(self._flow.convergence_points), checked)
        else:
            self._rebuild_scene()

    def current_view_state(self) -> ViewState:
        """현재 그래프 키 기준의 ViewState. 없으면 생성."""
        key = self._current_graph_key()
        if not key:
            return self._fallback_view_state
        if key not in self._view_states:
            self._view_states[key] = ViewState()
        return self._view_states[key]

    @property
    def view_state(self) -> ViewState:
        """하위 호환 프로퍼티 — 기존 테스트·외부 코드용."""
        return self.current_view_state()

    def _current_graph_key(self) -> str:
        current = self.graph_stack.current()
        if current is None:
            return ""
        label = quote(current.label or "(unlabeled)", safe="")
        parent = quote(current.parent_node or "", safe="")
        roots = self.graph_stack.roots()
        idx = self._tab_bar.currentIndex()
        root = roots[idx] if 0 <= idx < len(roots) else None
        token = self._root_tokens.get(id(root), "?") if root is not None else "?"
        return f"{token}/{label}/{parent}"

    def _rebuild_scene(self) -> None:
        if self.graph is not None:
            self.scene.populate(self.graph, view_state=self.current_view_state(),
                                flow=self._flow)

    def set_view_mode(self, mode_id: str, checked: bool) -> None:
        """안정 식별자로 뷰 모드 토글 — connected_only / fan_in_highlight."""
        action = self._view_mode_actions.get(mode_id)
        if action is not None:
            action.setChecked(checked)

    def _build_shortcuts(self) -> None:
        from PySide6.QtGui import QShortcut, QKeySequence
        for seq in (QKeySequence('Alt+Left'), QKeySequence(Qt.Key_Backspace)):
            sc = QShortcut(seq, self, activated=self._on_shortcut_back)
            sc.setContext(Qt.ApplicationShortcut)
        sc2 = QShortcut(QKeySequence('Alt+Up'), self, activated=self._on_shortcut_up)
        sc2.setContext(Qt.ApplicationShortcut)

    def _on_shortcut_back(self) -> None:
        self.graph_stack.pop()
        self._render_current()

    def _on_shortcut_up(self) -> None:
        segs = self.graph_stack.segments()
        if len(segs) >= 2:
            self.graph_stack.jump_to(len(segs) - 2)
            self._render_current()

    def _wire(self) -> None:
        self.scene.selectionChanged.connect(self._on_scene_selection)
        self.scene.pin_toggle_requested.connect(self._on_pin_toggle)
        self.node_filter.type_toggled.connect(self._on_type_toggled)
        self.node_filter.search_changed.connect(self._on_search_changed)
        self.inspector.navigate_requested.connect(self._navigate_to)
        self.analysis_panel.navigate_requested.connect(self._navigate_to)
        self.exec_order_panel.navigate_requested.connect(self._navigate_to)
        self.data_flow_panel.navigate_requested.connect(self._navigate_to)
        self.scene.enter_subgraph_requested.connect(self._on_enter_subgraph)
        self.breadcrumb.segment_clicked.connect(self._on_breadcrumb_clicked)
        self.minimap.location_clicked.connect(self._on_minimap_click)

    def _on_search_changed(self) -> None:
        if self.graph is None:
            return
        hits = self.node_filter.matched_node_names()
        self.scene.apply_search_highlight(hits)

    def _on_pin_toggle(self, full_path: str) -> None:
        self.current_view_state().toggle_pin_expanded(full_path)
        self._rebuild_scene()

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "T3D 파일 열기", "", "T3D files (*.t3d *.txt);;All files (*)")
        if path:
            self.open_path(path)

    def _on_minimap_click(self, root_index: int, depth: int) -> None:
        if root_index != self._tab_bar.currentIndex():
            self._tab_bar.setCurrentIndex(root_index)
        else:
            self.graph_stack.jump_to(depth)
            self._render_current()

    def set_open_handler(self, handler: Callable[[str], None]) -> None:
        self._open_handler = handler

    def open_path(self, path: str) -> None:
        if self._open_handler is not None:
            self._open_handler(path)

    def _on_scene_selection(self) -> None:
        name = self.scene.selected_node_name()
        self.current_view_state().select(name)
        if self.graph is not None:
            node = self.graph.node_by_name(name) if name else None
            self.inspector.show_node(node, self.graph)
        self.analysis_panel.highlight_node(name)
        self.exec_order_panel.highlight_node(name)
        self.data_flow_panel.highlight_node(name)

    def _on_type_toggled(self, type_name: str, hidden: bool) -> None:
        self.current_view_state().set_type_hidden(type_name, hidden)
        self.scene.apply_hidden_types(self.current_view_state().hidden_node_types)

    def _navigate_to(self, node_name: str) -> None:
        self.scene.select_node(node_name)
        item = self.scene.node_item(node_name)
        if item is not None:
            self.view.centerOn(item)

    def open_graph(self, graph: GraphModel, *, label: str | None = None) -> None:
        """새 루트 그래프 추가(파일 열기 진입점) — 브레드크럼 / 스택 갱신."""
        if label and not graph.label:
            graph.label = label
        self.graph_stack.open_root(graph)
        self._root_tokens[id(graph)] = str(self._next_token)
        self._next_token += 1
        self._tab_bar.blockSignals(True)
        self._tab_bar.addTab(graph.label or '(이름 없음)')
        self._tab_bar.setCurrentIndex(self._tab_bar.count() - 1)
        self._tab_bar.blockSignals(False)
        self._render_current()

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.graph_stack.roots()):
            return
        self.graph_stack.select_root(index)
        self._render_current()

    def _on_tab_close(self, index: int) -> None:
        # Capture token BEFORE removing tab (same pattern as layout_overrides cleanup)
        roots = self.graph_stack.roots()
        if 0 <= index < len(roots):
            root = roots[index]
            token = self._root_tokens.pop(id(root), None)
            if token is not None:
                # Clean up ViewState entries for this tab (prefix match catches subgraph keys)
                stale = [k for k in self._view_states
                         if k.startswith(f"{token}/") or k == token]
                for k in stale:
                    del self._view_states[k]
        self._tab_bar.blockSignals(True)
        self._tab_bar.removeTab(index)
        self._tab_bar.blockSignals(False)
        self.graph_stack.close_root(index)
        if self.graph_stack.current() is None:
            self.scene.clear()
            self.breadcrumb.set_segments([])
        else:
            self._render_current()

    def _on_enter_subgraph(self, node_name: str) -> None:
        current = self.graph_stack.current()
        if current is None:
            return
        node = current.node_by_name(node_name)
        if node is None or node.subgraph is None:
            return
        self.graph_stack.push(node.subgraph)
        self._render_current()

    def _on_breadcrumb_clicked(self, index: int) -> None:
        self.graph_stack.jump_to(index)
        self._render_current()

    def _render_current(self) -> None:
        current = self.graph_stack.current()
        if current is None:
            return
        self.graph = current
        from ..analysis.bundle import run as run_analyses
        bundle = run_analyses(current)
        self.scene.populate(current, view_state=self.current_view_state(), flow=bundle.flow)
        self.node_filter.set_graph(current)
        self.inspector.show_node(None, current)
        self.view.fit()
        self.breadcrumb.set_segments(self.graph_stack.segments())
        self.statusBar().showMessage(
            f"노드 {len(current.nodes)} · 링크 {len(current.links)}", 5000)
        self.show_analyses(bundle)
        self.minimap.show_stack(self.graph_stack)

    def show_graph(self, graph: GraphModel) -> None:
        """레거시 진입점 — 새 루트로 push."""
        self.open_graph(graph)

    def show_analyses(self, bundle) -> None:
        self.show_analysis(bundle.flow, bundle.execution_order)
        self.show_data_flow(bundle.data_flow)

    def show_analysis(self, flow, order) -> None:
        self._flow = flow
        self.analysis_panel.show_flow(flow)
        self.exec_order_panel.show_order(order)

    def show_data_flow(self, result: "DataFlowResult") -> None:
        self.data_flow_panel.show_result(result)

    def show_error(self, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "t3dgraph", message)


AbstractGraphView.register(MainWindow)
