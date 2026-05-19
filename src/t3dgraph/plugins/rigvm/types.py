"""RigVM 클래스 상수·분류 헬퍼."""
from __future__ import annotations

CLASS_PREFIXES = ["/Script/RigVMDeveloper.", "/Script/ControlRigDeveloper."]

NODE_CLASS_SUFFIXES = (
    "RigVMUnitNode", "RigVMDispatchNode", "RigVMFunctionEntryNode",
    "RigVMFunctionReturnNode", "RigVMVariableNode", "RigVMCollapseNode",
    "RigVMFunctionReferenceNode", "RigVMRerouteNode",
)
LINK_CLASS_SUFFIX = "RigVMLink"
PIN_CLASS_SUFFIX = "RigVMPin"
EXECUTE_CPP_TYPE = "FRigVMExecuteContext"


def _suffix(class_path: str) -> str:
    return class_path.rsplit(".", 1)[-1]


def is_node_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) in NODE_CLASS_SUFFIXES


def is_link_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) == LINK_CLASS_SUFFIX


def is_pin_class(class_path: str | None) -> bool:
    return bool(class_path) and _suffix(class_path) == PIN_CLASS_SUFFIX


def is_execution_cpp_type(cpp_type: str | None) -> bool:
    return cpp_type == EXECUTE_CPP_TYPE
