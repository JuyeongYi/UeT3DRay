"""RigVM 객체 → 사람-친화 표시명 결정. 실패 시 원본 name fallback."""
from __future__ import annotations
import re
from t3dgraph.core.t3d.objects import T3DObject
from t3dgraph.core.t3d.values import Value, Scalar, QuotedString


def _text(v) -> str | None:
    if isinstance(v, (Scalar, QuotedString)):
        return v.text
    return None


_CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _camel_split(s: str) -> str:
    return _CAMEL_SPLIT.sub(" ", s)


def _suffix(cls: str | None) -> str:
    if not cls:
        return ""
    return cls.rsplit(".", 1)[-1]


def display_name_for(obj: T3DObject) -> str:
    """노드 객체의 표시명. 원본 name이 항상 fallback."""
    name = obj.name or ""
    if not obj.cls:
        return name
    sfx = _suffix(obj.cls)

    if sfx == "RigVMUnitNode":
        bare = name
        if bare.startswith("RigUnit_"):
            bare = bare[len("RigUnit_"):]
        bare = re.sub(r"_\d+$", "", bare)
        return _camel_split(bare) or name

    if sfx == "RigVMDispatchNode":
        resolved = _text(obj.properties.get("ResolvedFunctionName"))
        notation = _text(obj.properties.get("TemplateNotation"))
        sig = resolved or notation
        if sig:
            head = sig.split("::")[0].split("(")[0]
            return _camel_split(head) or name
        bare = name
        if bare.startswith("RigVMDispatch_"):
            bare = bare[len("RigVMDispatch_"):]
        bare = re.sub(r"_\d+$", "", bare)
        return _camel_split(bare) or name

    if sfx == "RigVMVariableNode":
        for child in obj.children:
            if child.name == "Variable":
                vt = _text(child.properties.get("DefaultValue"))
                if vt:
                    return vt
        return name

    return name
