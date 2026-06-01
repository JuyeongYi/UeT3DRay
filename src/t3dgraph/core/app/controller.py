"""앱 컨트롤러 — 파일 열기 → Model 파이프라인 → view 렌더."""
from __future__ import annotations
import importlib
import inspect
import warnings
from pathlib import Path
from ..registry import default_registry
from ..t3d.document import parse_document
from ..t3d.objects import T3DParseError
from ..t3d.encoding import read_t3d_text
from ..analysis.bundle import run as run_analyses
from .contracts import AbstractGraphController, AbstractGraphView


def _call_interpreter_factory(factory, *, resolver):
    """Call interpreter factory with resolver= keyword.

    If factory does not accept resolver=, emit DeprecationWarning and call without it.
    """
    sig = inspect.signature(factory)
    if "resolver" in sig.parameters:
        return factory(resolver=resolver)
    warnings.warn(
        "InterpreterFactory does not accept resolver= keyword. "
        "Update factory to InterpreterFactory protocol "
        "(see core/app/contracts.py::InterpreterFactory). "
        "Backward-compat fallback will be removed in a future batch.",
        DeprecationWarning, stacklevel=2,
    )
    return factory()


def load_ref(ref: str | None):
    """'pkg.mod:Class' 문자열을 클래스로 해석. None이면 None."""
    if not ref:
        return None
    module_path, _, attr = ref.partition(":")
    return getattr(importlib.import_module(module_path), attr)


class AppController(AbstractGraphController):
    def __init__(self, view: AbstractGraphView) -> None:
        self.view = view

    def open_file(self, path: str) -> None:
        p = Path(path)
        if not p.is_file():
            self._fail(f"파일을 찾을 수 없습니다: {path}")
            return
        try:
            doc = parse_document(read_t3d_text(p))
        except (UnicodeDecodeError, T3DParseError) as e:
            self._fail(f"파싱 실패: {e}")
            return
        try:
            plugin = default_registry().detect(doc)
        except LookupError as e:
            self._fail(str(e))
            return
        resolver = getattr(self.view, "resolver", None)
        graph = _call_interpreter_factory(plugin.interpreter_factory, resolver=resolver).interpret(doc)
        open_graph = getattr(self.view, "open_graph", None)
        if callable(open_graph):
            # MainWindow는 open_graph 내부에서 분석/데이터플로까지 수행 (Slice C+D).
            open_graph(graph, label=p.name)
        else:
            # 레거시 뷰 폴백 — bundle.run 단일 출처.
            self.view.show_graph(graph)
            self.view.show_analyses(run_analyses(graph))

    def _fail(self, message: str) -> None:
        self.view.show_error(message)
