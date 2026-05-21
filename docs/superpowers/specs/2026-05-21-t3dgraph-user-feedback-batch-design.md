# t3dgraph 사용자 피드백 정리 batch — 설계 문서

- **작성일**: 2026-05-21
- **상태**: 브레인스토밍 산출물 — 사용자 리뷰 대기
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **위치**: Phase 2d 완료 직후 정리 batch ② 격(格). 이전 정리 batch ①(2026-05-19) 다음 차례.

---

## 1. 트리거

2026-05-21 사용자 피드백 10건 중 BP(블루프린트) 변형 요청 1건을 제외한 9건. 모두 RigVM(`Orion_WorkStation_Rig_Analysis` 샘플) 기준으로 코드 재현 확인 완료.

원문(요지):

1. 노드 이름이 UI 표시명이 아니라 클래스 이름이라 매칭 안 됨
2. 실행 순서 창이 실행-핀 있는 노드만 보여 기능 파악 제한 — 계산 결과(데이터 흐름)가 더 중요
3. 각 노드의 역할을 알 수 있으면 좋겠다
4. 직접 그래프를 만들고 싶다
5. 브레드크럼 UI로 여러 그래프를 한 번에
6. 서브그래프가 제대로 안 나옴 (같은 에셋 안이면 그나마 나옴)
7. "연결된 핀만 보기" 옵션이 비정상
8. 연결된 핀이 2배로 늘어남
9. 깊이 펼침을 전체가 아니라 노드/파라미터 단위로 지정

추가 사용자 지침: **그래프 그릴 시 생략되는 노드는 없어야 한다.**

---

## 2. 검증 결과 — 현 코드 상태

각 피드백을 코드와 대조한 결과:

| ID | 피드백 | 현 코드 | 결론 |
|---|---|---|---|
| **F1** | 노드 이름 ≠ 표시명 | `RigVMGraphInterpreter._add_node`가 `Node.name = obj.name`(예: `RigUnit_BeginExecution`, `RigVMDispatch_GetItemAtIndex_3`). T3D 객체 이름은 UE 내부 식별자임. UE 그래프 에디터에서 보이는 라벨("Begin Execution", "Get Item At Index")은 별도 메타 — 본 데이터엔 직접 미수집. | 유효. 별칭(alias) 인덱스 도입 필요. |
| **F2** | 실행 순서가 exec-pin만 | `core/analysis/flow.py` `_exec_pin_index`가 `EXECUTE_CPP_TYPE=FRigVMExecuteContext`만 통과. `compute_execution_order`는 flow의 exec edge로만 위상 정렬. 데이터-only 노드는 ExecutionOrderPanel에 미등장. | 유효. "계산 흐름" 분석 추가. |
| **F3** | 노드 역할 표시 | 인스펙터 헤더가 `name [cls]`만. T3D에는 `ResolvedFunctionName`(예: `Add::Execute(in A,in B,out Result)`), `TemplateNotation` 같은 유의미한 메타가 일부 노드에 있음 — 인터프리터는 보존만 하고 노출 안 함. | 유효. 역할 메타 추출·표시. |
| F4 | 직접 그래프 작성 | 스펙 §3.2 명시 비목표(round-trip 익스포트 포함). 편집 + 직렬화 + Undo 등 풀스택 작업 필요 — **본 배치 외**. | **별도 스펙으로 격리.** 본 문서 §8에서 deferred 처리. |
| **F5** | 브레드크럼 멀티그래프 | `MainWindow.setCentralWidget(view)` — 단일 캔버스, 탭/스택/히스토리 없음. 새 파일 열면 scene replace. | 유효. 그래프 스택 + 브레드크럼 도입. |
| **F6** | 서브그래프 미표시 | `RigVMGraphInterpreter.interpret`가 `doc.objects` top-level만 순회. CollapseNode/FunctionReferenceNode가 가진 `ContainedGraph` 자식(예: `CollapseNode_ContainedGraph`)의 내부 노드·링크 미추출. 같은 에셋 안에서도 노드 헤더만 보이고 본문 진입 불가. 크로스 에셋(FunctionLibrary 별도 파일)은 `external_refs`에 들어가지만 resolver 없음. | 유효. 두 단계 — (1) 같은 파일 내 `ContainedGraph` 재귀 파싱 → 모델 확장, (2) 크로스 파일 resolver. 본 배치는 (1)만. (2)는 모(母) 스펙 §3.3 seam의 "에셋 단위 통합" — 별도 작업. |
| **F7** | "연결된 핀만" 비정상 | `items.NodeItem._collect_rows`: top-level pin path가 `connected_paths`에 없으면 행 제외. 하지만 링크가 sub-pin(`Node.Pin.Sub`) 으로 들어오는 경우 top-level path `Node.Pin`은 set에 없어 부모 핀이 통째로 사라짐. `_connected_paths_by_node`가 `link.{source,target}_path`만 모음 — sub-pin path가 부모로 승급되지 않음. | 유효. 버그. sub-pin 연결을 부모 pin 연결로 승급. |
| **F8** | 연결된 핀 2배 | `_collect_rows`는 부모 pin과 sub-pin을 별도 행으로 모두 추가(`rows.append`가 부모에서도, 자식에서도 발생). "깊이 펼침" + "연결된 핀만" 동시 켰을 때 연결된 한 핀이 부모/자식 두 줄로 표시 → 사용자가 "2배"로 인식. 또한 `pin_anchor`가 sub-pin 행이 있으면 거기 앵커링 — 시각적으로 두 점 모두 후보가 됨(실제 그어지는 link는 한 개). | 유효. UX 버그. sub-pin 행이 보이면 부모 행은 라벨만 두고 dot/anchor 제거. |
| **F9** | 깊이 펼침 단위 지정 | `ViewState.expand_subpins`는 전역 boolean. 모든 노드의 모든 핀이 동시에 펼쳐짐 — 대형 노드는 화면 폭발. | 유효. per-(node, pin-path) 펼침 상태. |

---

## 3. 지도 원칙 — 노드 보존 불변식

**최상위 불변식 (PRESERVE-ALL):** 모델 → 시각화 어느 단계에서도 그래프 모델의 노드는 **드롭하지 않는다**. 필터/뷰모드/서브그래프 추출 — 어떤 작업이든 노드는 가시성(visible/hidden) 또는 컨테이너 소속 변경으로만 처리한다. 다음 모든 작업이 이 불변식을 지킨다:

- F1 별칭 미해결 시 → 원본 `name`을 fallback 표시(드롭 ✗)
- F2 데이터 흐름 분석이 일부 노드를 미포함해도 → 씬에는 여전히 보임(데이터 흐름 패널에서만 위치 결정에 사용)
- F6 ContainedGraph 추출 시 → 부모 그래프의 CollapseNode는 그대로 남고, 내부 그래프는 별도 컨테이너로 추가됨(부모 노드 삭제 ✗)
- F7 sub-pin 연결 승급 시 → 부모 pin은 "연결됨"으로 표시되지만 노드는 그대로
- F9 per-pin 펼침 → 펼치지 않은 노드도 정상 표시

테스트 슬롯: 모든 새 기능 통합 테스트에 "`len(scene._nodes) >= len(graph.nodes)`" 어서션 동반.

---

## 4. 범위

본 배치 안:

- **F7, F8** — 연결된 핀 옵션 버그 (정정)
- **F1** — 노드 별칭(alias) 인덱스 + 검색·표시 통합
- **F3** — 노드 역할 메타 수집·표시
- **F6 (내부 그래프 한정)** — CollapseNode/FunctionReferenceNode의 `ContainedGraph` 재귀 파싱 → `Node.subgraph` 슬롯
- **F5** — 그래프 스택 + 브레드크럼 UI (서브그래프 드릴다운 + 멀티 파일 열기)
- **F2** — 데이터 흐름 분석(`DataFlowResult`) + 새 패널 "계산 흐름"
- **F9** — per-(node, pin-path) 펼침 상태 (전역 토글은 "전체 펼침/접기" 단축으로 유지)

본 배치 밖(별도 스펙):

- **F4** — 그래프 작성·편집. 본 도구는 v1에서 *분석 뷰어* 정체성을 유지한다. 편집 도구로 전환하려면 (1) 모델 mutation API, (2) round-trip 직렬화(현 비목표), (3) Undo/Redo, (4) 검증 등 별도 설계가 필요. 본 문서에서는 *defer*만.
- **F6 크로스-에셋 부분** — 다른 파일에 있는 함수 라이브러리 진입은 모(母) 스펙 §3.3 "에셋 단위 통합" seam — 별도 작업.

---

## 5. 아키텍처 변경 요지

### 5.1 데이터 모델 확장

`core/base/graph_model.py`:

```python
@dataclass
class Node:
    name: str
    cls: str | None
    display_name: str | None = None           # NEW — F1 (UI 라벨 후보, 없으면 name)
    role_summary: str | None = None           # NEW — F3 (예: "Add(float,float)→float")
    role_category: str | None = None          # NEW — F3 (예: "Math")
    pins: list[Pin] = ...
    position: tuple[float, float] | None = None
    subgraph: "GraphModel | None" = None      # NEW — F6 (ContainedGraph)
    ...

@dataclass
class Pin:
    ...
    is_struct: bool = False                   # NEW — F8 (sub-pin 가진 컨테이너 식별)

@dataclass
class GraphModel:
    nodes: list[Node] = ...
    links: list[Link] = ...
    label: str | None = None                  # NEW — F5 ("RigVMModel" 등 — 브레드크럼 노드 라벨)
    parent_node: str | None = None            # NEW — F5 (서브그래프 진입점 노드 name)
    ...
```

서브그래프 라이프사이클: 자식 그래프는 부모 노드의 `Node.subgraph`에만 보관. 부모 그래프의 `nodes` 리스트엔 들어가지 않음(노드 보존 불변식 유지 — 부모 노드 그대로, 내부는 *컨테이너*로 추가).

### 5.2 별칭(alias) 해석 — F1

`plugins/rigvm/display_name.py` (신규) — RigVM 노드에서 사람 친화적 라벨 도출:

- `RigVMUnitNode`: `name`이 `RigUnit_` 접두 → 접두 제거 + CamelCase split (`RigUnit_BeginExecution` → "Begin Execution")
- `RigVMDispatchNode`: `ResolvedFunctionName`이 `Add::Execute(...)` 형태면 prefix(`Add`) 사용. 없으면 `TemplateNotation` 파싱
- `RigVMVariableNode`: `Variable` 핀 default value 사용 ("IKTarget" 등)
- `RigVMCollapseNode`/`RigVMFunctionReferenceNode`: `name` 그대로
- 모두 실패 시: `name` fallback (불변식)

검색/네비게이션 코드는 (1) `display_name` 매치, (2) `name` 매치, (3) `cls` 접미사 매치를 **OR**로 처리. **원본 name은 절대 버리지 않음** — 모든 내부 식별자·앵커는 여전히 `name` 기준(scene `_nodes` dict 등).

### 5.3 노드 역할 메타 — F3

`plugins/rigvm/role.py` (신규):

- `RigVMUnitNode.ScriptStruct`(있으면), `RigVMDispatchNode.ResolvedFunctionName`/`TemplateNotation` 파싱 → 시그니처 문자열 + 카테고리 추출.
- 인스펙터 헤더에 한 줄 추가: "역할: Math · Add(float,float)→float" (없으면 생략 — 불변식: 노드 표시 자체는 유지)

### 5.4 ContainedGraph 재귀 파싱 — F6

`plugins/rigvm/interpreter.py`:

- 노드 객체의 children 중 `cls == "/Script/RigVMDeveloper.RigVMGraph"`(또는 접미사 `RigVMGraph`)이고 이름이 `*_ContainedGraph` 인 것을 발견하면, **동일한 interpret 로직**(노드/링크/제네릭 분기)을 그 sub-object의 children에 재귀 적용 → `GraphModel` 산출 → 부모 노드의 `Node.subgraph`에 부착.
- `GraphModel.label`은 부모 노드의 `display_name` + "/" + sub-object name 으로 세팅.
- **부모 노드는 외부 그래프에 그대로 남는다(불변식).** 단지 진입점이 생긴 것.

테스트: 위 RigVMModel.t3d.txt의 `Physics.CollapseNode_ContainedGraph`가 child 그래프로 추출되어 그 안의 RigVMUnitNode·RigVMLink들이 모두 보존됨을 확인.

### 5.5 그래프 스택 + 브레드크럼 — F5

`core/app/graph_stack.py` (신규) — `list[GraphModel]` 스택 + 현재 인덱스 + 히스토리. MainWindow는 `QTabWidget` *또는* 단일 캔버스 + 상단 브레드크럼 바 둘 중 선택. **권장 — 단일 캔버스 + 브레드크럼 바**(파일 여러 개도 별도 *루트* 항목으로 스택에 쌓아 한 줄로 표현, 멀티탭의 복잡성 회피).

UX:

- 노드 더블클릭 시 `node.subgraph`가 있으면 push.
- 브레드크럼 바: `[RigVMModel] > [Physics] > [CollapseNode_ContainedGraph]` — 각 세그먼트 클릭 시 그 그래프로 pop.
- 파일 메뉴 "열기"는 새 루트로 push (현재 스택 옆에 + 표시).
- 뒤로/앞으로 단축키.

`AppController`는 파일 1개 → `GraphModel` 1개를 스택에 push 하도록 단순 변경(open_file은 그래프 스택을 비우지 않고 추가).

### 5.6 데이터 흐름 분석 — F2

`core/analysis/data_flow.py` (신규):

```python
@dataclass
class DataFlowResult:
    data_edges: list[tuple[str, str]]      # (src_node, dst_node) — 데이터 pin 링크
    inputs_of: dict[str, list[str]]
    outputs_of: dict[str, list[str]]
    sinks: list[str]                       # 출력 없는(최종 소비) 노드
    sources: list[str]                     # 입력 없는(상수/변수) 노드

def analyze_data_flow(graph: GraphModel) -> DataFlowResult: ...
```

규칙: link의 양 끝 pin이 **exec가 아니면** 데이터 엣지. exec/data 혼합 링크는 데이터 쪽 분류.

새 패널 `DataFlowPanel`:

- 하단 도크의 세 번째 탭 "계산 흐름". 기존 "수렴점"·"실행 순서"와 동급.
- sink부터 역방향 위상 정렬 → "이 값(sink)은 X·Y로부터 계산됨" 트리 표시. ExecutionStep과 비슷한 코드형 렌더.
- 노드 더블클릭 시 캔버스 네비게이션.

ExecutionOrderPanel은 **그대로 유지** — exec 흐름은 여전히 독립 의미를 가짐. 데이터 흐름은 별도 탭으로 *추가*.

### 5.7 per-pin 펼침 상태 — F9

`ViewState`:

```python
expanded_pin_paths: set[str] = set()         # 전체 경로(예: "Node.Pin")
def toggle_pin_expanded(self, full_path: str) -> None: ...
def is_pin_expanded(self, full_path: str) -> bool: ...
```

`items.NodeItem._collect_rows`: 전역 `show_subpins` 대신 `expanded_pin_paths` 참조 — 해당 pin path가 set에 있을 때만 자식 펼침. 노드 행에 작은 ▶/▼ 아이콘(또는 pin 라벨 클릭으로 토글) — items.py에 핀 클릭 시그널 추가.

기존 툴바 "깊이 펼침" 토글은 두 액션으로 분리: "전체 펼침", "전체 접기" — 한 번에 모든 pin path를 set에 채우거나 비움. (백워드 컴팩트한 사용성 유지.)

### 5.8 연결된 핀 버그 — F7, F8

`items.NodeItem._collect_rows` 재작성:

```python
def _collect_rows(node, connected_paths_subtree, connected_only, expanded_set):
    """connected_paths_subtree: 자신·자손 어디든 연결되어 있으면 True인 경로 set."""
    rows = []
    def walk(pin, path, depth):
        is_expanded = path in expanded_set
        has_visible_child = is_expanded and any(...)  # 자식 중 표시할 게 있는지
        if (not connected_only) or path in connected_paths_subtree:
            rows.append((pin, path, depth, has_visible_child))
        if is_expanded:
            for sp in pin.subpins:
                walk(sp, f"{path}.{sp.name}", depth + 1)
    ...
```

- `connected_paths_subtree`는 모든 sub-pin 연결을 부모로 **승급한 closure** — `_connected_paths_by_node`에서 각 link path의 prefix를 모두 추가(`Node.A.B.C` → `Node.A.B`, `Node.A`도 set에 포함).
- 행 렌더 시 `has_visible_child=True`(= 자식이 펼쳐져 있음)인 부모 행은 **dot/anchor 제거** — 라벨만 남김(F8 해결). 연결 표시는 자식 행이 함. `pin_anchor`는 자식 행이 있으면 자식 우선, 없으면 부모(현재 동작 유지).

이렇게 하면 — 부모 줄과 자식 줄이 동시에 보이지만 anchor는 하나, 시각적 dot 중복 없음, "2배" 현상 사라짐. "연결된 핀만"도 부모를 정상 포함(F7 해결).

---

## 6. 슬라이스(Slice) — 구현 순서

planner persona의 pipelined planning에 맞춰, 한 슬라이스가 다음 슬라이스를 차단하지 않도록 분리. router는 슬라이스 단위로 dispatch.

| 슬라이스 | 내용 | 의존 | 산출 plan |
|---|---|---|---|
| **A** | 핀 버그 정정 (F7, F8 + per-pin 펼침 F9 일부 — `_collect_rows` 재작성 한 번에) | 없음 | A: pin-rendering-fix |
| **B** | 노드 별칭 + 역할 메타 (F1, F3) — `display_name`, `role_summary`, `role_category` + 인스펙터 헤더 + 검색 | 없음 | B: node-display-meta |
| **C** | ContainedGraph 재귀 + 브레드크럼 (F6 내부, F5) — interpreter 재귀 + `Node.subgraph` + GraphStack + 브레드크럼 UI | A(인스펙터·뷰 안정 후), B(브레드크럼 라벨에 display_name 사용) | C: subgraph-breadcrumb |
| **D** | 데이터 흐름 분석 + 패널 (F2) — `analyze_data_flow` + `DataFlowPanel` 탭 | 없음(독립) | D: data-flow |

권장 발주 순서: **A → (B, D 동시) → C**. A가 가장 작고 명확한 버그 → 첫 dispatch. B와 D는 독립이라 병렬 가능. C는 마지막(B의 `display_name`이 브레드크럼 라벨에 쓰임).

**F4(편집)는 별도 스펙으로 격리** — 본 배치 어떤 슬라이스에도 포함되지 않음.

---

## 7. 위험 / 미해결 질문

### 7.1 노드 보존 불변식의 회귀 위험

서브그래프 추출 시 부모 그래프의 노드 리스트에서 자식 노드를 *옮기는* 실수가 가능. 자식 노드는 **새 GraphModel에 추가**하고 부모는 건드리지 않는다 — 인터프리터에서 child object 순회 시 outer scope의 `g.nodes`에 append 하지 않도록 sub-graph용 별도 local GraphModel 인스턴스를 두는 방식.

### 7.2 데이터 흐름의 "출력 없음" 노드 처리

데이터 흐름 분석 결과 sink가 없는 노드(완전 고립된 상수 등) 처리 — DataFlowResult 트리에 별도 그룹으로 표시. 누락 ✗ (불변식).

### 7.3 별칭 모호성

`display_name`은 사람-친화적 라벨일 뿐 식별자가 아님 — 같은 display_name을 가진 노드가 여러 개일 수 있음(예: 노드 두 개 모두 "Add"). 검색 결과가 여러 노드를 반환할 수 있으며, 모두 표시. 모든 내부 anchor·dict 키는 여전히 `name` 기준.

### 7.4 ContainedGraph가 가진 추가 외부 ref

서브그래프의 link가 부모 그래프 핀을 가리킬 수 있음 — 인터페이스 핀(Entry/Return). 이 경우 link의 한쪽 노드가 child graph에, 다른 쪽이 parent graph에 있음. 본 배치는 **child graph 내부 link만** 포함하고, child↔parent 경계 link는 `external_refs`처럼 별도 슬롯에 보관(렌더는 child 그래프 안에서만 — 부모 진입 화살표는 별도 UI). 본격적 *그래프 간 통합 뷰*는 추후.

### 7.5 ExecutionOrderPanel 의미 재정의 안 함

F2 데이터 흐름을 추가하지만 ExecutionOrderPanel 자체는 변경 없음(여전히 exec-pin 흐름) — 두 패널이 *상호 보완* 관계임을 사용자 가이드에 명시(README 갱신 또는 패널 툴팁).

---

## 8. 비목표 / Defer

| 항목 | 처리 |
|---|---|
| F4 — 직접 그래프 작성/편집 | **별도 스펙 작성 대상.** 본 batch에서 deferred. 차후 모(母) 스펙 §3 범위 자체를 *분석 뷰어 + 편집 도구*로 확장하는 별도 의사결정 필요. |
| 크로스-에셋 함수 라이브러리 진입 (F6 후속) | 모 스펙 §3.3 "에셋 단위 통합" — 별도 작업. |
| 노드 type 별 아이콘 / 색 디자인 변경 | 본 batch 안 함. |
| ContainedGraph child↔parent 경계 link 통합 뷰 | §7.4 — 추후. |

---

## 9. 테스트 전략 요지

- **불변식 회귀 테스트(공통)**: 새 통합 테스트 헬퍼 `assert_no_node_dropped(graph, scene)` — `scene._nodes.keys() ⊇ graph.nodes` 검사. 슬라이스 A·C 통합 테스트에 필수.
- **A**: `_collect_rows` 단위 테스트 — sub-pin 연결만 있을 때 부모 행 포함 / 펼침 시 dot 1개 / "연결된 핀만" + 펼침 조합.
- **B**: `display_name` 결정 케이스(unit/dispatch/variable/collapse/unknown fallback) 단위 테스트, 인스펙터 헤더 통합 테스트.
- **C**: 위 샘플 파일에서 `Physics.CollapseNode_ContainedGraph`가 추출되어 자식 그래프 노드/링크가 모두 들어왔는지 / 부모 그래프 노드는 여전히 존재 / 브레드크럼 push·pop 시 캔버스 일관성.
- **D**: 데이터-only 노드만 있는 작은 합성 그래프에 대해 `analyze_data_flow`가 모든 노드 포함하는지(불변식), 순환 보호.

각 슬라이스 plan에 구체적 케이스 명세.

---

## 10. 사용자 결정 요청

silent 모드로 진행하나, 다음 두 항목은 사용자 명시 확인이 권장됨(다음 응답에서 한 줄 confirm/deny이면 충분):

1. **F5 브레드크럼 vs 탭** — 본 스펙은 *단일 캔버스 + 브레드크럼 바*를 권장. 멀티탭이 더 좋다면 즉답 가능.
2. **슬라이스 발주 순서** — A → (B, D 병렬) → C 권장. router가 받자마자 작업자 분배하므로, 다르게 원하면 지금 의견.

답이 없으면 위 권장대로 plan을 작성·dispatch.
