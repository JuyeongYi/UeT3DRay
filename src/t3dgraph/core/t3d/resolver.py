from __future__ import annotations
import re
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

    def _extract_target_path(self, ref_path: str) -> str | None:
        if not ref_path:
            return None
        m = re.search(r"Class'([^']+)'", ref_path)
        if m:
            return m.group(1)
        quoted = re.findall(r"'([^']+)'", ref_path)
        if quoted:
            return quoted[-1]
        if ":" in ref_path:
            return ref_path
        return None

    def resolve_function_reference(self, ref_path: str) -> "T3DObject | None":
        """FunctionReferenceNode의 ReferencedNode 경로에서 함수 이름 추출 후 인덱스 조회.

        ref_path 예시:
            "Class'/Game/.../FunctionLibrary.FunctionLibrary:FunctionLibrary_C.MyFunc'"
        반환: 해당 이름으로 등록된 T3DObject, 없으면 None.
        """
        m = re.search(r"'([^']+)'", ref_path)
        inner = m.group(1) if m else ref_path
        if ":" in inner:
            sub_path = inner.split(":", 1)[1]
            func_name = sub_path.rsplit(".", 1)[-1]
        else:
            func_name = inner.rsplit(".", 1)[-1]
        hit = self._index.get(func_name)
        return hit[1] if hit else None

    def resolve_external_refs(self, graph) -> dict:
        out = {}
        for ref in graph.external_refs:
            node_name = ref.split('.', 1)[0]
            hit = self._index.get(node_name)
            if hit is not None:
                out[ref] = hit
        return out
