"""RigVM T3DDocument → 추상 GraphModel."""
from __future__ import annotations
from ..rigvm import types as t
from ...core.base.interpreter import AbstractGraphInterpreter
from ...core.base.graph_model import (
    GraphModel, Node, Pin, Link, VariableRef,
    InterpreterDiagnostics, DroppedObject,
)
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
        diag = InterpreterDiagnostics()
        g = self._interpret_objects(
            doc.objects, label=None, parent_node=None, diagnostics=diag)
        g.diagnostics = diag
        self._annotate_variable_consumers(g)     # F16
        return g

    def _annotate_variable_consumers(self, g: GraphModel) -> None:
        """variable_refs + links → 각 소비 핀에 variable_source 부여."""
        var_outputs: dict[str, str] = {}   # "VariableNode.Value" → variable_name
        for ref in g.variable_refs:
            var_outputs[f"{ref.node_name}.Value"] = ref.variable_name
        for link in g.links:
            var_name = var_outputs.get(link.source_path)
            if var_name is None:
                continue
            target_pin = self._locate_pin(g, link.target_path)
            if target_pin is not None:
                target_pin.variable_source = var_name
        # 재귀 — 서브그래프 자체에도 variable_refs/links가 있다
        for node in g.nodes:
            if node.subgraph is not None:
                self._annotate_variable_consumers(node.subgraph)
            for extra in node.extra_subgraphs:
                self._annotate_variable_consumers(extra)

    def _locate_pin(self, g: GraphModel, path: str) -> "Pin | None":
        """'NodeName.PinName[.SubPin...]' → Pin 객체. 없으면 None."""
        parts = path.split(".")
        if not parts:
            return None
        node = g.node_by_name(parts[0])
        if node is None:
            return None
        cur_pins = node.pins
        last = None
        for name in parts[1:]:
            pin = next((p for p in cur_pins if p.name == name), None)
            if pin is None:
                return None
            last = pin
            cur_pins = pin.subpins
        return last

    def _interpret_objects(
        self,
        objects: list[T3DObject],
        *,
        label: str | None,
        parent_node: str | None,
        diagnostics: InterpreterDiagnostics | None = None,
        depth: int = 0,
        max_depth: int = 64,
    ) -> GraphModel:
        if diagnostics is None:
            diagnostics = InterpreterDiagnostics()
        g = GraphModel(label=label, parent_node=parent_node)
        diagnostics.max_depth_seen = max(diagnostics.max_depth_seen, depth)
        if depth >= max_depth:
            g.warnings.append(
                f"interpret 깊이 {depth} >= {max_depth} — 추가 추출 중단 (label={label or '?'})"
            )
            for obj in objects:
                diagnostics.objects_dropped.append(DroppedObject(
                    name=obj.name or "?", cls=obj.cls,
                    reason="depth cap", parent_obj=parent_node))
            return g
        for obj in objects:
            if t.is_link_class(obj.cls):
                self._add_link(obj, g)
            elif t.is_node_class(obj.cls):
                self._add_node(obj, g, diagnostics=diagnostics,
                               depth=depth, max_depth=max_depth)
            elif obj.cls is None:
                continue
            elif t.is_graph_class(obj.cls):
                # 최상위에 RigVMGraph가 직접 나타나는 케이스 — 일반적으로
                # ContainedGraph는 _add_node 안에서 처리되므로 여기 도달은 드물다.
                # 발생 시 자식 노드가 소실되므로 경고를 남긴다.
                g.warnings.append(
                    f"최상위에 RigVMGraph 객체 '{obj.name or '?'}' 발견 — "
                    f"자식 {len(obj.children)}개가 추출되지 않음"
                )
                diagnostics.objects_dropped.append(DroppedObject(
                    name=obj.name or "?", cls=obj.cls,
                    reason="graph at top", parent_obj=parent_node))
                continue
            else:
                diagnostics.objects_dropped.append(DroppedObject(
                    name=obj.name or "?", cls=obj.cls,
                    reason="unknown class", parent_obj=parent_node))
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

    def _add_node(self, obj: T3DObject, g: GraphModel, *,
                  diagnostics: InterpreterDiagnostics,
                  depth: int = 0, max_depth: int = 64) -> None:
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
        # ContainedGraph 자식 전부 수집 — 첫 개는 subgraph, 나머지는 extra_subgraphs (C-A1)
        graph_children = [c for c in obj.children if t.is_graph_class(c.cls)]
        diagnostics.contained_graph_count += len(graph_children)
        for i, child in enumerate(graph_children):
            sub = self._interpret_objects(
                child.children,
                label=f"{node.name}/{child.name or 'graph'}",
                parent_node=node.name,
                diagnostics=diagnostics,
                depth=depth + 1,
                max_depth=max_depth,
            )
            # 깊이 cap 경고를 상위 그래프까지 전파
            g.warnings.extend(w for w in sub.warnings if "깊이" in w)
            if i == 0:
                node.subgraph = sub
            else:
                node.extra_subgraphs.append(sub)
        if len(graph_children) > 1:
            g.warnings.append(
                f"노드 '{node.name}'에 RigVMGraph 자식 {len(graph_children)}개 — "
                f"첫 개는 subgraph, 나머지 {len(graph_children) - 1}개는 extra_subgraphs"
            )
        g.nodes.append(node)
        suffix = (obj.cls or "").rsplit(".", 1)[-1]
        diagnostics.extracted_per_class[suffix] = (
            diagnostics.extracted_per_class.get(suffix, 0) + 1
        )
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
