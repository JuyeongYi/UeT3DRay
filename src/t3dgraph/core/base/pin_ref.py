"""PinRef — 그래프 내 핀의 안정 식별자."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PinRef:
    """핀의 전체 경로. node + 노드 내 상대 경로(점 구분).

    노드 직속이면 pin_path == "" (Link 한쪽이 노드만 가리키는 비정상 케이스 보존용).
    """
    node: str
    pin_path: str

    @property
    def full(self) -> str:
        return f"{self.node}.{self.pin_path}" if self.pin_path else self.node

    @classmethod
    def parse(cls, full_path: str) -> "PinRef":
        if "." in full_path:
            node, rest = full_path.split(".", 1)
            return cls(node=node, pin_path=rest)
        return cls(node=full_path, pin_path="")
