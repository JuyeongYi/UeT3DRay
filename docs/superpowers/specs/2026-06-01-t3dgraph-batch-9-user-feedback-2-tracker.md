# t3dgraph 사용자 피드백 정리 batch ⑨ — 트래커

- **작성일**: 2026-06-01
- **상태**: brainstorming 진행 중 — Spec 1 active, Spec 2 deferred
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **위치**: batch ⑧(2026-05-22 heavy features) 다음. 두 번째 user-feedback 라운드(첫 라운드는 batch ②, F1~F9).
- **자식 design 문서**:
  - Spec 1 (시각·렌더링) — `2026-06-01-t3dgraph-batch-9-spec-1-vis-rendering-design.md` (이번 세션 산출)
  - Spec 2 (데이터·상태·버그) — `<date>-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` (별도 세션 예정)

---

## 1. 트리거

2026-06-01 사용자 피드백 11건. RigVM(`Orion_WorkStation_Rig_Analysis` 샘플) 기준.

원문(요지):

1. (F10) 타입이 다른 인풋끼리 색이 달랐으면 함.
2. (F11) 최상단 4개 버튼(연결된 핀만, fan-in…) 등이 각각의 브레드크럼 탭으로 이동했으면 함.
3. (F12) 구조체 접기 기능 등이 확인되지 않음.
4. (F13) 연결 선이 직선 방식이라 불편함.
5. (F14) 연결된 핀만 보기 선택 시 입출력 포트가 2배로 증가하는 현상이 여전함 (F8 회귀).
6. (F15) 속성 인스펙터 창이 노드 선택 시 지나치게 옆으로 크게 늘어남.
7. (F16) 멤버 변수로부터 입력받는 경우 분간이 되지 않음.
8. (F17) 배열 요소가 역순으로 정렬됨.
9. (F18) 노드의 기본적인 이동이 가능했으면 함. 겹쳐서 보이는 경우 확인 어려움.
10. (F19) 노드 전체가 아니라 각각도 펼치기/접기가 가능했으면 한다.
11. (F20) 서브네트워크(그래프 내 함수) 등이 제대로 생성되지 않는 것 같음 — 실제 노드 내용에 비해 생성된 그래프가 터무니없이 작다.

추가 사용자 확언:

- F14는 **모든 노드**에서 발생.
- F17은 **모든 배열**에서 발생 (구조체 입력·float 입력·sequence 실행 핀 무관).

---

## 2. 검증 결과 — 현 코드 상태

| ID | 피드백 | 현 코드 | 결론 |
|---|---|---|---|
| **F10** | 타입별 핀 색 구분 | `items.py:113-114` — 모든 핀 dot이 `QColor(200,200,120)` 단색. `pin.cpp_type` → 색 매핑 없음. | 유효 · 신규 (타입→색 팔레트). |
| **F11** | 상단 4버튼이 탭별 상태 | `MainWindow.view_state = ViewState()` 1개. `graph_stack` root별 ViewState 없음. 탭이 같은 connected_only / fan_in / 펼침 set 공유. | 유효 · 상태 모델 리팩터. |
| **F12** | 구조체 접기 동작 발견 불가 | 토글 기능 존재(`mouseDoubleClickEvent` → `toggle_pin_expanded`). 다만 구조체 핀임을 알리는 시각 단서(▶/▼) 없음, `pin.subpins` 비어있는지 표시도 없음. | 유효 · UX 발견 가능성 0 (disclosure indicator 누락). |
| **F13** | 연결선 직선 → 곡선 | `LinkItem` extends `QGraphicsLineItem` — 직선 전용. | 유효 · 신규 (`QGraphicsPathItem` + 베지어). |
| **F14** | F8 회귀 — 연결된 핀만 → 포트 2배 (**모든 노드**) | `collect_pin_rows`는 children_added 시 부모 has_dot=False 처리됨(`items.py:54-57`). 정적 분석상 회귀 안 보이나 사용자 보편 관측. | 잠정 유효 · 재현 케이스로 위치 특정 필요. **Spec 2 우선축.** |
| **F15** | 인스펙터 노드 선택 시 폭 폭주 | `InspectorPanel`의 `QTreeWidget` 5컬럼, 자동 fit 옵션 없음. `dock_right` 최대폭/`sizePolicy` 없음. | 유효 · 레이아웃 결함 (컬럼 폭 + dock 폭 + 스크롤 정책). |
| **F16** | 멤버 변수 입력 분간 불가 | `RigVMVariableNode` → `VariableRef` 추출은 됨(`interpreter.py:148`). 인스펙터/씬에 "이 핀은 var X 읽음" 표시 없음. | 유효 · 신규 (variable 배지 + 소비 핀 인라인 표시). |
| **F17** | 배열 요소 역순 (**모든 배열**) | `_build_pin`이 `obj.children` 순서 그대로. T3D parser values.py 또는 `RigVMArrayNode` raw 처리 어딘가에서 reverse. | 잠정 유효 · 재현 후 위치 특정. **Spec 2.** |
| **F18** | 노드 드래그 이동 불가 | `NodeItem.setFlag(ItemIsSelectable, True)`만. `ItemIsMovable` 없음. 위치는 T3D `Position` 또는 fallback grid. | 유효 · 신규 (드래그 + 이동 상태 저장 여부 결정 필요). |
| **F19** | 노드별 펼치기/접기 (현재 전역만) | toolbar `전체 펼침/접기`만 → 전 노드 일괄. 노드 우클릭/단축 없음. 헤더 더블클릭은 subgraph 진입 점유. | 유효 · 신규 (노드 컨텍스트 메뉴 또는 헤더 단축). |
| **F20** | 서브네트워크가 터무니없이 작음 | batch ② F6에서 같은 파일 내 `ContainedGraph` 추출 들어감(`interpreter.py:124-138`). κ 슬라이스에서 `AssetResolver` 들어감. **improver κ-A2 백로그**: "`_resolver`가 등록만 되고 활용 안 됨" — 절반-기능 상태. | 유효 · 인터프리터 결함 (가설 다수, 재현 필요). **Spec 2 우선순위 최상.** |

가설 — F20 재현 시점 우선 검토 항목:
1. `RigVMFunctionReferenceNode`는 같은 파일에 `ContainedGraph` 없이 외부 라이브러리 참조만 — resolver 미연결 시 빈 그래프.
2. `is_node_class` / `is_graph_class` 필터가 신규 RigVM 클래스(`RigVMAggregateNode`, `RigVMRerouteNode` 등)를 누락 → `_add_generic` 또는 children 손실.
3. 깊은 중첩에서 `_interpret_objects`가 graph_class 자식의 children만 펴고 더 깊은 ContainedGraph를 재귀 못 함.
4. `max_depth=64` 절단 — 가능성 낮음(샘플 규모 고려).

---

## 3. 지도 원칙 — PRESERVE-ALL 불변식 (재확인)

batch ② §3과 동일. **모델 → 시각화 어느 단계에서도 그래프 모델의 노드는 드롭하지 않는다**. 본 batch에서 영향 매트릭스:

| ID | 불변식 영향 | 비고 |
|---|---|---|
| F10 | 색만 변경 — 노드/링크 보존 | ✅ |
| F11 | 뷰 상태 분리 — 모델 무변경 | ✅ |
| F12 | disclosure 표시만 — 토글 기능은 기존 | ✅ |
| F13 | 링크 렌더만 — Link 객체 보존 | ✅ |
| F14 | 시각 수정 — 모델 보존 | ✅ (행 표시 로직만) |
| F15 | dock 레이아웃 — 노드 무영향 | ✅ |
| F16 | 핀 메타 가시화 — 노드/링크 보존 | ✅ |
| F17 | 정렬 순서 수정 — 데이터 보존 | ✅ (subpins 수 동일) |
| F18 | 위치 변경 — 노드 id/존재 보존 | ✅ |
| F19 | 펼침 범위 — 모델 무변경 | ✅ |
| F20 | **노드 추가 방향** — PRESERVE-ALL 강화 (현 누락 노드 복원) | ✅ (보존 강화) |

테스트 슬롯: 모든 새 기능 통합 테스트에 `len(scene._nodes) >= len(graph.nodes)` 어서션 + F20 구현 시 `len(graph.nodes) >= len(doc.objects 중 노드)` 어서션 동반.

---

## 4. 범위 분할

### Spec 1 — 시각·렌더링 (이번 세션)

대상: **F10, F12, F13, F15, F18, F19** (6건)

성격: GUI 렌더 레이어 한정. 모델·인터프리터 무변경. 통합 테스트 부담 적음.

### Spec 2 — 데이터·상태·버그 (별도 세션)

대상: **F11, F16, F14, F17, F20** (5건). **우선순위: F20 > F14·F17 > F11 > F16**.

성격: 인터프리터/모델/상태 모델 변경. 회귀 위험 큼. 재현 케이스 작성이 슬라이스 진입 조건.

진입 전 준비:
- Orion 샘플로 F14·F17·F20 재현 스크립트 작성 (`tests/repro/`)
- F20에 대해 `len(doc.objects) vs len(graph.nodes)` 어서션 + ContainedGraph 깊이 통계
- `is_node_class` / `is_graph_class` 매처를 RigVM 신규 클래스에 대해 점검

### 본 batch 밖

- batch ② F4 (그래프 작성·편집) — 분석 뷰어 정체성 유지 정책 변경 없음. 별도 시점에 재논의.
- improver 백로그(ζ~λ B 시리즈) — 본 batch와 무관, 정리 슬라이스로 별도 처리.

---

## 5. 진행 상태

| 항목 | 상태 |
|---|---|
| 트래커 작성 | ✅ (본 문서) |
| Spec 1 brainstorming | ✅ 완료 |
| Spec 1 design doc | ✅ `2026-06-01-t3dgraph-batch-9-spec-1-vis-rendering-design.md` (63c7024) |
| Spec 1 plan (slice 분할) | ✅ μ/ν/ξ 3개 plan 문서 (ddaf458) |
| Spec 1 슬라이스 μ (F10+F12) | ✅ 머지 `ddfa8ea` · improver findings 9건(μ-A1~3, μ-B1~3, FEAT-32~34) |
| Spec 1 슬라이스 ξ (F15) | ✅ 머지 `806653a` · improver findings 6건(ξ-A1~2, ξ-B1~2, FEAT-35~36) |
| Spec 1 슬라이스 ν (F13+F18+F19) | ✅ 머지 `71208c2` · improver findings 9건(ν-A1~3, ν-B1~3, FEAT-37~39) |
| Spec 2 재현 케이스 작성 | ⏳ Spec 2 세션 시작 시 |
| Spec 2 design doc | ⏳ 별도 세션 |
| Spec 2 plan | ⏳ Spec 2 design 승인 후 |

**다음 단계**: Spec 2 (F11·F14·F16·F17·**F20**) brainstorming 진입. F20(서브네트워크 누락) 위중도 최상. 동시에 batch ⑨ 백로그 잔여(특히 **μ-A1 팔레트 무음**, **ν-A2 영속화**)도 별도 핫픽스/정리 슬라이스 후보.

### 2026-06-01 update (Spec 2 진행 상태)

| 항목 | 상태 |
|---|---|
| Spec 2 design doc | ✅ `2026-06-01-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` (bd34968) |
| Spec 2 1차 plan (π/τ/φ) | ✅ 3개 plan (207b8c2) |
| Spec 2 1차 슬라이스 τ (F11) | ✅ 머지 `0863428` · improver 7건 (FEAT-40~41) |
| Spec 2 1차 슬라이스 π (진단·repro) | ✅ 머지 `ad934a5` · improver 7건 (FEAT-42~43) — **π 데이터로 ρ scope 축소 확정** |
| Spec 2 1차 슬라이스 φ (F16) | ✅ 머지 `08827a5` · improver 7건 (FEAT-44~45) |
| Spec 2 2차 plan (ρ/σ) | ✅ 2개 plan (cd7bb93) — π 데이터 기반 |
| Spec 2 2차 슬라이스 ρ (F20 fix) | 🔄 implementer 진행 (AssetResolver 연결, κ-A2 동시 해소) |
| Spec 2 2차 슬라이스 σ (F17 fix) | 🔄 implementer 진행 (digit-only subpin 정렬) |

**F14 잔존**: Orion 샘플 repro 미재현 — Spec 1 작업 중 자연 해소 가능성. 사용자 추가 보고 시 별도 슬라이스로 재진입.

**ρ·σ 머지 후 batch ⑨ 완전 마감 후보**. 잔여 핫픽스 후보 (별도 사이클): μ-A1(팔레트 무음), τ-A1(툴바 desync), ν-A2+τ-A2(영속화 통일), 정리 슬라이스(ν-B1+φ-B2 pin walk 통합 1순위).

### 2026-06-01 마감 (batch ⑨ 종료)

| 슬라이스 | 머지 |
|---|---|
| ρ (F20 fix) | ✅ `b0464a6` · improver 8건 (FEAT-46~47) |

**batch ⑨ 완전 마감**. 사용자 피드백 11건 중 10건 처리(F10·F11·F12·F13·F15·F16·F17·F18·F19·F20), 1건 deferred(F14 Orion 미재현). 430 tests passing.

**최우선 핫픽스 후보** (다음 사이클): **ρ-A1 regex silent miss** — F20 fix 자체가 무효화 가능. ρ-A3와 묶어 처리.

본 트래커는 Spec 1·2 양쪽 디자인 문서에서 §2 검증 표·§3 불변식·§4 분할의 단일 출처(SoT)로 인용된다.
