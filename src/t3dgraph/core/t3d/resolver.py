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

    def extract_target_path(self, ref_path: str) -> str | None:
        """ref 경로에서 타겟 추출. 비표준이면 None (public)."""
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

    # 한 사이클 호환 별칭
    _extract_target_path = extract_target_path

    def resolve_function_reference(
        self, ref_path: str
    ) -> "tuple[T3DObject | None, str | None]":
        """FunctionReferenceNode의 ReferencedNode 경로에서 함수 이름 추출 후 인덱스 조회.

        반환: (T3DObject 또는 None, 사유 메시지). 사유 None이면 정상 해결.
        """
        inner = self.extract_target_path(ref_path)
        if inner is None:
            return None, "ref unparseable"
        if ":" in inner:
            sub_path = inner.split(":", 1)[1]
            func_name = sub_path.rsplit(".", 1)[-1]
        else:
            func_name = inner.rsplit(".", 1)[-1]
        hit = self._index.get(func_name)
        if hit is None:
            return None, "asset not found in resolver"
        return hit[1], None

    def resolve_external_refs(self, graph) -> dict:
        out = {}
        for ref in graph.external_refs:
            node_name = ref.split('.', 1)[0]
            hit = self._index.get(node_name)
            if hit is not None:
                out[ref] = hit
        return out
