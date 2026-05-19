"""최상위 추상 인터프리터 — 그래프 종류 모듈이 구현한다."""
from __future__ import annotations
from abc import ABC, abstractmethod
from .graph_model import GraphModel
from ..t3d.document import T3DDocument


class AbstractGraphInterpreter(ABC):
    @abstractmethod
    def interpret(self, doc: T3DDocument) -> GraphModel:
        raise NotImplementedError
