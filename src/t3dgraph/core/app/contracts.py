"""뷰어 view/controller 추상 계약 — 플러그인 오버라이드 seam."""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..base.graph_model import GraphModel
from ..analysis.data_flow import DataFlowResult
from ..analysis.bundle import AnalysisBundle


class AbstractGraphView(ABC):
    @abstractmethod
    def show_graph(self, graph: GraphModel) -> None:
        """주어진 GraphModel을 화면에 렌더링한다."""
        raise NotImplementedError

    @abstractmethod
    def show_analyses(self, bundle: AnalysisBundle) -> None:
        """분석 3종(flow·execution_order·data_flow)을 한 번에 표시한다."""
        raise NotImplementedError

    @abstractmethod
    def show_analysis(self, flow, order) -> None:
        """(deprecated) 분석 결과(FlowResult, 실행 순서)를 분석 도크에 표시한다."""
        raise NotImplementedError

    @abstractmethod
    def show_data_flow(self, result: DataFlowResult) -> None:
        """(deprecated) 데이터 흐름 분석 결과를 계산 흐름 도크에 표시한다."""
        raise NotImplementedError

    @abstractmethod
    def show_error(self, message: str) -> None:
        """오류 메시지를 사용자에게 표시한다."""
        raise NotImplementedError


class AbstractGraphController(ABC):
    @abstractmethod
    def open_file(self, path: str) -> None:
        """.t3d 파일을 열어 파싱·해석한 뒤 view에 렌더링을 지시한다."""
        raise NotImplementedError
