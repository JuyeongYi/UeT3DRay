from __future__ import annotations
from pathlib import Path
from .document import T3DDocument, parse_document
from .objects import T3DObject
from .encoding import read_t3d_text


class AssetResolver:
    def __init__(self) -> None:
        self._index: dict[str, tuple[Path, T3DObject]] = {}

    def register(self, path: Path, doc: T3DDocument) -> None:
        for obj in self._iter_objects(doc.objects):
            if obj.name:
                self._index.setdefault(obj.name, (path, obj))

    def _iter_objects(self, objs):
        for o in objs:
            yield o
            yield from self._iter_objects(o.children)

    def load_folder(self, folder: Path, pattern: str = '*.t3d.txt') -> None:
        for p in sorted(folder.glob(pattern)):
            try:
                doc = parse_document(read_t3d_text(p))
                self.register(p, doc)
            except Exception:
                continue

    def resolve_node_name(self, name: str):
        return self._index.get(name)

    def resolve_external_refs(self, graph) -> dict:
        out = {}
        for ref in graph.external_refs:
            node_name = ref.split('.', 1)[0]
            hit = self._index.get(node_name)
            if hit is not None:
                out[ref] = hit
        return out
