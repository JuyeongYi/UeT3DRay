"""RigVM 노드 객체 → (시그니처 요약, 카테고리)."""
from __future__ import annotations
import re
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.values import Scalar, QuotedString


def _text(v) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


def _suffix(cls: str | None) -> str:
    return cls.rsplit(".", 1)[-1] if cls else ""


_CATEGORY = {
    "RigVMUnitNode": "Unit",
    "RigVMDispatchNode": "Dispatch",
    "RigVMVariableNode": "Variable",
    "RigVMFunctionEntryNode": "Entry",
    "RigVMFunctionReturnNode": "Return",
    "RigVMCollapseNode": "Subgraph",
    "RigVMFunctionReferenceNode": "Subgraph",
    "RigVMRerouteNode": "Reroute",
}


def _parse_signature(sig: str) -> str:
    """'Name::Execute(in T A,out U B)' -> 'Name(T) -> U'. 파싱 실패 시 원문."""
    head, _, tail = sig.partition("(")
    if not tail.endswith(")"):
        return sig
    func_name = head.split("::")[0].strip()
    args_src = tail[:-1]
    inputs: list[str] = []
    outputs: list[str] = []
    if args_src.strip():
        for raw in args_src.split(","):
            tok = raw.strip()
            m = re.match(r"^(in|out)\s+(.+?)(?:\s+\w+)?$", tok)
            if not m:
                continue
            direction, type_part = m.group(1), m.group(2).strip()
            (inputs if direction == "in" else outputs).append(type_part)
    in_part = ", ".join(inputs) if inputs else ""
    out_part = ", ".join(outputs) if outputs else "void"
    return f"{func_name}({in_part}) → {out_part}"


def role_for(obj: T3DObject) -> tuple[str | None, str | None]:
    cls_sfx = _suffix(obj.cls)
    category = _CATEGORY.get(cls_sfx)
    if not category:
        return None, None

    if cls_sfx == "RigVMDispatchNode":
        sig = _text(obj.properties.get("ResolvedFunctionName")) \
            or _text(obj.properties.get("TemplateNotation"))
        if sig:
            return _parse_signature(sig), category
        return None, category

    if cls_sfx == "RigVMUnitNode":
        struct = _text(obj.properties.get("ScriptStruct"))
        if struct:
            return struct.rsplit(".", 1)[-1].rsplit("/", 1)[-1], category
        return obj.name or None, category

    return None, category
