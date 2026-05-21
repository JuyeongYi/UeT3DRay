"""그래프 스택 — 서브그래프 드릴다운 + 멀티 파일 루트.

각 루트(파일)는 자체 진입 경로(`path`)를 가진다. `current_root` 인덱스가 활성
루트를 가리키며, 그 루트의 path 마지막 원소가 현재 표시 그래프다.

- `open_root(g)`: 새 루트 그래프(새 파일) 추가. 현재 루트가 됨.
- `push(g)`: 현재 루트의 진입 경로에 child 그래프 push.
- `pop()`: 한 단계 back (루트면 noop — path는 항상 길이 1 이상).
- `jump_to(i)`: 현재 루트의 진입 경로 i번째로 점프.
- `roots()`: 모든 루트.
- `current()`: 가장 깊은 현재 그래프 또는 None.
- `segments()`: 현재 루트의 진입 경로 label 시퀀스.

스택은 **PRESERVE-ALL**: GraphModel 인스턴스를 변형하지 않는다.
push/pop 모두 외부에서 받은 참조를 그대로 가리킬 뿐이다.
"""
from __future__ import annotations
from ..base.graph_model import GraphModel


class GraphStack:
    def __init__(self) -> None:
        self._roots: list[GraphModel] = []
        self._paths: list[list[GraphModel]] = []
        self._cur_root: int = -1

    def open_root(self, g: GraphModel) -> None:
        self._roots.append(g)
        self._paths.append([g])
        self._cur_root = len(self._roots) - 1

    def push(self, g: GraphModel) -> None:
        # 빈 스택일 때는 새 루트로 자동 승격한다(편의 폴백). 호출자가 첫
        # 그래프를 push로 진입시킨 의도를 보존 — 드릴다운 의도였다 해도
        # 데이터 손실 없이 첫 화면이 그려진다.
        if self._cur_root < 0:
            self.open_root(g)
            return
        self._paths[self._cur_root].append(g)

    def pop(self) -> None:
        if self._cur_root < 0:
            return
        path = self._paths[self._cur_root]
        if len(path) > 1:
            path.pop()

    def jump_to(self, index: int) -> None:
        if self._cur_root < 0:
            return
        path = self._paths[self._cur_root]
        if 0 <= index < len(path):
            del path[index + 1:]

    def current(self) -> GraphModel | None:
        if self._cur_root < 0:
            return None
        return self._paths[self._cur_root][-1]

    def segments(self) -> list[str]:
        if self._cur_root < 0:
            return []
        return [g.label or "?" for g in self._paths[self._cur_root]]

    def roots(self) -> list[GraphModel]:
        return list(self._roots)

    def select_root(self, index: int) -> None:
        if 0 <= index < len(self._roots):
            self._cur_root = index
