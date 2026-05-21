# t3dgraph 정리 batch ③ — "상위 레이어 정보 묵살" 패턴 일소 설계

- **작성일**: 2026-05-21
- **상태**: 브레인스토밍 산출물 — 사용자 리뷰 대기
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **선행 batch**: 2026-05-21 사용자 피드백 batch ②(F1·F3·F5·F6·F7·F8·F9·F2 머지 완료, master `d173fab`)

---

## 1. 트리거

batch ② 두 슬라이스 PR에 대해 improver가 보낸 findings 18건(D-A1~A3·B1~B3·FEAT-6~8 + C-A1~A3·B1~B3·FEAT-9~11). improver 권고: **D-A1 핀 단위 정보 손실**과 **C-A1 다중 ContainedGraph 자식 silent drop**이 같은 패턴 — "상위 레이어가 하위 정보를 침묵으로 묵살". 이 두 축을 잡으면 D-A2/A3·FEAT-6/7도 자연 해결.

---

## 2. 검증 — 현 코드 상태 (master `d173fab`)

### 2.1 D-A1 핀 단위 정보 손실 (`core/analysis/data_flow.py`)

`analyze_data_flow`는 link를 노드 쌍 `(s_node, t_node)`로 평탄화:

```python
# core/analysis/data_flow.py:47-54
for link in graph.links:
    s_node = node_of(link.source_path)
    t_node = node_of(link.target_path)
    s_rel = link.source_path[len(s_node) + 1:] if "." in link.source_path else ""
    t_rel = link.target_path[len(t_node) + 1:] if "." in link.target_path else ""
    if (s_node, s_rel) in exec_paths or (t_node, t_rel) in exec_paths:
        continue
    edges.append((s_node, t_node))   # ← 핀 정보 손실
```

`s_rel`/`t_rel`을 *exec 필터*로만 쓰고 버림. 결과적으로 어느 핀이 어느 핀에 연결됐는지 알 수 없어 인스펙터·툴팁·diff·다중 링크 구분 불가.

### 2.2 D-A2 패널 multi-index (`core/app/data_flow_panel.py`)

`_items.setdefault(dep.node, item)` — 한 노드가 두 sink 트리에 등장 시 첫 항목만 인덱싱. 두 번째 위치는 `activate_node`/`highlight_node` 응답 안 함.

### 2.3 D-A3 adjacency 중복 (`core/analysis/data_flow.py:56-60`)

```python
for s, t in edges:
    outputs_of.setdefault(s, []).append(t)
    inputs_of.setdefault(t, []).append(s)
```

같은 source 노드의 여러 핀이 같은 target 노드의 여러 핀에 연결되면 `(s,t)` 쌍이 여러 번 → `inputs_of[t]`에 동일 항목 중복.

### 2.4 D-B2 `pin_rel_path` 중복 로직

`_collect_exec_pin_paths.walk`(`full[len(node_name)+1:]`)와 `analyze_data_flow`(`link.source_path[len(s_node)+1:] if "." in ...`)가 동일 슬라이싱을 두 모양으로 표현. `.` 부재 케이스 처리도 분산.

### 2.5 BL1-B1 paths.py 위치

`core/t3d/paths.py`에 `node_of`, `pin_segment`, `type_suffix` — `core/t3d`는 그래프-타입 무관 *구조 파서* 영역. 핀/클래스 경로 헬퍼는 그래프 모델 개념이므로 `core/base`가 적합.

### 2.6 C-A1 다중 자식 silent drop (`plugins/rigvm/interpreter.py:117-124`)

```python
for child in obj.children:
    if t.is_graph_class(child.cls):
        node.subgraph = self._interpret_objects(...)
        break          # ← 두 번째부터 무경고 drop
```

top-level RigVMGraph는 `warnings.append`로 알리는데 자식 케이스는 무경고 — 대칭 깨짐.

### 2.7 C-A2 재귀 깊이 무가드

`_interpret_objects`가 자기 호출로 펼치되 `max_depth`나 seen set 없음. cyclic ContainedGraph 입력 시 stack overflow.

### 2.8 잡정리 항목

- C-A3 chevron 어포던스(`▶`만, hover cursor·툴팁 없음)
- C-B1 `GraphStack.push`의 빈-스택 폴백(`open_graph`가 유일 진입점인데 두 의미 혼합)
- C-B2 `BreadcrumbBar.click_segment`, `NodeItem.simulate_header_double_click` 프로덕션 public 노출
- C-B3 `_NodeItemBus` 모든 노드에 무조건 생성
- D-B1 `show_data_flow` 타입힌트 누락

---

## 3. 지도 원칙

PRESERVE-ALL 불변식은 batch ②에서 확립. batch ③은 그 위에 **PRESERVE-INFO** 보조 원칙을 더한다:

> **PRESERVE-INFO:** 상위 레이어(분석 결과, 인터프리터 출력)는 하위 레이어가 제공한 정보를 절대 묵살(drop·중복·collapse)하지 않는다. 정보를 *압축*해야 하면 압축 사유를 warning으로 남기거나 별도 슬롯에 보존한다.

이 원칙으로:
- D-A1: link의 핀 정보를 `data_edges`에 끝까지 보존
- D-A3: adjacency 중복은 압축이 아니라 *드러내야 할 사실*(다중 링크) — set 누적 후 정렬 노출
- C-A1: 두 번째 자식 graph가 있으면 warning + 모델에도 보존(둘 다 가능한 `subgraphs: list`)
- C-A2: 깊이 cap 초과 시 warning(silent return ✗)

---

## 4. 범위

본 batch 안:

### slice α — 핀 단위 데이터 흐름 모델 (D-A1·A2·A3·B1·B2 + BL1-B1)
- `data_flow.py`: `DataFlowEdge(source: PinRef, target: PinRef)` 형 도입. `data_edges: list[DataFlowEdge]`.
- adjacency: `inputs_of/outputs_of`를 *핀 단위* `dict[str, list[PinRef]]`로 확장하되 노드 단위 access 헬퍼 함께 노출.
- adjacency 중복 제거(set 누적 후 정렬 리스트).
- `pin_rel_path(node_name, full_path)` 헬퍼를 `core/base/paths.py`(이동 후 새 위치)로 추출. 기존 `core/t3d/paths.py`는 그대로 두되 동일 함수 두 군데 노출은 1주기 deprecation으로 단순화.
- 패널: 노드 + 핀 라벨 모두 표시(`A.Out → C.In`), `_items: dict[str, list[item]]`로 다중 인덱싱, "[위 참조]" 표식.
- `show_data_flow` 타입힌트.

### slice β — 인터프리터 정보 보존 (C-A1·A2)
- `_add_node`: 자식 RigVMGraph 첫 매치 break 제거. 둘 이상이면 `Node.subgraph`(첫 개) + warning + `Node.extra_subgraphs: list[GraphModel]`(나머지).
- `_interpret_objects` 재귀 깊이 cap(`max_depth=64`) + 초과 시 warning + 그 자리에 비어 있는 GraphModel(label 표기).

### slice γ — UX·API 잡정리 (C-A3·B1·B2·B3)
- subgraph 보유 NodeItem에 `setCursor(PointingHandCursor)` + `setToolTip`.
- `GraphStack.push`에서 빈-스택 폴백 제거 → 사전조건 위반 시 `RuntimeError`(또는 `assert`).
- `BreadcrumbBar.click_segment` → `_click_for_test`, `NodeItem.simulate_header_double_click` → `_emit_for_test` 또는 `tests/helpers.py`로 이동.
- `_NodeItemBus`를 `node.subgraph is not None` 또는 핀 행이 있을 때만 lazy-init. `mouseDoubleClickEvent`도 헤더·핀 미보유 시 `super()` 위임.

본 batch 밖:

- **D-B3 AnalysisBundle 패턴** — controller/contracts/view 3곳 묶기. 본 batch의 D-A1·D-A2 변경과 충돌 없이 별도 cycle에서 처리 가능(batch ④ 후보).
- **FEAT-6~11** — 기능 추가. 백로그 유지. D-A1 이후 FEAT-6(CLI dataflow), FEAT-7(파일 간 diff)는 즉시 가능해짐을 메모.
- 옛 백로그 P1.5·P2a·P2b·P2c·P2d 항목 — 본 패턴과 결이 다름. 별도 cycle.

---

## 5. 아키텍처 변경 요지

### 5.1 `PinRef` 모델 도입 (slice α)

`core/base/graph_model.py`(또는 `core/base/pin_ref.py`):

```python
@dataclass(frozen=True)
class PinRef:
    """핀의 전체 경로 — 노드 + 노드 내 상대 경로."""
    node: str
    pin_path: str       # "Pin" 또는 "Pin.Sub.Sub2"; 노드 직속이면 ""

    @property
    def full(self) -> str:
        return f"{self.node}.{self.pin_path}" if self.pin_path else self.node

    @classmethod
    def parse(cls, full_path: str) -> "PinRef":
        if "." in full_path:
            node, rest = full_path.split(".", 1)
            return cls(node=node, pin_path=rest)
        return cls(node=full_path, pin_path="")
```

`DataFlowResult` 확장:

```python
@dataclass(frozen=True)
class DataFlowEdge:
    source: PinRef
    target: PinRef


@dataclass
class DataFlowResult:
    data_edges: list[DataFlowEdge]                                  # 핀 단위
    inputs_of: dict[str, list[DataFlowEdge]]                        # 노드 → 들어오는 엣지 (중복 제거)
    outputs_of: dict[str, list[DataFlowEdge]]                       # 노드 → 나가는 엣지
    incoming_nodes: dict[str, list[str]]                            # 호환 — 노드 단위 (set→sorted list)
    outgoing_nodes: dict[str, list[str]]                            # 호환 — 노드 단위
    sinks: list[str]
    sources: list[str]
    isolated: list[str]
    all_nodes: list[str]
```

`dependency_tree`는 노드 단위 그대로(시각화 트리 단순 유지) — 핀 정보는 별도 lookup API로 제공.

### 5.2 `pin_rel_path` 헬퍼 + paths 이동 (slice α)

신규 `core/base/paths.py`:

```python
def node_of(full_path: str) -> str: ...
def pin_segment(full_path: str, index: int) -> str: ...
def pin_rel_path(node_name: str, full_path: str) -> str:
    """노드 이름을 prefix로 떼어낸 핀 상대 경로. 단일 세그먼트(노드만) → ''."""
    if full_path == node_name:
        return ""
    prefix = f"{node_name}."
    return full_path[len(prefix):] if full_path.startswith(prefix) else ""
def type_suffix(class_path: str | None) -> str: ...
```

기존 `core/t3d/paths.py`는 본 batch 동안:
- 모든 심볼을 `core/base/paths`에서 re-export(`from t3dgraph.core.base.paths import *`)
- 신규 import는 `core/base/paths`만 사용
- batch ④에서 `core/t3d/paths.py` 자체 제거

### 5.3 인터프리터 다중 자식 + 재귀 가드 (slice β)

`graph_model.py`:

```python
@dataclass
class Node:
    ...
    subgraph: "GraphModel | None" = None
    extra_subgraphs: list["GraphModel"] = field(default_factory=list)   # NEW
```

`_add_node`:

```python
graph_children = [c for c in obj.children if t.is_graph_class(c.cls)]
for i, child in enumerate(graph_children):
    sub = self._interpret_objects(
        child.children,
        label=f"{node.name}/{child.name or 'graph'}",
        parent_node=node.name,
        depth=current_depth + 1,
    )
    if i == 0:
        node.subgraph = sub
    else:
        node.extra_subgraphs.append(sub)
        g.warnings.append(
            f"노드 '{node.name}'에 RigVMGraph 자식 {len(graph_children)}개 — "
            f"두 번째 이후는 Node.extra_subgraphs에 보존"
        )
```

`_interpret_objects`에 `depth` 파라미터 + cap:

```python
def _interpret_objects(self, objects, *, label, parent_node, depth=0, max_depth=64):
    if depth >= max_depth:
        g = GraphModel(label=label, parent_node=parent_node)
        g.warnings.append(f"interpret 깊이 {depth} 초과 — 추가 추출 중단")
        return g
    ...
```

### 5.4 잡정리 (slice γ)

각각의 변경은 §4·§2에 명시.

---

## 6. 슬라이스 발주 순서

| 슬라이스 | 의존 | 비고 |
|---|---|---|
| α 핀 단위 데이터 모델 | 없음 | data_flow + paths 헬퍼 + 패널 — 가장 굵음 |
| β 인터프리터 정보 보존 | graph_model(α와 동일 파일 수정) — α 후 |
| γ UX·API 잡정리 | 없음(독립) | 작아서 한 번에 |

권장 발주: **α → (β·γ 병렬)**. α의 graph_model.py 변경(`PinRef` 추가)이 β의 `Node.extra_subgraphs` 추가와 같은 파일 — α 머지 후 β 진입이 conflict 없음. γ는 다른 파일이라 α와 병렬도 가능하나 implementer 큐 상태 따라 router 재량.

---

## 7. 위험 / 미해결

### 7.1 노드 단위 API 호환

batch ②의 DataFlowPanel·tests가 `inputs_of/outputs_of`를 `dict[str, list[str]]`로 소비. α에서 형이 `dict[str, list[DataFlowEdge]]`로 바뀌면 회귀. 호환을 위해 `incoming_nodes`/`outgoing_nodes`를 별도 슬롯으로 추가(§5.1) — 기존 소비자는 그쪽을 가리키도록 일괄 변경. DataFlowResult API 변경은 한 슬라이스 안에서 완결.

### 7.2 `core/t3d/paths.py` 제거 시점

본 batch에서 즉시 제거하면 외부 import(테스트 포함) 전부 동시 수정 필요 — 회귀 위험. **re-export만 하고 제거는 batch ④로 미룸**. 본 batch 종료 시점에 깃 grep으로 `from t3dgraph.core.t3d.paths` 잔존 카운트를 0으로 만들고 batch ④에서 파일 제거.

### 7.3 `extra_subgraphs` UI 노출

slice β는 모델·warning까지. UI 측 표시(브레드크럼 어디 표시? chevron 여러 개?)는 의도적 deferred — 본 사이클 사용자 피드백을 보고 잡음.

### 7.4 cap 값 64

`max_depth=64`는 RigVM 실데이터 기준 충분히 큼(샘플은 최대 3단). 합성 cyclic 입력에서 stack 보호. 너무 작으면 정상 깊은 그래프를 자름 — sample fail 시 cap 상향.

### 7.5 PinRef equality

`@dataclass(frozen=True)` — hashable. set/dict 키 사용 가능. 같은 핀에 두 link 들어오는 케이스(`A.Out → B.In` + `A.Out → B.In` 라벨만 다른 변형)는 `DataFlowEdge` 자체가 freezing이라 set으로 dedupe 가능.

---

## 8. 테스트 전략

- **slice α**:
  - `PinRef.parse` round-trip 단위
  - 노드 쌍 동일·핀 다른 다중 링크가 `data_edges`에 각각 별도 엣지로 남는지
  - `inputs_of/outputs_of` 중복 제거 후 deterministic order
  - 패널 핀 라벨 렌더 + 같은 노드 두 번 등장 시 모두 인덱싱 + "[위 참조]" 표식
  - `pin_rel_path` 빈 prefix·실패 경로 케이스
- **slice β**:
  - 한 노드 RigVMGraph 자식 2개 → 첫 개 `subgraph`, 두 번째 `extra_subgraphs`, warning 1건
  - 합성 cyclic ContainedGraph → cap 발동 + warning + 빈 GraphModel 반환
  - 기존 single-subgraph 케이스 회귀 없음
- **slice γ**:
  - chevron 노드의 cursor/툴팁
  - `GraphStack.push` 빈 스택에서 호출 시 RuntimeError
  - 테스트 헬퍼 함수가 `_` prefix 또는 helpers 모듈로 이동
  - `_NodeItemBus`가 subgraph + 핀 둘 다 없는 노드엔 미생성(`hasattr` 확인)

---

## 9. 비목표 / Defer

| 항목 | 처리 |
|---|---|
| D-B3 AnalysisBundle 패턴 | batch ④ 후보. 본 batch의 DataFlowResult API 변경 후 보면 view 측 푸시 메서드가 더 늘어나(F2 추가 + 핀 단위 lookup 등) AnalysisBundle 이점이 또렷해짐. |
| FEAT-6 CLI `dataflow` | 백로그 유지. D-A1 이후 핀 정보를 텍스트로 덤프하기 쉬워짐 — 본 batch 완료 시점에서 사용자 의향 확인 후 별도 작업. |
| FEAT-7 파일 간 dataflow diff | 백로그 유지. |
| FEAT-8 sink compute trace | 백로그 유지. FEAT-5 execution-order 코드형과 짝 — 함께 별도 작업 권장. |
| FEAT-9 뒤로/위로 단축키 | 백로그 유지. C-B2 정리 후 단축키 hook 비용 작음 — 다음 사이클. |
| FEAT-10 멀티 파일 탭 UI | 백로그 유지. `GraphStack.select_root`가 이미 받쳐 줌. |
| FEAT-11 서브그래프 미니맵 | 백로그 유지. 별도 UX 작업. |
| `core/t3d/paths.py` 파일 제거 | batch ④. 본 batch는 re-export까지. |
| `extra_subgraphs` UI 노출 | 사용자 피드백 후 별도 작업. |
| 옛 백로그 P1.5/P2a/P2b/P2c/P2d/BL1-B2 | 본 batch와 결 다름. 별도 cycle. |

---

## 10. 사용자 결정 요청

silent 모드 진행. 다음 두 항목은 사용자 의향 확인 권장:

1. **D-B3 AnalysisBundle 본 batch 포함 여부** — 본 스펙은 deferred 권장(batch ④). 본 batch에 같이 넣고 싶다면 알려주세요. 들어가면 slice δ로 controller·contracts·DataFlowPanel·MainWindow가 한 묶음으로 더 바뀝니다.
2. **slice 발주 순서** — α → (β·γ 병렬) 권장. 다르게 원하면 의견.

답이 없으면 위 권장대로 plan 작성·dispatch.
