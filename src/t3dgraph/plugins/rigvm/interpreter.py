"""RigVM T3DDocument → 추상 GraphModel."""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from ...core.t3d.resolver import AssetResolver


def _text(v: Value | None) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


def _cls_suffix(obj: T3DObject) -> str | None:
    """T3DObject.cls의 suffix (마지막 '.' 이후) 반환. None이면 None."""
    return (obj.cls or "").rsplit(".", 1)[-1] or None


def _classify_kind(obj: T3DObject) -> str:
    suffix = _cls_suffix(obj) or ""
    if suffix in ("RigVMCollapseNode", "RigVMFunctionReferenceNode"):
        return "function"
    if "ContainedGraph" in obj.properties:
        return "function"
    # property-extension block(cls=None, same name)에서도 속성 확인
    ext_props: dict = {}
    for c in obj.children:
        if c.cls is None and c.name == obj.name:
            ext_props = c.properties
            break
    notation = _text(obj.properties.get("TemplateNotation")
                     or ext_props.get("TemplateNotation")) or ""
    resolved = _text(obj.properties.get("ResolvedFunctionName")
                     or ext_props.get("ResolvedFunctionName")) or ""
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


_ARRAY_PATTERN = re.compile(r"^([A-Za-z_]*?)(\d+)$")


def _sort_array_subpins(subpins: list[Pin]) -> list[Pin]:
    """T3D 배열 직렬화 quirk 정정.

    name이 전부 같은 prefix + 끝 digits면 digit 부분으로 int 정렬.
    예: '0','1','2'           → 0,1,2 (digit-only)
        'Item_0','Item_1'     → 0,1 정렬
        'X','Y','Z'           → 원순서 (배열 아님)
        'Item_0','Element_1'  → 원순서 (prefix 불일치, 안전)
    """
    if not subpins:
        return subpins
    matches = [_ARRAY_PATTERN.match(p.name) for p in subpins]
    if not all(matches):
        return subpins
    prefixes = {m.group(1) for m in matches}
    if len(prefixes) != 1:
        return subpins
    return sorted(subpins, key=lambda p: int(_ARRAY_PATTERN.match(p.name).group(2)))


def _extract_pin_name_from_path(path_token: str) -> str | None:
    """Pins(N)/SubPins(N) 값 형식 '...'PinName'' → 핀 이름 추출."""
    m = re.search(r"'([^']+)'", path_token)
    if m:
        return m.group(1).rsplit(".", 1)[-1]
    return None


def _read_ordered_pin_names(obj: T3DObject, prefix: str) -> list[str] | None:
    """`Pins(N)=...` / `SubPins(N)=...` 속성에서 권위 순서 추출.

    obj.properties 먼저 확인, 없으면 같은 이름의 cls=None 자식 블록 확인.
    """
    pattern = re.compile(rf"^{prefix}\((\d+)\)$")

    def _scan(props: dict) -> list[tuple[int, str]]:
        indexed: list[tuple[int, str]] = []
        for key, value in props.items():
            m = pattern.match(key)
            if m is None:
                continue
            text = _text(value)
            if text is None:
                continue
            name = _extract_pin_name_from_path(text)
            if name:
                indexed.append((int(m.group(1)), name))
        return indexed

    indexed = _scan(obj.properties)
    if not indexed:
        for c in obj.children:
            if c.cls is None and c.name == obj.name:
                indexed = _scan(c.properties)
                break
    if not indexed:
        return None
    indexed.sort(key=lambda iv: iv[0])
    return [name for _, name in indexed]


def _reorder_by_names(pins: list[Pin], names: list[str]) -> list[Pin]:
    """권위 순서(names)대로 pins 재정렬. names에 없는 핀은 원순서로 뒤에."""
    name_set = set(names)
    by_name = {p.name: p for p in pins}
    ordered = [by_name[n] for n in names if n in by_name]
    leftover = [p for p in pins if p.name not in name_set]
    return ordered + leftover


def _sort_pins_exec_first(pins: list[Pin]) -> list[Pin]:
    """실행 핀(is_execution=True)을 앞쪽으로 안정 정렬.

    실행 핀 그룹 내에서 IO(주 실행) > Output(보조 실행) > 기타 순.
    같은 direction 내에서는 원순서 보존(stable sort).
    """
    def _exec_dir_rank(direction: str | None) -> int:
        d = (direction or "").lower()
        if d == "io":
            return 0
        if d == "output":
            return 1
        return 2

    return sorted(pins, key=lambda p: (
        not p.is_execution,
        _exec_dir_rank(p.direction) if p.is_execution else 0,
    ))


def _build_pin(obj: T3DObject) -> Pin:
    cpp_type = _text(obj.properties.get("CPPType"))
    # property-extension block(같은 이름, cls=None)은 subpin 후보에서 제외
    child_pins = [_build_pin(c) for c in obj.children
                  if t.is_pin_class(c.cls) or (c.cls is None and c.name != obj.name)]
    ordered_names = _read_ordered_pin_names(obj, "SubPins")
    if ordered_names is not None:
        child_pins = _reorder_by_names(child_pins, ordered_names)
    else:
        child_pins = _sort_array_subpins(child_pins)
    return Pin(
        name=obj.name or "",
        cpp_type=cpp_type,
        direction=_text(obj.properties.get("Direction")),
        default_value=_text(obj.properties.get("DefaultValue")),
        is_execution=t.is_execution_cpp_type(cpp_type),
        subpins=child_pins,
        raw=dict(obj.properties),
    )


class RigVMGraphInterpreter(AbstractGraphInterpreter):
    def __init__(self, resolver: "AssetResolver | None" = None) -> None:
        self._resolver = resolver

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
            target_pin = g.find_pin(link.target_path)
            if target_pin is not None:
                target_pin.variable_source = var_name
        # 재귀 — 서브그래프 자체에도 variable_refs/links가 있다
        for node in g.nodes:
            if node.subgraph is not None:
                self._annotate_variable_consumers(node.subgraph)
            for extra in node.extra_subgraphs:
                self._annotate_variable_consumers(extra)

    def _interpret_objects(
        self,
        objects: list[T3DObject],
        *,
        label: str | None,
        parent_node: str | None,
        diagnostics: InterpreterDiagnostics,
        depth: int = 0,
        max_depth: int = 64,
    ) -> GraphModel:
        g = GraphModel(label=label, parent_node=parent_node)
        diagnostics.max_depth_seen = max(diagnostics.max_depth_seen, depth)
        if depth >= max_depth:
            g.warnings.append(
                f"interpret 깊이 {depth} >= {max_depth} — 추가 추출 중단 (label={label or '?'})"
            )
            for obj in objects:
                diagnostics.objects_dropped.append(DroppedObject(
                    name=obj.name or "?", cls=_cls_suffix(obj),
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
                    name=obj.name or "?", cls=_cls_suffix(obj),
                    reason="graph at top", parent_obj=parent_node))
                continue
            else:
                diagnostics.objects_dropped.append(DroppedObject(
                    name=obj.name or "?", cls=_cls_suffix(obj),
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
        # property-extension block(같은 이름, cls=None)은 핀 후보에서 제외
        raw_pins = [_build_pin(c) for c in obj.children
                    if t.is_pin_class(c.cls) or (c.cls is None and c.name != obj.name)]
        node_kind = _classify_kind(obj)
        # Sequence 노드는 Pins(N) 권위 정렬 skip — T3D 원본 실행 순서 보존
        if node_kind != "sequence":
            pin_order = _read_ordered_pin_names(obj, "Pins")
            if pin_order is not None:
                raw_pins = _reorder_by_names(raw_pins, pin_order)
        node = Node(
            name=obj.name or "",
            cls=obj.cls,
            pins=_sort_pins_exec_first(raw_pins),
            position=_position(obj),
            raw=dict(obj.properties),
            kind=node_kind,
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
        # F20: FunctionReferenceNode — resolver로 외부 함수 subgraph 연결
        if (
            node.subgraph is None
            and _cls_suffix(obj) == "RigVMFunctionReferenceNode"
        ):
            ref_path_raw = _text(obj.properties.get("ReferencedNode"))
            if not ref_path_raw:
                ref_path_raw = self._extract_lib_node_path_from_header(obj)
            if not ref_path_raw:
                diagnostics.external_refs_unresolved.append(
                    f"{obj.name or '?'} (header parse failed)"
                )
            elif self._resolver is not None:
                ext_obj, reason = self._resolver.resolve_function_reference(ref_path_raw)
                if ext_obj is None:
                    suffix = f" ({reason})" if reason else ""
                    diagnostics.external_refs_unresolved.append(
                        f"{ref_path_raw}{suffix}"
                    )
                else:
                    ext_graph_children = [
                        c for c in ext_obj.children if t.is_graph_class(c.cls)
                    ]
                    diagnostics.contained_graph_count += len(ext_graph_children)
                    for j, ext_child in enumerate(ext_graph_children):
                        ext_sub = self._interpret_objects(
                            ext_child.children,
                            label=f"{node.name}/(ext){ext_child.name or 'graph'}",
                            parent_node=node.name,
                            diagnostics=diagnostics,
                            depth=depth + 1,
                            max_depth=max_depth,
                        )
                        if j == 0 and node.subgraph is None:
                            node.subgraph = ext_sub
                        else:
                            node.extra_subgraphs.append(ext_sub)
            else:
                diagnostics.external_refs_unresolved.append(ref_path_raw)
        g.nodes.append(node)
        suffix = _cls_suffix(obj) or ""
        diagnostics.extracted_per_class[suffix] = (
            diagnostics.extracted_per_class.get(suffix, 0) + 1
        )
        if _cls_suffix(obj) == "RigVMVariableNode":
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

    def _extract_lib_node_path_from_header(self, obj: T3DObject) -> str | None:
        header = obj.properties.get("ReferencedFunctionHeader")
        if not isinstance(header, Struct):
            return None
        known = header.find_path("LibraryPointer", "LibraryNodePath")
        if known is not None:
            return known
        return header.find_first("LibraryNodePath")

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
