# t3dgraph batch ⑦ — 분석 시각화 (FEAT-7, FEAT-8) 설계

- **작성일**: 2026-05-22 자율 사이클

## 범위

- **FEAT-7** 두 t3d 파일 간 데이터 흐름 diff — 동일 sink 기준 의존 트리 추가/제거/깊이 변화.
- **FEAT-8** Sink 단위 "compute trace" 코드형 렌더 — DAG depth(레벨)별 의존 노드 평탄화. FEAT-5와 짝.

## 슬라이스

- **θ-1** FEAT-8 compute trace — `DataFlowPanel`에 sink 선택 시 코드형 트레이스. 새 모듈 `core/analysis/compute_trace.py` + 패널 보조 뷰.
- **θ-2** FEAT-7 dataflow diff — CLI 서브커맨드 `t3dgraph diff <a.t3d> <b.t3d>` + JSON 출력. 두 GraphModel을 비교해 sink별 변경 요약.

## 아키텍처

### θ-1 compute trace

```python
# core/analysis/compute_trace.py
@dataclass
class TraceLevel:
    depth: int
    nodes: list[str]

def compute_trace(sink: str, incoming_nodes: dict[str, list[str]],
                  max_depth: int = 64) -> list[TraceLevel]:
    """BFS로 sink에서 ancestor 레벨별 그룹."""
```

DataFlowPanel에 sink 항목 활성화 시 별도 텍스트 박스(또는 트리)로 trace 표시. 출력 예:

```
sink: B
  level 1: A
  level 2: Const
```

### θ-2 dataflow diff

```python
# core/analysis/data_flow_diff.py
@dataclass
class DataFlowDiff:
    sinks_only_in_a: list[str]
    sinks_only_in_b: list[str]
    sinks_common: list[str]
    per_sink: dict[str, "PerSinkDiff"]


@dataclass
class PerSinkDiff:
    added_ancestors: list[str]
    removed_ancestors: list[str]
    depth_changes: dict[str, tuple[int, int]]    # node → (depth_a, depth_b)


def diff_data_flow(a: DataFlowResult, b: DataFlowResult) -> DataFlowDiff:
    ...
```

CLI 신규 서브커맨드 `diff`:

```
t3dgraph diff <file_a> <file_b> [--json] [--lenient]
```

## 불변식

- PRESERVE-ALL/INFO: 변경 없음.

## 비목표

- diff UI — CLI 우선. 패널 추가는 다음 사이클.
- compute trace의 UI 위치 — 본 batch는 *기본 표시*만. 정렬·필터는 후속.
