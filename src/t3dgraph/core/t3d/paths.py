"""핀 경로·클래스 경로 파싱 헬퍼 (중앙화)."""
from __future__ import annotations


def node_of(pin_path: str) -> str:
    """핀 경로의 노드 세그먼트. 'Node.Pin.Sub' -> 'Node'."""
    return pin_path.split(".", 1)[0]


def pin_segment(pin_path: str, index: int) -> str:
    """핀 경로의 index번째 점-구분 세그먼트. 범위 밖이면 ''."""
    parts = pin_path.split(".")
    return parts[index] if len(parts) > index else ""


def type_suffix(class_path: str | None) -> str:
    """클래스 경로의 마지막 세그먼트. '/Script/X.RigVMUnitNode' -> 'RigVMUnitNode'.
    None이면 '?'."""
    return (class_path or "?").rsplit(".", 1)[-1]
