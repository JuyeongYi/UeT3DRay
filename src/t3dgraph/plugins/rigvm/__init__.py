"""RigVM 그래프 타입 플러그인 — import 시 self-register."""
from __future__ import annotations
from ...core.registry import default_registry
from ...core.base.plugin import GraphTypePlugin
from .types import CLASS_PREFIXES
from .interpreter import RigVMGraphInterpreter

_PLUGIN = GraphTypePlugin(
    id="rigvm",
    class_prefixes=list(CLASS_PREFIXES),
    interpreter_factory=RigVMGraphInterpreter,
)


def register() -> None:
    reg = default_registry()
    if _PLUGIN.id not in [p.id for p in reg.plugins()]:
        reg.register(_PLUGIN)


register()
