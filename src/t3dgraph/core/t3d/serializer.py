from __future__ import annotations
from .values import Value, Scalar, QuotedString, Struct, ArrayLiteral
from .objects import T3DObject
from .document import T3DDocument


def serialize_value(v: Value) -> str:
    if isinstance(v, Scalar):
        return v.text
    if isinstance(v, QuotedString):
        return f'"{v.text}"'
    if isinstance(v, Struct):
        body = ','.join(f'{k}={serialize_value(val)}' for k, val in v.items)
        return f'({body})'
    if isinstance(v, ArrayLiteral):
        return f'({",".join(serialize_value(x) for x in v.items)})'
    raise TypeError(f'unknown value: {type(v).__name__}')


def serialize_object(obj: T3DObject, indent: int = 0) -> str:
    ind = '   ' * indent
    head = f'{ind}Begin Object Class={obj.cls or "?"} Name="{obj.name or ""}"'
    if obj.export_path:
        head += f' ExportPath="{obj.export_path}"'
    head += '\n'
    body_lines = []
    for key, val in obj.properties.items():
        body_lines.append(f'{ind}   {key}={serialize_value(val)}')
    for child in obj.children:
        body_lines.append(serialize_object(child, indent + 1).rstrip('\n'))
    tail = f'{ind}End Object\n'
    return head + ('\n'.join(body_lines) + '\n' if body_lines else '') + tail


def serialize_document(doc: T3DDocument) -> str:
    return ''.join(serialize_object(o, indent=0) for o in doc.objects)
