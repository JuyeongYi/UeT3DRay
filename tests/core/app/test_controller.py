from t3dgraph.core.app.controller import AppController, load_ref
from t3dgraph.core.app.contracts import AbstractGraphController, AbstractGraphView
from t3dgraph.core.base.graph_model import GraphModel


class _FakeView(AbstractGraphView):
    def __init__(self):
        self.shown: GraphModel | None = None
        self.error: str | None = None
        self.analysis = None
        self.data_flow = None
    def show_graph(self, graph):
        self.shown = graph
    def show_analysis(self, flow, order):
        self.analysis = (flow, order)
    def show_data_flow(self, result):
        self.data_flow = result
    def show_analyses(self, bundle):
        self.bundle = bundle
    def show_error(self, message):
        self.error = message


def test_controller_is_abstract_controller():
    assert issubclass(AppController, AbstractGraphController)


def test_open_real_file_renders(orion_dir):
    view = _FakeView()
    ctrl = AppController(view)
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    ctrl.open_file(str(f))
    assert view.shown is not None
    assert len(view.shown.nodes) > 0


def test_open_missing_file_reports_error():
    view = _FakeView()
    AppController(view).open_file("does-not-exist.t3d.txt")
    assert view.shown is None
    assert view.error is not None


def test_load_ref_resolves_dotted_path():
    cls = load_ref("t3dgraph.core.app.main_window:MainWindow")
    from t3dgraph.core.app.main_window import MainWindow
    assert cls is MainWindow


def test_load_ref_none_returns_none():
    assert load_ref(None) is None


def test_controller_feeds_analysis_to_view(orion_dir):
    view = _FakeView()
    ctrl = AppController(view)
    f = orion_dir / "Game_Characters_workshop_Meshes_SKM_workshop_upper_weldingArm_CR__RigVMModel.t3d.txt"
    ctrl.open_file(str(f))
    assert view.shown is not None
    assert view.analysis is not None
    flow, order = view.analysis
    assert len(order) >= 0 and hasattr(flow, "convergence_points")
