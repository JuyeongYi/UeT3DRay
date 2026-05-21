# t3dgraph 정리 batch ④ — AnalysisBundle + 잔여 잡정리 설계

- **작성일**: 2026-05-22 (자율 사이클)
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **선행**: batch ②(2026-05-21) + batch ③(2026-05-21) 완료. master tip = batch ③ 머지 후 상태.

---

## 1. 트리거

사용자 위임 자율 사이클 — 데드라인 2026-05-22 06:00 KST. 백로그(2026-05-22 정합본) 잔여 항목 일소.

본 batch는 정리 성격 — *기능 추가 없음*. FEAT-* 항목은 batch ⑤ 이후로 분리.

---

## 2. 범위

### slice δ — AnalysisBundle (D-B3 + P2c-B2 잔여)

`AppController`가 분석을 `flow → execution_order → data_flow` 셋을 줄세워 호출하고 view에 별도 메서드 3개(`show_analysis(flow, order)` + `show_data_flow(result)`)로 푸시. `MainWindow._render_current`도 분석을 다시 호출 → 단일 출처 위반.

해결: `AnalysisBundle` 도입.

```python
# core/analysis/bundle.py (신규)
@dataclass
class AnalysisBundle:
    flow: FlowResult
    execution_order: list[ExecutionStep]
    data_flow: DataFlowResult

def run(graph: GraphModel) -> AnalysisBundle:
    f = analyze_flow(graph)
    return AnalysisBundle(
        flow=f,
        execution_order=compute_execution_order(graph, f),
        data_flow=analyze_data_flow(graph),
    )
```

`contracts.AbstractGraphView`:

```python
def show_analyses(self, bundle: AnalysisBundle) -> None: ...
```

기존 `show_analysis`·`show_data_flow`는 한 사이클 동안 deprecated re-export(MainWindow가 내부적으로 둘 다 호출). 다음 cycle에서 제거.

`AppController.open_file`이 호출하는 분석 단일 경로:

```python
graph = plugin.interpreter_factory().interpret(doc)
self.view.show_graph_with_analyses(graph, analyses_bundle.run(graph))
```

`MainWindow._render_current`도 같은 함수 호출 — controller·view 둘 다 단일 출처 사용.

### slice ε — 잡정리 묶음 (P1.5-A1 + P2a-B2 + P2c-B1 + BL1-B2)

- **P1.5-A1**: `ValueParseError.pos` — `t3d/values.py`의 예외 클래스에 `pos: int` 속성 추가. parse 함수가 raise 시 위치 전달.
- **P2a-B2**: `contracts.AbstractGraphView.show_error(message: str)` 추상 메서드 추가. MainWindow는 이미 구현. controller의 `getattr` 덕타이핑 제거 → 직접 호출.
- **P2c-B1**: `NavigablePanel`에 `highlight_node(node_name | None)` 공통 시그니처. 각 패널은 `_set_current_item(item)` 내부 메서드만 override. 보일러플레이트 4곳(inspector / analysis_panel / execution_order_panel / data_flow_panel) → 1곳으로 압축.
- **BL1-B2**: `scene._connected_paths_by_node`에서 `pin_segment(path, 0)` → `node_of(path)` 일관화.

---

## 3. 슬라이스 발주

| 슬라이스 | 내용 | 의존 | 산출 plan |
|---|---|---|---|
| δ | AnalysisBundle | 없음 | docs/superpowers/plans/2026-05-22-t3dgraph-batch4-δ-analysis-bundle.md |
| ε | 잡정리 묶음 | 없음(δ와 다른 파일 영역) | docs/superpowers/plans/2026-05-22-t3dgraph-batch4-ε-cleanup.md |

병렬 가능. router queue에 동시 발주.

---

## 4. 불변식

- **PRESERVE-ALL** (노드 보존): 변경 없음.
- **PRESERVE-INFO** (정보 보존): AnalysisBundle은 *3개 분석 결과를 묶을 뿐* — 정보 손실 ✗. `show_analysis`·`show_data_flow`도 한 cycle 유지(호출 사이트 분산 위험 회피).

---

## 5. 비목표

- FEAT-* — batch ⑤+ 별도 사이클.
- `core/t3d/paths.py` 파일 제거 — batch ⑤에 묶을 후보 (re-export shim 1주기 경과).

---

## 6. 자율 결정 사항 기록

silent 모드 + 자율 위임. 본 batch의 결정:

1. AnalysisBundle은 별도 `core/analysis/bundle.py` 파일에 두기 (기존 모듈 hub 패턴 유지).
2. `show_analyses` 도입 시점에 `show_analysis`·`show_data_flow`는 *유지* — deprecation 한 cycle 두고 제거.
3. `NavigablePanel`에 `highlight_node`를 *템플릿 메서드* 패턴으로 — 각 패널이 `_lookup_item(name) -> QWidget | None`만 구현.
