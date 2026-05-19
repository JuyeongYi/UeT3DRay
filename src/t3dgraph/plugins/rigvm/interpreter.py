"""RigVM T3DDocument → 추상 GraphModel."""
from __future__ import annotations
from ..rigvm import types as t
from ...core.base.interpreter import AbstractGraphInterpreter
from ...core.base.graph_model import GraphModel, Node, Pin, Link, VariableRef
from ...core.t3d.document import T3DDocument
from ...core.t3d.objects import T3DObject
from ...core.t3d.values import Value, Scalar, QuotedString, Struct


def _text(v: Value | None) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


def _position(obj: T3DObject) -> tuple[float, float] | None:
    v = obj.properties.get("Position")
    if not isinstance(v, Struct):
        return None
    d = {k: _text(val) for k, val in v.items}
    try:
        return (float(d.get("X", "0")), float(d.get("Y", "0")))
    except (TypeError, ValueError):
        return None


def _build_pin(obj: T3DObject) -> Pin:
    return Pin(
        name=obj.name or "",
        cpp_type=_text(obj.properties.get("CPPType")),
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        subpins=[_build_pin(c) for c in obj.children],
        raw=dict(obj.properties),
    )


class RigVMGraphInterpreter(AbstractGraphInterpreter):
    def interpret(self, doc: T3DDocument) -> GraphModel:
        g = GraphModel()
        for obj in doc.objects:
            if t.is_link_class(obj.cls):
                self._add_link(obj, g)
            elif t.is_node_class(obj.cls):
                self._add_node(obj, g)
            elif obj.cls is None:
                continue
            else:
                self._add_generic(obj, g)
        known = {n.name for n in g.nodes}
        for link in g.links:
            for path in (link.source_path, link.target_path):
                node = path.split(".", 1)[0]
                if node not in known and path not in g.external_refs:
                    g.external_refs.append(path)
        return g

    def _add_link(self, obj: T3DObject, g: GraphModel) -> None:
        src = _text(obj.properties.get("SourcePinPath"))
        tgt = _text(obj.properties.get("TargetPinPath"))
        if src and tgt:
            g.links.append(Link(source_path=src, target_path=tgt))

    def _add_node(self, obj: T3DObject, g: GraphModel) -> None:
        node = Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children if t.is_pin_class(c.cls) or c.cls is None],
            position=_position(obj),
            raw=dict(obj.properties),
        )
        g.nodes.append(node)
        if obj.cls and obj.cls.rsplit(".", 1)[-1] == "RigVMVariableNode":
            self._add_variable_ref(node, g)

    def _add_variable_ref(self, node: Node, g: GraphModel) -> None:
        var_pin = next((p for p in node.pins if p.name == "Variable"), None)
        val_pin = next((p for p in node.pins if p.name == "Value"), None)
        if var_pin and var_pin.default_value:
            g.variable_refs.append(VariableRef(
                variable_name=var_pin.default_value,
                cpp_type=val_pin.cpp_type if val_pin else None,
                node_name=node.name,
            ))

    def _add_generic(self, obj: T3DObject, g: GraphModel) -> None:
        g.warnings.append(f"알 수 없는 클래스 '{obj.cls}' — 제네릭 노드로 폴백")
        g.nodes.append(Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children],
            position=_position(obj),
            raw=dict(obj.properties),
            is_generic=True,
        ))
