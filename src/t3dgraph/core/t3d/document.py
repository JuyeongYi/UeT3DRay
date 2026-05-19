"""무손실 T3DDocument — 2단계(선언/정의) 블록 병합."""
from __future__ import annotations
from dataclasses import dataclass, field
from .objects import T3DObject, parse_objects


@dataclass
class T3DDocument:
    objects: list[T3DObject] = field(default_factory=list)


def _merge_into(target: T3DObject, other: T3DObject) -> None:
    if target.cls is None and other.cls is not None:
        target.cls = other.cls
    if other.export_path:
        target.export_path = other.export_path
    target.properties.update(other.properties)
    _merge_sibling_list(target.children, other.children)


def _merge_sibling_list(dst: list[T3DObject], src: list[T3DObject]) -> None:
    by_name: dict[str, T3DObject] = {o.name: o for o in dst if o.name}
    for o in src:
        existing = by_name.get(o.name) if o.name else None
        if existing is not None:
            _merge_into(existing, o)
        else:
            dst.append(o)
            if o.name:
                by_name[o.name] = o


def parse_document(src: str) -> T3DDocument:
    raw = parse_objects(src)
    merged: list[T3DObject] = []
    _merge_sibling_list(merged, raw)
    return T3DDocument(objects=merged)
