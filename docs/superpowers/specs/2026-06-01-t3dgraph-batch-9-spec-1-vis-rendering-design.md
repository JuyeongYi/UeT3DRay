# t3dgraph batch ⑨ Spec 1 — 시각·렌더링 설계 문서

- **작성일**: 2026-06-01
- **상태**: brainstorming 산출물 — 사용자 리뷰 대기
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **트래커**: `2026-06-01-t3dgraph-batch-9-user-feedback-2-tracker.md` (§2 검증·§3 PRESERVE-ALL·§4 분할의 단일 출처)
- **자매 spec**: Spec 2 — 데이터·상태·버그 (별도 세션)

---

## 1. 범위

본 문서가 다루는 사용자 피드백 6건:

| ID | 한 줄 요약 | 트래커 §2 결론 |
|---|---|---|
| F10 | 타입별 핀 색 구분 | 신규 (TOML 팔레트) |
| F12 | 구조체 접기 발견 불가 | UX 결함 (disclosure 누락) |
| F13 | 연결선 직선 | 신규 (베지어) |
| F15 | 인스펙터 폭 폭주 | 레이아웃 결함 (컬럼 폭 + dock 폭) |
| F18 | 노드 드래그 이동 | 신규 (`ItemIsMovable` + 영속) |
| F19 | 노드별 펼침/접기 | 신규 (컨텍스트 메뉴) |

본 문서 밖 (Spec 2 또는 deferred): F11·F14·F16·F17·F20, batch ② F4. 트래커 §4 참조.

---

## 2. PRESERVE-ALL 불변식 (재확인)

본 spec 6건 전부 모델 무변경. 렌더 옵션·시각 표시·UI 보조 입력만 추가/조정.

| ID | 조작 | 노드 보존 | 링크 보존 |
|---|---|---|---|
| F10 | 핀 dot 색 변경 | ✅ | ✅ |
| F12 | 핀 행 좌측 indicator 추가 | ✅ | ✅ |
| F13 | `LinkItem` 클래스만 `Line`→`Path` | ✅ | ✅ (`source_path`·`target_path` 보존) |
| F15 | dock·컬럼 폭만 변경 | ✅ | ✅ |
| F18 | `NodeItem.setPos` 변경 (T3D `Position` 미수정) | ✅ | ✅ |
| F19 | `expanded_pin_paths` set 부분 조작 | ✅ | ✅ |

테스트 슬롯: 통합 테스트에 `len(scene._nodes) >= len(graph.nodes)` 어서션 유지.

---

## 3. F10 — 타입별 핀 색

### 3.1 디자인

핀 dot 색을 `pin.cpp_type` 기반으로 매핑. UE Blueprint 컨벤션을 디폴트로, 사용자가 설정 파일에서 전부 오버라이드 가능.

3계층 룩업:

1. **special** (패턴) — `cpp_type`이 패턴 토큰 포함 시 특별 처리
   - `ExecuteContext` 포함 → palette `exec`
   - `TArray<` 시작 → inner 추출 후 재귀 룩업 + 외곽선 변형
2. **bucket** (cpp_type 토큰 → palette key) — 정규화 매핑
3. **palette** (palette key → `#RRGGBB`) — 색 정의

매치 실패 시 palette `default`.

### 3.2 설정 파일

- **번들 디폴트**: `src/t3dgraph/core/app/resources/pin_colors.toml` — UE Blueprint 컨벤션 전체 박힘
- **사용자 파일**: `%APPDATA%/t3dgraph/pin_colors.toml` (Win) / `$XDG_CONFIG_HOME/t3dgraph/pin_colors.toml` (Linux). `XDG_CONFIG_HOME` 미설정 시 `~/.config/t3dgraph/`로 폴백.
- **첫 실행**: 사용자 파일 없으면 번들에서 풀 카피 (사용자가 열면 모든 키 가시).
- **런타임**: 사용자 파일만 읽음 (부분 머지 X). 메뉴 "팔레트 리셋" → 번들 풀 카피로 덮어쓰기.
- **형식**: TOML (Python 3.11 `tomllib`, 신규 의존성 0).

### 3.3 TOML 스키마

```toml
[palette]
exec    = "#FFFFFF"
bool    = "#A02020"
int     = "#1FBEB6"
float   = "#7AC74F"
name    = "#C68FE6"
string  = "#FF66FF"
struct  = "#5B8FF9"
object  = "#3F9CBE"
default = "#C8C878"

[bucket]
# cpp_type 토큰 → palette key
bool    = "bool"
float   = "float"
double  = "float"
int32   = "int"
int64   = "int"
uint8   = "int"
uint32  = "int"
FName   = "name"
FString = "string"
FText   = "string"
FVector = "struct"
FRotator = "struct"
FTransform = "struct"
FQuat   = "struct"
FRigElementKey = "struct"
# ... (UE RigVM 빈출 cpp_type 전부)

[special]
exec_marker  = "ExecuteContext"  # cpp_type 포함 → exec 색
array_marker = "TArray<"         # cpp_type 시작 → inner 추출 + 외곽선
```

### 3.4 모듈

신규 `src/t3dgraph/core/app/pin_colors.py`:

```python
@dataclass(frozen=True)
class ResolvedColor:
    color: QColor          # 메인 색
    is_array: bool         # True면 외곽선 변형
```

```python
class PinColorTable:
    @classmethod
    def load(cls) -> "PinColorTable": ...   # 사용자 dir 우선, 없으면 번들 카피 후 로드
    def resolve(self, cpp_type: str | None) -> ResolvedColor: ...
    @classmethod
    def reset_user_file(cls) -> Path: ...   # 번들로 덮어쓰기. 새 경로 리턴
```

### 3.5 인스턴스 보유 위치

`PinColorTable` 인스턴스 1개를 `MainWindow.__init__`에서 `PinColorTable.load()`로 생성·보유. `scene.populate(..., pin_colors=self.pin_colors)` 시그니처로 주입, `scene._build_node`(또는 인라인)에서 `NodeItem(node, ..., pin_colors=pin_colors)`로 전달. 테스트는 임시 `PinColorTable`을 직접 주입 가능 (의존성 주입 모킹 불필요).

### 3.6 items.py 변경

`NodeItem.__init__`에서 `pin_colors: PinColorTable` 인자로 주입받아 사용:

```python
resolved = color_table.resolve(row.pin.cpp_type)
dot.setBrush(QBrush(resolved.color))
if resolved.is_array:
    dot.setPen(QPen(QColor(40, 40, 40), 1.5))  # 외곽선 변형
```

기존 라벨 색·노드 배경은 무변경 (다크 가독성 유지).

### 3.7 테스트 `tests/app/test_pin_colors.py`

- 번들 TOML 파싱 성공
- `bucket`/`special` 매핑 정확도: 주요 토큰 10여개
- 미정의 cpp_type → `default` 폴백
- `TArray<bool>` → bool 색 + `is_array=True`
- 사용자 dir 없을 때 첫 `load()` 호출이 번들 카피 생성
- `reset_user_file()` 후 사용자 파일이 번들과 바이트 동일

---

## 4. F12 — 구조체 접기 발견 불가

### 4.1 디자인

`pin.subpins`가 비어있지 않은 핀 행 좌측 들여쓰기 앞에 disclosure indicator:

- ▶ (펼침 가능, 접힘 상태) / ▼ (펼침 됨)
- 8×8px, 라벨과 같은 회색(`#D2D2D2`)
- **단일 클릭으로 토글** (indicator 영역만)
- 기존 행 더블클릭 토글은 호환성 유지

### 4.2 items.py 변경

`collect_pin_rows`가 반환하는 `PinRow`에 `has_children: bool` 필드 추가.

`NodeItem.__init__` 행 렌더링 루프:

```python
if row.has_children:
    arrow = QGraphicsSimpleTextItem("▼" if row.path in expanded_paths else "▶", self)
    arrow.setBrush(QBrush(QColor(210, 210, 210)))
    ax = (indent - 10) if is_input else (NODE_WIDTH - indent + 2)
    arrow.setPos(ax, cy - ROW_HEIGHT / 2 + 2)
    self._arrows[row.path] = arrow
```

들여쓰기 계산 조정: `indent = 8 + depth*12` → `indent = 18 + depth*12` (좌측 8px arrow 영역 확보).

마우스 단일 클릭:

```python
def mousePressEvent(self, event):
    y = event.pos().y()
    x = event.pos().x()
    row = int((y - HEADER_HEIGHT) / ROW_HEIGHT)
    if 0 <= row < len(self._row_paths):
        path = self._row_paths[row]
        if path in self._arrows and self._is_in_arrow_zone(x, row):
            self._bus.pin_toggle_requested.emit(path)
            event.accept()
            return
    super().mousePressEvent(event)
```

`_is_in_arrow_zone`은 input/output 따라 0~16px 또는 NODE_WIDTH-16~NODE_WIDTH 범위 검사.

### 4.3 테스트 `tests/app/test_items_disclosure.py`

- subpins 보유 핀 행에 ▶ 텍스트 아이템 존재
- 펼침 상태에서 ▼로 표시
- subpins 없는 핀 행에 화살표 미존재
- 화살표 영역 클릭 시 `pin_toggle_requested` 발사 (라벨 영역 클릭은 미발사)
- 기존 더블클릭 토글 경로 회귀 없음

---

## 5. F13 — 연결선 곡선 (UE 스타일 cubic bezier)

### 5.1 디자인

`LinkItem`이 `QGraphicsLineItem` → `QGraphicsPathItem`. cubic bezier로 두 핀 앵커 연결:

```
p1 = source anchor (오른쪽)
p2 = target anchor (왼쪽)
dx = p2.x - p1.x

# 핸들 길이 — 양쪽 endpoint 수평
handle_len = max(abs(dx) / 2, MIN_HANDLE_PX=40)

# 백워드 (출력이 입력 노드의 왼쪽에 있는 경우)
if dx < 0:
    handle_len = max(handle_len, BACKWARD_HANDLE_PX=120)

c1 = p1 + (handle_len, 0)
c2 = p2 - (handle_len, 0)

path = QPainterPath(p1)
path.cubicTo(c1, c2, p2)
```

선 두께·색 현행 유지: `QPen(#AAAAAA, 1.5)`.

### 5.2 items.py 변경

```python
class LinkItem(QGraphicsPathItem):
    def __init__(self, p1: QPointF, p2: QPointF):
        super().__init__(self._build_path(p1, p2))
        self.setPen(QPen(QColor(170, 170, 170), 1.5))
        self.setZValue(-1)

    @staticmethod
    def _build_path(p1: QPointF, p2: QPointF) -> QPainterPath:
        dx = p2.x() - p1.x()
        handle = max(abs(dx) / 2, 40.0)
        if dx < 0:
            handle = max(handle, 120.0)
        c1 = QPointF(p1.x() + handle, p1.y())
        c2 = QPointF(p2.x() - handle, p2.y())
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        return path
```

`scene._add_link` 변경 없음 (생성자 시그니처 동일).

### 5.3 테스트 `tests/app/test_scene_bezier.py`

- LinkItem이 PathItem 인스턴스
- path.elementCount() 검사 — moveTo + 3개 cubic point = 4
- path의 시작·끝이 p1·p2와 일치
- 백워드 케이스(p1.x > p2.x)에서 핸들 길이 `BACKWARD_HANDLE_PX` 이상으로 확장
- 기존 link 생성 통합 테스트 회귀 없음

---

## 6. F15 — 인스펙터 폭 안정화

### 6.1 디자인

폭 폭주 원인: `QTreeWidget`의 디폴트 `setStretchLastSection(True)` + dock의 자식 sizeHint 추종.

해결:

- 컬럼별 디폴트 폭 명시:
  - 핀 140, 타입 160, 방향 70, 기본값 120, 상태 90
- 헤더 `setSectionResizeMode(QHeaderView.Interactive)` — 사용자 드래그 가능
- `setStretchLastSection(False)` — 마지막 컬럼 자동 늘림 OFF
- `setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)`
- 셀 텍스트가 컬럼 폭 초과 시 `ToolTipRole` 자동 부여 (긴 cpp_type/default_value 풀 텍스트 보존)

dock 자체는 사용자가 자유롭게 드래그 (maximumWidth 미지정).

### 6.2 inspector_panel.py 변경

```python
def __init__(self):
    super().__init__()
    layout = QVBoxLayout(self)
    self._title = QLabel("(노드를 선택하세요)")
    self._tree = QTreeWidget()
    self._tree.setColumnCount(5)
    self._tree.setHeaderLabels(["핀", "타입", "방향", "기본값", "상태"])
    header = self._tree.header()
    header.setSectionResizeMode(QHeaderView.Interactive)
    header.setStretchLastSection(False)
    for i, w in enumerate((140, 160, 70, 120, 90)):
        self._tree.setColumnWidth(i, w)
    self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    ...
```

`_add_pin` 행 생성 시 컬럼별 텍스트가 컬럼 폭 초과(font metrics 기준)면 `setToolTip(col, full_text)`.

### 6.3 테스트 `tests/app/test_inspector_layout.py`

- 노드 선택 전후 dock(또는 InspectorPanel) `sizeHint().width()` 안정 (긴 cpp_type 노드 선택해도 변동 임계 이하)
- 컬럼 합 > 위젯 폭일 때 horizontal scroll bar 등장
- 긴 default_value 셀에 ToolTipRole 부여됨

---

## 7. F18 — 노드 드래그 이동

### 7.1 디자인

`NodeItem`에 `ItemIsMovable` 활성화. 위치는 세션 메모리(`LayoutOverrides`)에 그래프 단위 보관. `scene.populate()`에서 override 우선 적용. 사이드카 파일 영속은 본 spec 밖 (다음 라운드 확장 여지).

### 7.2 LayoutOverrides 모듈

신규 `src/t3dgraph/core/app/layout_overrides.py` (순수 Python, Qt 없음):

```python
@dataclass
class LayoutOverrides:
    """그래프별 노드 위치 오버라이드. populate 우선 적용."""
    _by_graph: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)

    def set(self, graph_key: str, node: str, x: float, y: float) -> None: ...
    def get(self, graph_key: str, node: str) -> tuple[float, float] | None: ...
    def clear_node(self, graph_key: str, node: str) -> None: ...
    def clear_graph(self, graph_key: str) -> None: ...
    def all_for_graph(self, graph_key: str) -> dict[str, tuple[float, float]]: ...
```

`graph_key`는 `MainWindow._current_graph_key()`에서 도출 — `f"{graph.label or '(unlabeled)'}/{graph.parent_node or ''}"`. 루트 그래프(parent_node=None)는 `"<label>/"`, 서브그래프는 `"<root_label>/<parent_node>"` 형태로 안정. 라벨 미설정 그래프는 `(unlabeled)` 폴백(테스트 시드 등 엣지 케이스). F11 진입 시(Spec 2) ViewState 키 체계와 통일.

### 7.3 NodeItem 변경

```python
def __init__(self, node, *, ...):
    super().__init__(...)
    self.setFlag(QGraphicsItem.ItemIsSelectable, True)
    self.setFlag(QGraphicsItem.ItemIsMovable, True)            # F18
    self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True) # itemChange 활성
    ...

def itemChange(self, change, value):
    if change == QGraphicsItem.ItemPositionHasChanged and self._bus is not None:
        p = self.pos()
        self._bus.position_changed.emit(self.node.name, p.x(), p.y())
    return super().itemChange(change, value)
```

`_NodeItemBus`에 `position_changed = Signal(str, float, float)` 추가.

### 7.4 scene.populate 변경

```python
def populate(self, graph, *, view_state=None, flow=None, layout_overrides=None, graph_key=""):
    ...
    for node in graph.nodes:
        item = NodeItem(node, ...)
        # 우선순위: override > T3D Position > fallback grid
        override = layout_overrides.get(graph_key, node.name) if layout_overrides else None
        if override is not None:
            item.setPos(*override)
        elif node.position is None:
            item.setPos((fallback_i % 8) * 240.0, (fallback_i // 8) * 200.0)
            fallback_i += 1
        # else: NodeItem __init__이 이미 node.position 적용
```

### 7.5 main_window.py 변경

```python
self.layout_overrides = LayoutOverrides()
# scene.populate에 graph_key/overrides 전달
# NodeItem.bus.position_changed → self._on_node_moved
def _on_node_moved(self, node_name, x, y):
    self.layout_overrides.set(self._current_graph_key(), node_name, x, y)
```

`_current_graph_key()`는 `graph_stack.current()`에서 도출.

### 7.6 컨텍스트 메뉴 액션 (F19와 공유)

§8 참조. "원래 위치로 되돌리기"는 `layout_overrides.clear_node(...)` 후 `_rebuild_scene()`.

### 7.7 테스트 `tests/app/test_items_drag.py`, `test_layout_overrides.py`

- `NodeItem`에 `ItemIsMovable` 플래그 세팅됨
- `setPos`로 위치 이동 시 `position_changed` 신호 발사
- `LayoutOverrides.set/get/clear_node/clear_graph` 자료구조 동작
- `scene.populate` 재호출 후 override 위치 유지
- 탭 전환 시뮬레이션(별 graph_key) 후 복귀 시 위치 보존
- override 없는 노드는 `node.position` 또는 fallback grid 그대로
- "원래 위치로" 호출 후 `node.position` 복원

---

## 8. F19 — 노드별 펼치기/접기

### 8.1 디자인

노드 헤더 우클릭 → 컨텍스트 메뉴:

- "이 노드 모두 펼침"
- "이 노드 모두 접기"
- "원래 위치로 되돌리기" (F18)

향후 노드 단위 액션은 같은 메뉴에 적층.

### 8.2 NodeItem 변경

```python
def contextMenuEvent(self, event):
    if self._bus is not None:
        self._bus.context_menu_requested.emit(self.node.name, event.screenPos())
        event.accept()
```

`_NodeItemBus`에 `context_menu_requested = Signal(str, QPoint)` 추가.

### 8.3 ViewState 변경

```python
def expand_node_pins(self, node_name: str, all_paths: list[str]) -> None:
    """노드의 모든 핀 경로(서브핀 포함)를 expanded에 추가."""
    self.expanded_pin_paths.update(all_paths)

def collapse_node_pins(self, node_name: str) -> None:
    """노드 prefix 매칭 path를 expanded에서 제거."""
    prefix = f"{node_name}."
    self.expanded_pin_paths = {
        p for p in self.expanded_pin_paths if not p.startswith(prefix)
    }
```

호출 측에서 `all_paths` 도출(노드의 모든 pin path 재귀 수집)은 `main_window._collect_node_pin_paths(node)` helper.

### 8.4 main_window.py 슬롯

```python
def _on_node_context_menu(self, node_name: str, screen_pos: QPoint):
    menu = QMenu()
    act_expand = menu.addAction("이 노드 모두 펼침")
    act_collapse = menu.addAction("이 노드 모두 접기")
    menu.addSeparator()
    act_reset = menu.addAction("원래 위치로 되돌리기")
    chosen = menu.exec(screen_pos)
    if chosen is act_expand:
        node = self.graph.node_by_name(node_name)
        paths = self._collect_node_pin_paths(node)
        self.view_state.expand_node_pins(node_name, paths)
        self._rebuild_scene()
    elif chosen is act_collapse:
        self.view_state.collapse_node_pins(node_name)
        self._rebuild_scene()
    elif chosen is act_reset:
        self.layout_overrides.clear_node(self._current_graph_key(), node_name)
        self._rebuild_scene()
```

### 8.5 테스트 `tests/app/test_main_window_node_menu.py`

- 노드 우클릭 → 컨텍스트 메뉴 표시 (3개 액션)
- "모두 펼침" 후 해당 노드의 모든 pin path가 `expanded_pin_paths`에 포함
- "모두 접기" 후 해당 노드 prefix path가 set에서 제거. 다른 노드 expanded 불변
- "원래 위치로" 후 노드 위치가 `node.position`으로 복원
- F12 disclosure 회귀 없음

---

## 9. 통합·교차 관심사

### 9.1 슬라이스 분할 제안 (writing-plans에서 확정)

| 슬라이스 | 대상 | 변경 파일 | 의존 |
|---|---|---|---|
| **μ** 핀 시각 어휘 | F10·F12 | resources/pin_colors.toml, pin_colors.py, items.py | 없음 |
| **ν** 링크·레이아웃 | F13·F18·F19 | items.py(LinkItem, NodeItem flags/contextMenu), scene.py(populate sig), view_state.py, layout_overrides.py, main_window.py | μ 와 items.py 동시 편집 — 슬라이스 순서: μ 먼저 |
| **ξ** 인스펙터 레이아웃 | F15 | inspector_panel.py | 없음 (병렬 가능) |

`ν` 슬라이스가 가장 큼. μ → ν 순차, ξ는 어디서든 끼울 수 있음.

### 9.2 Spec 2와의 정합

- **F11 per-tab ViewState** ↔ **F18 LayoutOverrides.graph_key**: 같은 `(graph.label, parent_node)` 조합 키 사용. F11이 ViewState를 per-tab으로 분해할 때 `LayoutOverrides`도 같은 키 체계로 인덱싱되어 정렬 비용 0.
- Spec 2 진입 시 본 spec §7.2의 `graph_key` 도출 함수를 `view_state_index` 같은 공용 모듈로 추출 가능 (지금은 main_window 내부 메서드).

### 9.3 회귀 가드

기존 통합 테스트가 검증하는 동작:

- batch ② F1~F9 통합 흐름 (브레드크럼·서브그래프·연결된 핀만·fan-in)
- batch ⑥ 단축키 (Backspace, Alt+Left, Alt+Up)
- batch ⑦ θ-1/θ-2 (compute trace, data flow diff)
- batch ⑧ ι/κ/λ (round-trip, asset resolver, minimap)

본 spec 6건은 시각 레이어만 만지므로 위 통합 테스트가 그대로 통과해야 함. 회귀 시 슬라이스 진행 중단.

### 9.4 의존성

- 신규 외부 의존성 0
- Python 3.11 `tomllib` 사용 (pyproject.toml 기존 `requires-python = ">=3.11"`)
- PySide6 기존 사용 모듈 외 신규 import: `QGraphicsPathItem`, `QGraphicsSceneContextMenuEvent`, `QMenu`, `QPainterPath`, `QHeaderView` — 모두 기존 패키지 내

### 9.5 Out-of-scope

- 사이드카 layout 파일 (F18 영속) — 다음 라운드
- 색약 모드 / 라이트 테마 (F10 확장) — 별도 항목
- 자동 레이아웃(force-directed 등) — 분석 뷰어 정체성 외 (batch ② F4 deferred 정책 유지)
- 노드 멀티 선택 일괄 이동 — F18 1차 single-node drag만, 다음 라운드 확장

---

## 10. 다음 단계

1. 사용자 리뷰 (본 문서) — 변경 요청 시 §3~§8 해당 절 수정
2. 승인 후 `writing-plans` 스킬로 슬라이스 μ/ν/ξ 구현 플랜 작성
3. 슬라이스 순서: μ → ν, ξ 병렬 가능
4. Spec 2 (F11·F14·F16·F17·F20) 별도 brainstorming 세션 — F20 우선
