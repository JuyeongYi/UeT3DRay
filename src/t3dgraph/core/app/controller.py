"""앱 컨트롤러 — 파일 열기 → Model 파이프라인 → view 렌더."""
from __future__ import annotations
import importlib
from pathlib import Path
from ..registry import default_registry
from ..t3d.document import parse_document
from ..t3d.objects import T3DParseError
from .contracts import AbstractGraphController, AbstractGraphView


def load_ref(ref: str | None):
    """'pkg.mod:Class' 문자열을 클래스로 해석. None이면 None."""
    if not ref:
        return None
    module_path, _, attr = ref.partition(":")
    return getattr(importlib.import_module(module_path), attr)


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


class AppController(AbstractGraphController):
    def __init__(self, view: AbstractGraphView) -> None:
        self.view = view

    def open_file(self, path: str) -> None:
        p = Path(path)
        if not p.is_file():
            self._fail(f"파일을 찾을 수 없습니다: {path}")
            return
        try:
            doc = parse_document(_read_text(p))
        except (UnicodeDecodeError, T3DParseError) as e:
            self._fail(f"파싱 실패: {e}")
            return
        try:
            plugin = default_registry().detect(doc)
        except LookupError as e:
            self._fail(str(e))
            return
        graph = plugin.interpreter_factory().interpret(doc)
        self.view.show_graph(graph)

    def _fail(self, message: str) -> None:
        show_error = getattr(self.view, "show_error", None)
        if callable(show_error):
            show_error(message)
