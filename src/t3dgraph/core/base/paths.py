"""핀 경로·클래스 경로 파싱 헬퍼 (그래프 모델 개념 — core/base 위치).

batch ③ slice α에서 core/t3d/paths.py로부터 이동. core/t3d/paths.py는
1주기 동안 re-export shim으로 유지된다.
"""
from __future__ import annotations


def node_of(full_path: str) -> str:
    """핀 경로의 노드 세그먼트. 'Node.Pin.Sub' -> 'Node'."""
    return full_path.split(".", 1)[0]


def pin_segment(full_path: str, index: int) -> str:
    """핀 경로의 index번째 점-구분 세그먼트. 범위 밖이면 ''."""
    parts = full_path.split(".")
    return parts[index] if len(parts) > index else ""


def pin_rel_path(node_name: str, full_path: str) -> str:
    """노드 이름을 prefix로 떼어낸 핀 상대 경로.

    노드 자체 경로(`node_name == full_path`)면 ''.
    prefix 불일치면 ''(드러나야 할 사실 — 호출부에서 처리).
    """
    if full_path == node_name:
        return ""
    prefix = f"{node_name}."
    if full_path.startswith(prefix):
        return full_path[len(prefix):]
    return ""


def type_suffix(class_path: str | None) -> str:
    """클래스 경로의 마지막 세그먼트. '/Script/X.Foo' -> 'Foo'. None이면 '?'."""
    return (class_path or "?").rsplit(".", 1)[-1]
