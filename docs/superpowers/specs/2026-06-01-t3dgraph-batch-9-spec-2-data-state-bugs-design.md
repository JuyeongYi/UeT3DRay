# t3dgraph batch ⑨ Spec 2 — 데이터·상태·버그 설계 문서

- **작성일**: 2026-06-01
- **상태**: brainstorming 산출물 — 사용자 리뷰 대기
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **트래커**: `2026-06-01-t3dgraph-batch-9-user-feedback-2-tracker.md` (§2 검증·§3 PRESERVE-ALL·§4 분할의 단일 출처)
- **자매 spec**: Spec 1 (시각·렌더링, μ/ν/ξ) — 완료 (`71208c2`)

---

## 1. 범위

본 문서가 다루는 사용자 피드백 5건:

| ID | 한 줄 요약 | 트래커 §2 결론 | 본 spec 우선순위 |
|---|---|---|---|
| **F20** | 서브네트워크 터무니없이 작음 | 인터프리터 결함 · 가설 다수 | 최상 |
| F17 | 배열 요소 역순 (**모든 배열**) | 잠정 유효 · 재현 후 위치 특정 | 상 |
| F14 | 연결된 핀만 → 포트 2배 (**모든 노드**, F8 회귀) | 잠정 유효 · 재현 후 위치 특정 | 상 |
| F11 | 상단 4버튼 탭별 상태 | 상태 모델 리팩터 | 중 |
| F16 | 멤버 변수 입력 분간 불가 | 가시화 누락 | 중 |

본 문서 밖 (Spec 1, 또는 deferred): F10·F12·F13·F15·F18·F19(Spec 1 완료), batch ② F4(편집), ν-A2/B/C(다음 라운드).

---

## 2. 디자인 원칙 — Diagnostic-Driven Bug Fixing

F14·F17·F20은 모두 **정적 분석으로 root cause 단정 불가** 상태. 사용자가 "전부 노드", "모든 배열"이라고 보편성을 확언했지만 코드 리딩만으론 어디서 결함이 생기는지 좁히지 못함.

본 spec은 두 단계 진행을 강제한다:

1. **진단·재현 인프라부터** — `tests/repro/` 디렉터리에 결함을 시각화하는 실패 테스트를 먼저 박는다. fix 슬라이스가 그 테스트를 통과시키도록 자른다. 가설 검증 회피.
2. **데이터 기반 fix** — F20은 `InterpreterDiagnostics` 데이터(어떤 클래스 몇 개가 누락됐는지)를 보고 fix 슬라이스 scope를 정한다.

이 원칙이 슬라이스 분할(§8)을 결정한다.

---

## 3. PRESERVE-ALL 불변식 (강화)

| ID | 조작 | 보존 |
|---|---|---|
| F20 | 누락된 노드 **복원** | ✅ (불변식 **강화** 방향) |
| F17 | 배열 subpin 순서만 변경 | ✅ (subpin 수 동일) |
| F14 | 시각 dot 표시 로직 수정 | ✅ (모델 무변경) |
| F11 | per-tab `ViewState` 분리 | ✅ (모델 무변경) |
| F16 | 변수 배지·인라인 표시 | ✅ (가시화만) |

테스트 슬롯:

- 전 슬라이스 통합 테스트에 `len(scene._nodes) >= len(graph.nodes)` 어서션 유지
- π 슬라이스에서 **새 어서션** 추가: `len(graph.nodes) + len(graph.diagnostics.objects_dropped) >= count_of_node_class_objects(doc)` (PRESERVE-ALL 정량 가드)

---

## 4. F20 — 서브네트워크 누락 (인터프리터 완전성)

### 4.1 디자인

`GraphModel`에 `diagnostics: InterpreterDiagnostics | None = None` 필드 추가. 인터프리터가 모든 객체에 대해 추출/누락 결정을 기록. fix 슬라이스가 데이터를 보고 NODE_CLASS_SUFFIXES 확장 / FunctionReferenceNode → AssetResolver 연결 / 깊은 ContainedGraph 재귀 강화 중 필요한 것만 적용.

### 4.2 자료구조

`src/t3dgraph/core/base/graph_model.py`:

```python
@dataclass
class DroppedObject:
    """인터프리터가 처리하지 못해 그래프에 들어가지 못한 객체."""
    name: str
    cls: str | None
    reason: str            # "unknown class" | "depth cap" | "graph at top" | "no resolver"
    parent_obj: str | None # 재귀 중 손실 시 부모 객체명. top-level이면 None.


@dataclass
class InterpreterDiagnostics:
    """인터프리터 한 사이클의 정량 진단."""
    objects_dropped: list[DroppedObject] = field(default_factory=list)
    extracted_per_class: dict[str, int] = field(default_factory=dict)   # cls suffix → count
    max_depth_seen: int = 0
    contained_graph_count: int = 0
    external_refs_unresolved: list[str] = field(default_factory=list)


@dataclass
class GraphModel:
    nodes: list[Node] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    variable_refs: list[VariableRef] = field(default_factory=list)
    external_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: InterpreterDiagnostics | None = None      # F20: 진단 데이터
    label: str | None = None
    parent_node: str | None = None
    boundary_refs: list[str] = field(default_factory=list)
    # 기존 메서드 그대로
```

### 4.3 인터프리터 변경 (π 슬라이스)

`RigVMGraphInterpreter.interpret`가 진단 객체를 항상 생성·반환. 깊은 재귀에서도 같은 객체를 누적 갱신:

```python
def interpret(self, doc: T3DDocument) -> GraphModel:
    diag = InterpreterDiagnostics()
    g = self._interpret_objects(doc.objects, label=None, parent_node=None, diagnostics=diag)
    g.diagnostics = diag
    return g

def _interpret_objects(self, objects, *, label, parent_node, depth=0, max_depth=64,
                       diagnostics: InterpreterDiagnostics) -> GraphModel:
    diagnostics.max_depth_seen = max(diagnostics.max_depth_seen, depth)
    if depth >= max_depth:
        # 누락된 객체들 기록
        for obj in objects:
            diagnostics.objects_dropped.append(DroppedObject(
                name=obj.name or "?", cls=obj.cls,
                reason="depth cap", parent_obj=parent_node))
        # ... 기존 로직
    ...
    # is_node_class/is_link_class/is_graph_class 분기에서:
    elif obj.cls is not None:    # is_node_class 등 모두 False
        diagnostics.objects_dropped.append(DroppedObject(
            name=obj.name or "?", cls=obj.cls,
            reason="unknown class", parent_obj=parent_node))
        self._add_generic(obj, g)   # 기존 동작 유지
    ...
    # 노드 추출 성공 시
    suffix = (node.cls or "").rsplit(".", 1)[-1]
    diagnostics.extracted_per_class[suffix] = diagnostics.extracted_per_class.get(suffix, 0) + 1
    # ContainedGraph 추출 시
    diagnostics.contained_graph_count += len(graph_children)
```

### 4.4 ρ 슬라이스 — F20 fix (π 데이터 기반)

π 머지 후 Orion 샘플로 `test_f20_node_preservation.py`를 통과시킬 때 보이는 데이터에 따라 결정:

- `extracted_per_class`에 `RigVMAggregateNode`/`RigVMBranchNode` 등 신규 클래스 0개 → `NODE_CLASS_SUFFIXES` 확장
- `objects_dropped`의 `reason="unknown class"` 누적 → 동일
- `external_refs_unresolved` 다수 + `RigVMFunctionReferenceNode` 미추출 → `AssetResolver` 연결 (κ-A2 동시 해소)
- `max_depth_seen` >= 16 + 추가 dropped → 재귀 강화 또는 cap 조정

ρ 슬라이스 plan 작성은 π 머지 데이터 확인 직후 별도 사이클. 본 spec은 ρ의 정확한 scope를 deferred.

### 4.5 테스트 `tests/repro/test_f20_node_preservation.py`

**노드 후보 정의**: T3D 객체 중 클래스 경로가 `/Script/RigVM*`로 시작하고 suffix가 `RigVMPin`/`RigVMLink`/`RigVMGraph`가 **아닌** 객체. 중첩 객체(`ContainedGraph` 내부 등) 모두 포함.

헬퍼 (테스트 파일 안에 정의):

```python
def count_node_candidates(objects) -> int:
    """T3D 객체 트리(중첩 포함)에서 노드 후보 수."""
    excluded_suffixes = ("RigVMPin", "RigVMLink", "RigVMGraph")
    n = 0
    for o in objects:
        cls = o.cls or ""
        if cls.startswith("/Script/RigVM") and not any(
                cls.endswith(s) for s in excluded_suffixes):
            n += 1
        n += count_node_candidates(o.children)
    return n


def count_extracted_nodes(g) -> int:
    """GraphModel 트리(subgraph·extra_subgraphs 포함)에서 추출된 노드 수."""
    total = len(g.nodes)
    for node in g.nodes:
        if node.subgraph is not None:
            total += count_extracted_nodes(node.subgraph)
        for extra in node.extra_subgraphs:
            total += count_extracted_nodes(extra)
    return total
```

핵심 어서션:

```python
def test_orion_sample_node_preservation():
    """모든 노드 후보가 추출 또는 dropped 목록에 들어간다 — 잠적 0."""
    doc = parse_t3d_file(ORION_SAMPLE_PATH)
    graph = RigVMGraphInterpreter().interpret(doc)
    expected = count_node_candidates(doc.objects)
    extracted = count_extracted_nodes(graph)
    dropped = len(graph.diagnostics.objects_dropped)
    assert extracted + dropped >= expected, (
        f"노드 잠적: expected={expected}, extracted={extracted}, dropped={dropped}, "
        f"dropped_classes={ {d.cls for d in graph.diagnostics.objects_dropped} }")
```

추가:

```python
def test_extracted_per_class_snapshot():
    """추출 클래스 분포 스냅숏 — 회귀 알람용."""
    doc = parse_t3d_file(ORION_SAMPLE_PATH)
    graph = RigVMGraphInterpreter().interpret(doc)
    # 최소한 핵심 클래스는 0이 아니어야 함
    for cls in ("RigVMUnitNode", "RigVMDispatchNode"):
        assert graph.diagnostics.extracted_per_class.get(cls, 0) > 0
    # ρ 머지 시 신규 클래스(예: RigVMAggregateNode) > 0 어서션 추가


@pytest.mark.xfail(reason="π에서는 unknown class drop 허용 — ρ 머지 시 통과 기대")
def test_no_unknown_classes_after_fix():
    """ρ 머지 충족 조건 — unknown class dropped 0."""
    doc = parse_t3d_file(ORION_SAMPLE_PATH)
    graph = RigVMGraphInterpreter().interpret(doc)
    unknown = [d for d in graph.diagnostics.objects_dropped
               if d.reason == "unknown class"]
    assert unknown == [], (
        f"미알 클래스 {len(unknown)}개 — NODE_CLASS_SUFFIXES 확장 필요: "
        f"{ {d.cls for d in unknown} }")
```

xfail은 ρ 머지 시 `@pytest.mark.xfail` 제거 → 정상 어서션으로 승급.

`ORION_SAMPLE_PATH`는 `tests/repro/conftest.py`에서 환경변수 또는 고정 경로로 정의 (Orion 샘플은 `Orion_WorkStation_Rig_Analysis/`에 있음).

---

## 5. F17 — 배열 요소 역순

### 5.1 디자인

`_array_body`·`_struct_body`·`_build_pin` 정적 분석상 입력 순서 보존 — 그러나 사용자가 "모든 배열" 보편 관측. 동적 재현 후 핀포인트 fix.

### 5.2 σ 슬라이스 진입 전 재현 (π에서)

`tests/repro/test_f17_array_order.py`:

```python
def test_array_subpin_order_matches_source(tmp_path):
    """배열 핀의 subpin 순서가 T3D 원본 객체 순서와 일치."""
    src = '''Begin Object Name="N1" Class=...
        Begin Object Name="Items" Class=...RigVMPin
            Begin Object Name="0" Class=...RigVMPin
            End Object
            Begin Object Name="1" Class=...RigVMPin
            End Object
            Begin Object Name="2" Class=...RigVMPin
            End Object
        End Object
    End Object'''
    doc = parse_t3d_text(src)
    graph = RigVMGraphInterpreter().interpret(doc)
    items_pin = graph.nodes[0].pins[0]
    names = [sp.name for sp in items_pin.subpins]
    assert names == ["0", "1", "2"]   # 원본 순서
```

### 5.3 σ 슬라이스 fix scope

재현 테스트 실패 위치에 따라:

- `_array_body`/`_struct_body` 내부에 inadvertent reverse → 파서 수정
- `_build_pin` 또는 obj.children 정렬 어딘가 reverse → 추출 수정
- 시각 레이어(items, inspector)에서 역순 출력 → 렌더 수정

각 경우 fix는 ~5줄. 다만 어디서 발생하는지가 데이터로 결정 — π 머지 후 σ 슬라이스 진입 시 확정.

---

## 6. F14 — 연결된 핀만 포트 2배 (F8 회귀)

### 6.1 디자인

`collect_pin_rows` 정적 분석상 `has_dot` 승급 처리됨 — 그러나 사용자가 "모든 노드" 보편 관측. 동적 재현 후 핀포인트 fix.

### 6.2 σ 슬라이스 진입 전 재현 (π에서)

`tests/repro/test_f14_connected_only_dot_count.py`:

```python
def test_connected_only_toggle_dot_count_stable(qtbot):
    """connected_only 토글 후 dot 개수가 (감소 또는 동일)이어야 함 — 증가는 회귀."""
    graph = load_orion_sample()
    scene = GraphScene()
    vs = ViewState()
    # OFF
    scene.populate(graph, view_state=vs, pin_colors=...)
    dots_off = sum(count_dots(n) for n in scene._nodes.values())
    # ON
    vs.connected_pins_only = True
    scene.populate(graph, view_state=vs, pin_colors=...)
    dots_on = sum(count_dots(n) for n in scene._nodes.values())
    assert dots_on <= dots_off, (
        f"connected_only 토글 후 dot 증가 (F14 회귀): off={dots_off}, on={dots_on}")
```

### 6.3 σ 슬라이스 fix scope

재현 통해 어디서 dot이 두 번 추가되는지 식별. 가능성:

- `_connected_paths_by_node`가 부모·자식 path 모두 add → expanded 미설정인데 양쪽 행 생성 (현 코드상 expand에 따라 has_dot 조정되므로 확인 필요)
- `NodeItem.__init__`에서 dot 추가 코드 경로 중 disclosure indicator(μ) 또는 array outline(μ) 변형이 의도치 않게 두 번 그림
- pin_anchor fallback이 sub-pin 링크를 부모에 매핑하면서 부모 row도 dot 표시되어 중복 노출

핀포인트 후 fix는 ~5-10줄.

---

## 7. F11 — Per-tab ViewState

### 7.1 디자인

`MainWindow.view_state = ViewState()` 1개 → `MainWindow._view_states: dict[graph_key, ViewState]`. 현재 활성 탭의 ViewState를 `current_view_state()` getter로 제공. 탭 전환·서브그래프 진입 시 자동 스위치. 토글 액션은 현재 탭만 영향.

### 7.2 graph_key 통일

ν에서 도입된 `_current_graph_key()`(루트 토큰 + parent_node 조합) 그대로 재사용. ν-B3(escape 누락) 백로그 항목을 본 슬라이스에서 동시 해소 — 튜플 키 또는 `urllib.parse.quote` 적용.

`LayoutOverrides`와 `_view_states` 모두 동일 graph_key로 인덱싱.

### 7.3 main_window.py 변경

```python
self._view_states: dict[str, ViewState] = {}

def current_view_state(self) -> ViewState:
    key = self._current_graph_key()
    if key not in self._view_states:
        self._view_states[key] = ViewState()
    return self._view_states[key]

# 기존 self.view_state 직접 접근을 self.current_view_state()로 치환
```

토글 액션(`_on_view_mode`), 펼침/접기 액션, 노드 컨텍스트 메뉴 액션 모두 `current_view_state()`로 작업.

### 7.4 탭 닫기 시 정리

`_on_tab_close`에서 닫힌 root의 graph_key prefix 매칭으로 `_view_states` 항목 정리(`LayoutOverrides.clear_by_prefix`와 같은 패턴).

### 7.5 회귀 가드

기존 `view_state` 단일 가정 통합 테스트(toolbar 토글 결과 적용 등) → 활성 탭에서만 적용되는지 확인하는 어서션으로 갱신.

새 통합 테스트: `tests/app/test_per_tab_view_state.py`:

- 두 탭 열고 탭1에서 `connected_only` 토글 → 탭2의 ViewState 영향 없음
- 탭1 → 탭2 전환 시 toolbar 액션 체크 상태가 탭2의 ViewState 반영
- 탭 닫기 후 `_view_states` 항목 제거

---

## 8. F16 — 변수 가시화

### 8.1 디자인

`RigVMVariableNode` 식별 강화 (배지) + 그 노드의 출력 핀을 소비하는 핀에 인라인 var 표시.

세 부분:

**(a) 변수 노드 배지**

- `NodeItem` 헤더 좌측에 `var` 배지(작은 사각형 + "var" 텍스트 + variable 색)
- 또는 노드 헤더 배경색 다르게 (variable 팔레트 색)
- 사용자 식별 즉각

**(b) 소비 핀 인라인 표시**

- 인스펙터 "기본값" 컬럼에 `← var: VariableName` 표시 (해당 핀이 var output에서 링크된 경우)
- 노드 캔버스 핀 라벨에도 작은 var 아이콘 prefix
- 데이터 출처: `GraphModel.variable_refs`(이미 존재) + `links`에서 source가 variable node인지 확인

**(c) 팔레트 확장**

- μ에서 만든 `pin_colors.toml`에 `variable = "#9966FF"` (보라 계열) 추가
- bucket에 변수 노드 핀 타입 매핑 (RigVM variable get의 출력 핀이 `Value`라 cpp_type이 임의)
- 또는 별도 palette key가 아니라 node-level color override (간단성)

### 8.2 인터프리터 변경 — variable consumers

`RigVMGraphInterpreter` (또는 후처리)에서 각 노드 pin에 대해 "variable 출처" 메타 부여:

```python
@dataclass
class Pin:
    ...
    variable_source: str | None = None    # 이 핀이 var X의 출력에서 링크되면 X 이름
```

GraphModel `variable_refs` + `links` 조합으로 사후 계산. **호출 위치**: `RigVMGraphInterpreter.interpret()` 마지막에 `_annotate_variable_consumers(g)` 호출 (extraction 완료 후, 반환 직전):

```python
def interpret(self, doc):
    diag = InterpreterDiagnostics()
    g = self._interpret_objects(doc.objects, label=None, parent_node=None, diagnostics=diag)
    g.diagnostics = diag
    self._annotate_variable_consumers(g)        # F16
    return g

def _annotate_variable_consumers(self, g: GraphModel) -> None:
    """variable_refs + links → 각 소비 핀에 variable_source 부여."""
    var_outputs: dict[str, str] = {}   # "VariableNode.Value" → variable_name
    for ref in g.variable_refs:
        var_outputs[f"{ref.node_name}.Value"] = ref.variable_name
    for link in g.links:
        var_name = var_outputs.get(link.source_path)
        if var_name is None:
            continue
        target_pin = self._locate_pin(g, link.target_path)
        if target_pin is not None:
            target_pin.variable_source = var_name
    # 재귀: subgraph 안에서도 variable_refs가 있을 수 있음
    for node in g.nodes:
        if node.subgraph is not None:
            self._annotate_variable_consumers(node.subgraph)
        for extra in node.extra_subgraphs:
            self._annotate_variable_consumers(extra)

def _locate_pin(self, g: GraphModel, path: str) -> Pin | None:
    """'NodeName.PinName[.SubPin...]' → Pin 객체."""
    parts = path.split(".")
    node = g.node_by_name(parts[0])
    if node is None:
        return None
    cur_pins = node.pins
    for name in parts[1:]:
        pin = next((p for p in cur_pins if p.name == name), None)
        if pin is None:
            return None
        cur_pins = pin.subpins
        last = pin
    return last
```

`variable_source`가 직접 핀(top-level)에 부여되든 sub-pin에 부여되든 모두 지원 (변수가 struct의 한 필드로 소비될 수도 있음).

### 8.3 시각 적용

`NodeItem`:

- `if node.cls suffix == "RigVMVariableNode"`: 헤더 우측에 작은 `var` 배지 그리기
- 핀 행에 `pin.variable_source`가 있으면 라벨 앞에 `↩` 또는 `📥` 같은 prefix 추가 (단, 이모지 회피 — 단순 `var:` 접두)

`InspectorPanel`:

- `_add_pin`에서 핀에 `variable_source`가 있으면 "기본값" 셀 텍스트를 `pin.default_value or ""` → `← var: {variable_source}`로 변환 (또는 별도 컬럼 vs 결합 — 결정 §8.5)

### 8.4 팔레트 확장

`src/t3dgraph/core/app/resources/pin_colors.toml`에 추가:

```toml
[palette]
# ... 기존 ...
variable = "#9966FF"     # var get 노드 헤더·var-fed 핀 시각용
```

`pin_colors.py`의 `resolve()`는 cpp_type 기반이므로 var 표시는 별도 경로(NodeItem이 node.cls/pin.variable_source 검사). pin_colors는 var 표시에 직접 관여 안 함 — 다만 팔레트 파일을 사용자가 색 일관성 유지 위해 한 곳에서 보도록 entries 추가.

### 8.5 인스펙터 결정

기본값 컬럼에 합쳐 표시. 별도 컬럼 만들면 인스펙터 폭 회귀 (ξ 결과 침해). 합치되 prefix `← var: Name` 사용 — 잘림 시 ξ-A1 ToolTipRole 자동 적용(이미 구현).

### 8.6 테스트 `tests/app/test_variable_visualization.py`

- 변수 노드 inspector 헤더에 var 마커 노출
- 변수 소비 핀의 "기본값" 셀이 `← var: VarName` 시작
- 변수 소비 없는 핀은 기존 기본값 그대로
- `Pin.variable_source` 메타 추출 정확도 (annotate_variable_consumers)
- 변수 노드 헤더 배지 렌더링 (NodeItem)

---

## 9. 슬라이스 분할

### 9.1 슬라이스 표

| 슬라이스 | 대상 | 변경 파일 | 의존 | 진입 |
|---|---|---|---|---|
| **π** Diagnostic & Repro | F20 진단 인프라 + F14·F17·F20 repro 테스트 | base/graph_model.py, plugins/rigvm/interpreter.py, tests/repro/* (신규) | 없음 | 1차 (병렬) |
| **ρ** F20 Fix | π 데이터 기반 — NODE_CLASS_SUFFIXES 확장 / FunctionReferenceNode → AssetResolver 연결 / 재귀 강화 | rigvm/types.py, rigvm/interpreter.py, core/app/main_window.py (resolver wire) | **π 머지 후** | 2차 |
| **σ** F14·F17 Fix | π 재현 테스트 통과 — 핀포인트 fix | scene.py 또는 items.py 또는 t3d/values.py (위치 미정) | **π 머지 후** | 2차 |
| **τ** F11 Per-tab ViewState | view_state per-tab 분리 + ν-B3 graph_key escape | core/app/main_window.py, view_state.py | 없음 | 1차 (병렬) |
| **φ** F16 Variable Display | 변수 배지 + 소비 핀 인라인 + 팔레트 entry | plugins/rigvm/interpreter.py(annotate), core/base/graph_model.py(Pin.variable_source), core/app/items.py, inspector_panel.py, resources/pin_colors.toml | 없음 | 1차 (병렬) |

### 9.2 진입 순서

- **1차 병렬**: π, τ, φ (서로 다른 파일군)
- **2차 병렬** (π 머지 후): ρ, σ

ρ과 σ는 서로 무관(ρ은 인터프리터, σ은 시각·파서). π 머지 후 동시 디스패치 가능.

### 9.3 Spec 1과의 정합

- τ의 `graph_key` 모델은 ν `_current_graph_key()` 그대로. ν-B3 백로그 동시 해소.
- φ의 팔레트 entry는 μ TOML 확장. 기존 `pin_colors.toml` 사용자 파일이 있으면 reset 또는 사용자 수동 추가 안내(메뉴 "팔레트 리셋"으로 해결).
- π의 `InterpreterDiagnostics` 자료구조는 향후 분석 계열(flow/order/data_flow) 결과 attach 패턴의 선례.

### 9.4 회귀 가드

기존 통합 테스트:

- batch ② F1~F9 (브레드크럼·서브그래프·연결된 핀·fan-in)
- batch ⑥ 단축키
- batch ⑦ θ-1/θ-2 (compute trace, data flow diff)
- batch ⑧ ι/κ/λ (round-trip, asset resolver, minimap)
- batch ⑨ Spec 1 (μ pin colors·F12 disclosure, ν bezier·drag·context menu, ξ inspector layout)

본 spec 슬라이스가 이들을 깨지 않아야 진행.

### 9.5 의존성

- 신규 외부 의존성 0
- `InterpreterDiagnostics`·`DroppedObject`는 dataclass — Python 표준
- Pin에 `variable_source: str | None = None` 추가는 dataclass 기본값 — 호출부 무영향

### 9.6 Out-of-scope (Spec 2 밖)

- 사이드카 layout 영속화 (ν-A2) — 핫픽스 슬라이스 후보
- 자동 레이아웃 (ν-C3)
- 멀티 선택 드래그·Undo/Redo (ν-C1·C2)
- batch ② F4 그래프 편집
- F20 fix의 미관측 카테고리 — π 데이터 외 새로 발견 시 다음 라운드

---

## 10. 다음 단계

1. 사용자 리뷰 (본 문서) — 변경 요청 시 해당 절 수정
2. 승인 후 `writing-plans` 스킬로 슬라이스 π/ρ/σ/τ/φ 구현 플랜 작성. ρ·σ plan은 π 머지 데이터 확정 후 추가 cycle.
3. 슬라이스 디스패치 순서:
   - 1차: π, τ, φ → sp-router → 각 implementer
   - π improver 사이클 + 데이터 캡처
   - 2차: ρ, σ plan 작성 → 디스패치
4. 본 batch ⑨ 마감 (Spec 1 + Spec 2) 후 batch ⑩ 후보 — μ-A1(팔레트 무음), ν-A2(영속화), ν-B1(walk 중복), 백로그 누적 잔여
