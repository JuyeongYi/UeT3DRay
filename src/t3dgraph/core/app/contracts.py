"""뷰어 view/controller 추상 계약 — 플러그인 오버라이드 seam."""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..base.graph_model import GraphModel


class AbstractGraphView(ABC):
    @abstractmethod
    def show_graph(self, graph: GraphModel) -> None:
        """주어진 GraphModel을 화면에 렌더링한다."""
        raise NotImplementedError


class AbstractGraphController(ABC):
    @abstractmethod
    def open_file(self, path: str) -> None:
        """.t3d 파일을 열어 파싱·해석한 뒤 view에 렌더링을 지시한다."""
        raise NotImplementedError
