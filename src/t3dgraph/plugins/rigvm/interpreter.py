"""RigVM T3DDocument → 추상 GraphModel."""
from __future__ import annotations
from ..rigvm import types as t
from ...core.base.interpreter import AbstractGraphInterpreter
from ...core.base.graph_model import GraphModel, Node, Pin, Link, VariableRef
from ...core.t3d.document import T3DDocument
from ...core.t3d.objects import T3DObject
from ...core.t3d.values import Value, Scalar, QuotedString, Struct
from ...core.t3d.paths import node_of
from .display_name import display_name_for
from .role import role_for


def _text(v: Value | None) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


def _classify_kind(obj: T3DObject) -> str:
    suffix = (obj.cls or "").rsplit(".", 1)[-1]
    if suffix in ("RigVMCollapseNode", "RigVMFunctionReferenceNode"):
        return "function"
    if "ContainedGraph" in obj.properties:
        return "function"
    notation = _text(obj.properties.get("TemplateNotation")) or ""
    resolved = _text(obj.properties.get("ResolvedFunctionName")) or ""
    if "ArrayIterator" in notation:
        return "loop"
    if "Sequence" in resolved or "Sequence" in (obj.name or ""):
        return "sequence"
    return "node"


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
    cpp_type = _text(obj.properties.get("CPPType"))
    return Pin(
        name=obj.name or "",
        cpp_type=cpp_type,
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        is_execution=t.is_execution_cpp_type(cpp_type),
        subpins=[_build_pin(c) for c in obj.children],
        raw=dict(obj.properties),
    )


class RigVMGraphInterpreter(AbstractGraphInterpreter):
    def interpret(self, doc: T3DDocument) -> GraphModel:
        return self._interpret_objects(doc.objects, label=None, parent_node=None)

    def _interpret_objects(
        self,
        objects: list[T3DObject],
        *,
        label: str | None,
        parent_node: str | None,
    ) -> GraphModel:
        g = GraphModel(label=label, parent_node=parent_node)
        for obj in objects:
            if t.is_link_class(obj.cls):
                self._add_link(obj, g)
            elif t.is_node_class(obj.cls):
                self._add_node(obj, g)
            elif obj.cls is None:
                continue
            elif t.is_graph_class(obj.cls):
                # 최상위에 RigVMGraph가 나타나면 그 자식을 그대로 풀어 처리
                # (보통 ContainedGraph는 _add_node 내에서 처리되므로 여기 도달 드물다)
                continue
            else:
                self._add_generic(obj, g)
        known = {n.name for n in g.nodes}
        for link in g.links:
            for path in (link.source_path, link.target_path):
                node = node_of(path)
                if node not in known and path not in g.external_refs:
                    g.external_refs.append(path)
        return g

    def _add_link(self, obj: T3DObject, g: GraphModel) -> None:
        src = _text(obj.properties.get("SourcePinPath"))
        tgt = _text(obj.properties.get("TargetPinPath"))
        if src and tgt:
            g.links.append(Link(source_path=src, target_path=tgt))

    def _add_node(self, obj: T3DObject, g: GraphModel) -> None:
        summary, category = role_for(obj)
        node = Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children if t.is_pin_class(c.cls) or c.cls is None],
            position=_position(obj),
            raw=dict(obj.properties),
            kind=_classify_kind(obj),
            display_name=display_name_for(obj),
            role_summary=summary,
            role_category=category,
        )
        # ContainedGraph 자식 발견 → 재귀로 subgraph 부착
        for child in obj.children:
            if t.is_graph_class(child.cls):
                node.subgraph = self._interpret_objects(
                    child.children,
                    label=f"{node.name}/{child.name or 'graph'}",
                    parent_node=node.name,
                )
                break
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
        summary, category = role_for(obj)
        g.nodes.append(Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=[_build_pin(c) for c in obj.children],
            position=_position(obj),
            raw=dict(obj.properties),
            is_generic=True,
            kind=_classify_kind(obj),
            display_name=display_name_for(obj),
            role_summary=summary,
            role_category=category,
        ))
