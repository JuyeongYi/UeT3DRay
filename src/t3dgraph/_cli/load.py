from __future__ import annotations
from pathlib import Path
from ..core.t3d.document import parse_document
from ..core.t3d.objects import T3DParseError
from ..core.t3d.encoding import read_t3d_text
from ..core.registry import default_registry
from ..core.base.graph_model import GraphModel


def strict_load(path: Path) -> tuple[GraphModel, list[str]]:
    doc = parse_document(read_t3d_text(path))
    plugin = default_registry().detect(doc)
    graph = plugin.interpreter_factory().interpret(doc)
    return graph, list(graph.warnings)


def lenient_load(path: Path) -> tuple[GraphModel | None, list[str]]:
    warnings: list[str] = []
    try:
        doc = parse_document(read_t3d_text(path))
    except (UnicodeDecodeError, T3DParseError) as e:
        warnings.append(f'parse 실패: {e}')
        return None, warnings
    try:
        plugin = default_registry().detect(doc)
    except LookupError as e:
        warnings.append(f'plugin 탐지 실패: {e}')
        return None, warnings
    try:
        graph = plugin.interpreter_factory().interpret(doc)
    except Exception as e:
        warnings.append(f'해석 실패: {e}')
        return None, warnings
    warnings.extend(graph.warnings)
    return graph, warnings
