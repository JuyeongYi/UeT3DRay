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


def _dedupe_within(objects: list[T3DObject]) -> list[T3DObject]:
    """단일 sibling list 안에서 같은 name 항목 머지.

    선언(`Begin Object Class=... Name="X"`) + 정의(`Begin Object Name="X"`)가
    같은 부모의 children에 연속 또는 비연속으로 나타나면 하나로 합친다.
    """
    result: list[T3DObject] = []
    by_name: dict[str, T3DObject] = {}
    for o in objects:
        if o.name and o.name in by_name:
            _merge_into(by_name[o.name], o)
        else:
            result.append(o)
            if o.name:
                by_name[o.name] = o
    return result


def _recursive_dedupe(objects: list[T3DObject]) -> list[T3DObject]:
    """전 트리 깊이에서 sibling 중복 머지."""
    deduped = _dedupe_within(objects)
    for obj in deduped:
        obj.children = _recursive_dedupe(obj.children)
    return deduped


def parse_document(src: str) -> T3DDocument:
    raw = parse_objects(src)
    merged: list[T3DObject] = []
    _merge_sibling_list(merged, raw)
    return T3DDocument(objects=_recursive_dedupe(merged))
