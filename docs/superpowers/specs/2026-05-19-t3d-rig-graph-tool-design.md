# T3D 그래프 분석·시각화 도구 — 설계 문서

- **작성일**: 2026-05-19
- **상태**: 브레인스토밍 산출물 — 사용자 리뷰 대기
- **패키지명**: `t3dgraph` (가칭, 변경 가능)
- **리포 루트**: `C:\Users\jylee\source\UeT3DRay` · 코드: `src/t3dgraph/`

---

## 1. 개요 및 목적

Unreal Engine이 일부 `.uasset`을 익스포트할 때 생성하는 **T3D 텍스트 데이터**를 해석하는 도구이다. 1차 대상은 **Control Rig(RigVM 그래프)** 익스포트.

산출물 2종:

1. **파서 라이브러리** — `.t3d` 텍스트를 무손실 구조화 모델로 변환. 순수 Python, Qt 의존성 없이 단독 import·사용 가능.
2. **그래프 분석·시각화 데스크톱 앱** — PySide6 GUI. 노드 그래프를 시각화하고 실행 흐름을 분석.

---

## 2. 배경 — 입력 데이터

### 2.1 데이터 정체

`Orion_WorkStation_Rig_Analysis` 폴더의 11개 `.t3d.txt` 파일은 Control Rig 에셋 2종(기본 `weldingArm_CR` + `Target` 변형)을 서브그래프 단위로 익스포트한 것이다. T3D는 UE 그래프 노드의 복사/붙여넣기 텍스트 포맷이다.

| 접미사 | 내용 |
| --- | --- |
| `__RigVMModel` | 최상위 모델 그래프 |
| `__RigVMFunctionLibrary` | 함수 라이브러리 |
| `__IK_Rig` | IK_Rig 함수 그래프 |
| `__Physics` | Physics 콜랩스 노드 그래프 |
| `__Target_Set` | (Target 변형 전용) |

### 2.2 포맷 문법

- 중첩 `Begin Object … End Object` 블록 구조
- 헤더: `Begin Object Class=<클래스> Name="<이름>" ExportPath="<전체경로>"`
- 본문: `Key=Value` 줄 — 스칼라(`Direction=Output`), 따옴표 문자열, 구조체 리터럴(`Position=(X=…,Y=…)`), 중첩 구조체(`(A=(…),B=(…))`), 인덱스 배열(`Pins(0)="…"`)
- **2단계 인코딩**: 같은 객체가 ① `Class=` 포함 선언 블록(중첩 구조만, 값 비어있음) → ② `Name=`만 있는 정의 블록(값 채움) 두 번 등장
- **그래프 구조**: `RigVMUnitNode`/`RigVMDispatchNode`/`RigVMFunctionEntryNode` 등 = 노드, 각 노드는 `Pins` 보유 / `RigVMLink` 객체가 `SourcePinPath`·`TargetPinPath`로 엣지 표현 / 그래프 객체가 `Nodes(i)=`·`Links(i)=`로 집계

### 2.3 검증된 데이터 사실 (설계 근거)

- **`DefaultValueType`**: 11개 파일 514개 occurrence 전부 `Unset`. `Override`/`AutoDetect` 등 0건 → 데이터에 명시적 "변경(오버라이드) 플래그"가 **없음**.
- **실행 흐름**: 스캔한 샘플(IK_Rig, RigVMModel)의 실행 핀 체인은 전부 **선형** — fan-in 수렴점 0건. (포맷은 fan-in을 표현 가능하나 이 샘플엔 없음.)
- **변수**: 기본 리그(`weldingArm_CR`) 파일엔 "Variable" 0회. `Target` 변형만 `RigVMVariableNode`(`IKTarget` 등) 사용.
- **bool 표기 비일관**: `DefaultValue`에 `True`/`False`와 `false`가 혼재.

---

## 3. 범위

### 3.1 v1 범위

- **입력**: `.t3d` 파일 **1개 단위** 로드
- **그래프 타입**: **RigVM(Control Rig)** 만 — 첫 번째 플러그인
- **파서**: 무손실 — 모든 속성·전체 핀 트리 보존
- **시각화**: PySide6 `QGraphicsView` 노드 그래프, "분석 중심" 윈도우 레이아웃
- **분석**: fan-in 수렴점 탐지, 공통 다운스트림 식별, 실행 순서 선형화
- **인스펙터**: 핀별 기본값·연결됨(네비게이션)·변경됨(휴리스틱)

### 3.2 비목표 / 한계 (v1)

- **원본 `.t3d` 재출력(round-trip)** — 무손실 모델이 가능케 하되 v1 기능 아님
- **에셋 단위 통합** — 파일 간 교차 참조 resolver는 미구현. 단, 미해결 참조를 external ref로 보존해 **확장 seam은 설계**에 포함 (3.3 참조)
- **멤버 변수 전체 목록** — `.t3d`는 노드 복사 포맷이라 *그래프에 쓰인* 변수만 추출 가능. 선언만 되고 미사용인 변수, 선언 메타데이터(카테고리·툴팁 등)는 불가
- **정확한 아키타입 기본값 DB** — v1은 타입 zero-value 휴리스틱. "변경됨(추정)"으로 라벨
- **외부 pip-install 플러그인** — entry-point 발견은 v2

### 3.3 향후 확장 (seam 설계됨)

- 에셋 단위 통합 — 파일별 모델 위에 `ExportPath` 매칭 resolver 레이어 추가
- entry-point 기반 외부 플러그인 발견
- round-trip 익스포트
- 정확한 노드 타입 기본값 DB (변경됨 판정 전략 교체)
- RigVM 외 그래프 타입 플러그인

---

## 4. 아키텍처

### 4.1 MVC + 플러그인 구조

최상위는 **플러그인 우선** 레이아웃(`core` + `plugins`). MVC는 규율로 유지 — Model = `core/t3d`+`core/base`+`core/analysis` 및 각 플러그인 `interpreter.py`/`types.py`, View·Controller = `core/app` 및 플러그인 `view.py`/`controller.py`.

레이어 (위=추상, 아래=구체):

```
viewer (PySide6)        QGraphicsView 그래프 + 뷰 모드
analysis                fan-in 탐지, 공통 다운스트림, 실행 순서   ┐
plugins/rigvm           RigVM 구체 해석                          ├ 추상 GraphModel에만 의존
core/base (추상)         AbstractGraphInterpreter + GraphModel    ┘
core/t3d (구조 파서)     Begin/End 트리 + 재귀 값 문법 (그래프 무관, 무손실)
```

### 4.2 디렉터리 레이아웃

```
UeT3DRay/
├─ src/t3dgraph/
│  ├─ core/
│  │  ├─ t3d/                  # T3D 구조 파서 (무손실, 순수 Python)
│  │  │  ├─ tokenizer.py            # .t3d 텍스트 → 토큰
│  │  │  ├─ values.py               # 재귀 하강 값 파서 (구조체·중첩·배열·참조)
│  │  │  ├─ objects.py               # Begin Object…End Object → 객체 트리
│  │  │  └─ document.py              # 무손실 T3DDocument (2단계 병합)
│  │  ├─ base/                  # 추상 계약 (순수 Python, Qt 없음)
│  │  │  ├─ graph_model.py           # GraphModel/Node/Pin/Link
│  │  │  ├─ interpreter.py            # AbstractGraphInterpreter (최상위 추상)
│  │  │  └─ plugin.py                # GraphTypePlugin 계약
│  │  ├─ analysis/              # 그래프 무관 분석 (순수 Python)
│  │  │  ├─ flow.py                  # fan-in 수렴점, 공통 다운스트림
│  │  │  └─ execution_order.py        # 구조화된 실행 순서 선형화
│  │  ├─ registry.py            # 플러그인 발견·등록 (순수 Python)
│  │  └─ app/                   # ── Qt 영역 ──
│  │     ├─ view.py                  # AbstractGraphView
│  │     ├─ controller.py            # AbstractGraphController
│  │     ├─ main_window.py           # 윈도우 셸
│  │     └─ app.py                   # 진입점: 플러그인 로드 → M/V/C 조립
│  └─ plugins/
│     └─ rigvm/                 # 그래프 타입 플러그인 = 자기완결 단위
│        ├─ __init__.py              # 등록 진입점 (import 시 self-register)
│        ├─ interpreter.py           # RigVMGraphInterpreter (순수 Python)
│        ├─ types.py                 # RigVM 전용 노드/핀/링크 확장 (순수 Python)
│        ├─ view.py                  # RigVM 전용 View (선택, Qt)
│        └─ controller.py            # RigVM 전용 Controller (선택, Qt)
├─ config/graph_types.toml      # 플러그인 활성화·class_prefix 매핑
├─ docs/superpowers/specs/
├─ docs/superpowers/plans/
├─ tests/
└─ pyproject.toml
```

### 4.3 의존성 경계

- **Qt를 import하는 곳**: `core/app/` 와 플러그인 `view.py`/`controller.py` 뿐
- 플러그인 `__init__.py`는 view/controller를 **지연 참조**(문자열 경로)로 등록 → 파싱·분석만 쓰는 소비자는 Qt를 안 건드림
- **이 Qt-free 부분이 곧 산출물 #1 라이브러리**
- Model 레이어 서드파티 의존성 0 (stdlib만; config는 Python 3.11+ `tomllib` 내장)

---

## 5. 컴포넌트

### 5.1 T3D 구조 파서 — `core/t3d/`

- `tokenizer.py` — `.t3d` 텍스트를 토큰 스트림으로
- `values.py` — **재귀 하강 값 파서**. 스칼라·따옴표 문자열·타입付 객체 참조(`/Script/…'/Game/…'`)·구조체 리터럴·중첩 구조체·배열(`()`, 인덱스형) 처리. 정규식 불가, 직접 작성. 외부 의존성 0.
- `objects.py` — `Begin Object … End Object` 중첩 트리 구성
- `document.py` — 무손실 `T3DDocument`. **2단계 인코딩 병합** — `Class=` 선언 블록과 `Name=` 정의 블록을 하나의 완전한 객체로 통합
- 그래프 종류를 전혀 모름

### 5.2 추상 계약 — `core/base/`

- `graph_model.py` — `GraphModel`/`Node`/`Pin`/`Link` 추상 데이터 모델 (인터프리터 출력, 분석·뷰가 소비)
- `interpreter.py` — `AbstractGraphInterpreter` (최상위 추상클래스)
- `plugin.py` — `GraphTypePlugin` 계약: `id`, `class_prefixes`, `interpreter` 클래스, 선택적 `view`/`controller` 지연 참조

### 5.3 플러그인 레지스트리 — `core/registry.py`

- `plugins/` 하위 패키지를 import → 각 `__init__.py`가 `GraphTypePlugin`을 self-register
- `graph_types.toml` 로 활성화·`class_prefix` 오버라이드
- `클래스 → 인터프리터` 디스패치만 담당 (Model 순수성 유지; View/Controller 선택은 `core/app/app.py`가 처리)

`graph_types.toml` 예:

```toml
[graph_types.rigvm]
class_prefixes = ["/Script/RigVMDeveloper.", "/Script/ControlRigDeveloper."]
interpreter    = "t3dgraph.plugins.rigvm.interpreter:RigVMGraphInterpreter"
view           = "t3dgraph.plugins.rigvm.view:RigVMGraphView"        # 생략 시 base
controller     = "t3dgraph.plugins.rigvm.controller:RigVMController"  # 생략 시 base
```

### 5.4 RigVM 플러그인 — `plugins/rigvm/`

- `__init__.py` — import 시 `GraphTypePlugin` 인스턴스 구성 후 `registry.register()` 호출. view/controller는 지연 참조
- `interpreter.py` — `RigVMGraphInterpreter`. `T3DDocument` 객체 트리 → 추상 `GraphModel`. RigVM*Node → Node, 중첩 RigVMPin → Pin 트리, RigVMLink → Link, `RigVMVariableNode` → 변수 참조 추출, 미해결 외부 참조 → external ref 보존
- `types.py` — RigVM 전용 노드/핀/링크 확장 (실행 핀 타입 판정 등)
- `view.py`/`controller.py` — RigVM 전용 표현·인터랙션 (선택)

### 5.5 분석 — `core/analysis/`

추상 `GraphModel`만 보고 동작 → 그래프 종류 무관.

- `flow.py`:
  - 핀 단위 링크 그래프에서 **노드 단위 실행 그래프** 유도 (실행 핀 = `CPPType="FRigVMExecuteContext"` 사이의 링크)
  - **수렴점(fan-in)**: 들어오는 실행 엣지 in-degree ≥ 2 인 노드
  - **분기점**: 나가는 실행 엣지 out-degree ≥ 2 인 노드
  - 수렴점마다 **분기 프리픽스**(역방향 추적한 상류 경로) + **공통 다운스트림**(정방향 추적, 모든 경로 공유) 산출
  - 진입/종료 노드, 도달 불가 노드
- `execution_order.py`:
  - 실행 그래프를 위상 순회해 **구조화된 실행 순서** 산출 (루프·시퀀스·분기 중첩 트리)
- 표준 그래프 알고리즘(BFS/DFS·in-degree)만 사용 → stdlib only

### 5.6 뷰어 — `core/app/` + 플러그인 `view`/`controller`

- `QGraphicsView` 자체 구현 — `NodeItem`/`PinItem`/`LinkItem` (커스텀 `QGraphicsItem`)
- 노드 배치는 데이터의 `Position` 좌표 사용
- 도크는 `QDockWidget` — 사용자가 자유 재배치 가능

---

## 6. 데이터 흐름

```
1. 로드          Controller: 사용자가 .t3d 파일 열기
2. 구조 파싱      core/t3d: tokenizer → objects → document
                  · values.py가 모든 속성값 파싱
                  · 2단계 인코딩(선언+정의 블록) 병합
                  → 무손실 T3DDocument
3. 종류 감지      registry: 최상위 객체 Class= → graph_types.toml 조회 → rigvm 선택
4. 해석          plugins/rigvm/interpreter: T3DDocument → 추상 GraphModel
                  · 미해결 외부 참조는 external ref로 보존
5. GraphModel    순수 데이터: 노드·핀트리·링크·변수참조·외부참조 + 원본 T3DDocument
6. 분석(요청 시)  core/analysis: GraphModel → AnalysisResult (수렴점·실행 순서 등)
7. 뷰 빌드        core/app/app.py가 graph type별 View/Controller 조립 →
                  scene이 Node의 Position 좌표로 아이템 배치
8. 인터랙션       뷰모드 토글·선택 → Controller가 view_state 갱신 → View 재렌더 (재파싱 없음)
```

---

## 7. 뷰어 UI

### 7.1 윈도우 레이아웃 — "분석 중심"

```
┌ 메뉴: 파일·뷰·분석 ──────────────────────────────────┐
├ 툴바: 뷰모드 토글 ───────────────────────────────────┤
│ ┌ 좌도크 ┐ ┌──── 그래프 캔버스 ────┐ ┌ 우도크 ──┐ │
│ │ 노드   │ │   (QGraphicsView)     │ │ 속성      │ │
│ │ 타입   │ │                       │ │ 인스펙터  │ │
│ │ 필터   │ │                       │ │           │ │
│ └────────┘ └───────────────────────┘ └───────────┘ │
│ ┌ 하단 도크: [분석 결과(수렴점)] [실행 순서] 탭 ────┐ │
│ └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 7.2 패널

- **노드 타입 필터** (좌측 도크) — 노드 타입별 체크박스. 끄면 해당 타입 노드 숨김
- **속성 인스펙터** (우측 도크) — 선택 노드의 핀·타입·기본값·무손실 속성
- **분석 결과** (하단 탭) — fan-in 수렴점 목록. 행 클릭 시 캔버스가 해당 노드로 이동
- **실행 순서** (하단 탭) — 실행 핀 링크를 위상 순회해 **코드처럼** 표시. 들여쓰기로 `ForEach`/`Sequence` 중첩, 함수/콜랩스 노드는 `name() { … }` (더블클릭 시 서브그래프로 이동), 행 클릭 시 캔버스 노드와 양방향 연동. *형태는 추후 반복 개선 예정.*

### 7.3 뷰 모드 (`view_state`)

- **연결된 핀만 표시** — 링크 있는 핀만 보임 (깊은 핀 트리 정리)
- **깊이 펼침** — 핀 서브트리 펼침/접힘
- **fan-in 강조** — 수렴점 시각 강조
- **노드 타입 가시성** — 노드 타입 필터와 연동

### 7.4 인스펙터 — 연결됨 / 변경됨

- **연결됨** — 핀이 링크를 가지면 대상 `노드.핀` 표시. 클릭 → 캔버스가 연결된 노드로 이동·선택·포커스, 인스펙터도 갱신. 양방향(캔버스에서 링크 선택 시 인스펙터 핀 강조).
- **변경됨** — 데이터에 오버라이드 플래그가 없으므로 **휴리스틱**: 핀의 `DefaultValue`가 해당 CPPType의 zero-value(숫자 0·bool false·빈 구조체/문자열)와 다르면 "변경됨(추정)". 비교 로직은 **전략(strategy)으로 분리** → 추후 정확한 아키타입 기본값 DB로 교체 가능.

---

## 8. 에러 처리

- **파싱 에러** — `T3DParseError(line, col, message)` 로 정확한 위치 보고. v1 strict, `--lenient` 플래그 시 불량 객체 skip하고 경고 누적
- **알 수 없는 그래프 타입** — registry 매칭 실패 시 명확한 메시지("class X 인터프리터 없음 — graph_types.toml 확인"), 크래시 없음
- **알 수 없는 노드/핀 클래스** (알려진 그래프 타입 내부) — 무손실이므로 **제네릭 노드로 폴백** + 경고. UE 버전업으로 새 노드 타입 생겨도 안 깨짐
- **미해결 외부 참조** — 에러 아님. external ref로 기록, UI에 "외부"로 표시
- **config 불량** — `graph_types.toml` 파싱 실패 시 명확한 메시지
- **GUI** — 파일 취소·없음·권한 오류 → 메시지 박스, 크래시 없음
- **로깅** — `.t3d`가 크므로 로그엔 파일 경로 + 소량 요약(카운트·에러 위치)만. 원본 내용 덤프 금지

---

## 9. 테스트 전략

`pytest` + `pytest-qt`. Model 레이어가 Qt-free → GUI 없이 단위 테스트 용이.

- **파서** — tokenizer / 값 파서(구조체·중첩·배열·참조) / 객체 트리 / 2단계 병합 — 소형 수제 `.t3d` 스니펫 픽스처
- **무손실 검증** — 11개 실제 Orion 파일 = 골든 통합 픽스처. 객체·핀·링크 카운트와 알려진 값 단언
- **인터프리터** — 실제 파일로 RigVM 그래프 검증 (IK_Rig 선형 체인, Physics For_Each 루프)
- **분석** — ⚠️ **fan-in은 합성 픽스처 필수**: 제공된 샘플 11개는 실행 흐름이 전부 선형(수렴점 0건)이라 실제 파일로 fan-in 테스트 불가. 수렴점이 있는 합성 그래프를 만들어 검증. 실행 순서도 합성 + 실제 픽스처 병행
- **레지스트리/플러그인** — 클래스 문자열 → 타입 감지, `__init__.py` 자기등록 동작
- **View/Controller** — pytest-qt 스모크 테스트 + `view_state` 로직 단위 테스트

---

## 10. 기술 스택

- **언어**: Python 3.11+ (`tomllib` 내장 활용)
- **GUI**: PySide6 (Qt) — `QGraphicsView` 자체 구현
- **테스트**: pytest, pytest-qt
- **Model 레이어 서드파티 의존성**: 0 (stdlib만)
- **플랫폼**: Windows 11 (1차)

---

## 11. 결정 기록

| 결정 | 근거 |
| --- | --- |
| 언어 Python | Windows·생태계 적합, 파싱·그래프 라이브러리 풍부 |
| UI PySide6 | 사용자 지정 |
| 파서 무손실 | 사용자 선택(2+1). 얕게/깊게는 파서가 아닌 UI 뷰 모드 |
| 값 파서 직접 작성 | round-trip·관용 표기 때문에 파서 제너레이터 부적합 |
| 플러그인 우선 레이아웃 | 사용자 선택. 그래프 타입 = 자기완결 단위, 추출 용이 |
| `__init__.py` self-register | 사용자 지정 |
| graph type 감지 = config 기반 | 사용자 지정. 코드에 박지 않음 |
| QGraphicsView 자체 구현 | 커스텀 뷰 모드 자유도, 의존성 최소, Position 좌표 활용 |
| 윈도우 레이아웃 "분석 중심"(C) | 사용자 선택 |
| 변경됨 = 타입 zero-value 휴리스틱 | 데이터에 오버라이드 플래그 없음(514/514 Unset). 전략 분리로 추후 교체 |
| 파일 단위 시작, 에셋 단위 seam | 사용자 선택. 교차 참조가 데이터에 명시되어 확장 깨끗함 |

---

## 12. 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 구현 계획을 작성한다. 구현은 다수 파일에 걸치므로 작은 하위 작업으로 분해한다.
