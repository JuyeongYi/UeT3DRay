# t3dgraph batch ⑬ — 시각 보강 & 함수 진입 설계 문서

- **작성일**: 2026-06-02
- **상태**: 사용자 승인 ("go") — 직접 디스패치
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **이전 사이클**: 자율 루프 cycle 1·2 (batch ⑨~⑫, master `f8fa09d`, 499 tests)

---

## 1. 범위

사용자 피드백 8건 → 5 슬라이스.

| ID | 한 줄 | 슬라이스 |
|---|---|---|
| **F21** | 출력만 있어야 할 핀이 입/출력 모두 — Hidden 핀이 input dot으로 잘못 표시 (모든 노드) | g1 |
| **F22** | 실행 핀이 항상 먼저 출력되게 | g2 |
| **F23** | 파라미터 순서 = 에디터 | g1+g2 부수 효과 (Hidden 숨김 + 실행 우선이 효과) |
| **F24** | 인스펙터 헤더 레이블 과대 | g3 |
| **F25** | 연결선 색 = 파라미터 색 | g4 |
| **F26** | 실행 핀 굵게 + 확실히 | g4 |
| **F27** | 실행 핀 흰색 → 다른 색 + 애니메이션 | g4 |
| **F28** | 그래프상에서 서브그래프·함수 노드 시각 구분 (노드 직접 더블클릭은 정상, 시각 정보 누락이 본질) | g5 |

---

## 2. PRESERVE-ALL

전 슬라이스 시각/UX 변경 — 모델·노드 보존 ✅. g1은 Hidden 핀 모델 보존(렌더링만 변경). g2는 인터프리터 출력 순서만 정렬.

---

## 3. g1 — 핀 Direction 정확화 (F21)

### 3.1 T3D Direction 값 분포 (Orion 샘플)

| Direction | 개수 | UE 의미 | 현 처리 → 목표 |
|---|---|---|---|
| Input | 2,236 | 입력 | LEFT ✓ → LEFT |
| Output | 1,207 | 출력 | RIGHT ✓ → RIGHT |
| **Hidden** | 637 | 설정 필드 (에디터 비표시) | LEFT (BUG) → **dot 미표시·라벨 muted** |
| **IO** | 198 | 주 실행핀(`ExecuteContext`) | LEFT (BUG) → **양쪽 dot** |

### 3.2 items.py 변경

`is_input` 분기 확장:

```python
direction = (row.pin.direction or "").lower()
is_hidden = direction == "hidden"
is_io = direction == "io"
is_output = direction == "output"
# direction 미설정 — 부모 direction 상속
if not direction and parent_direction is not None:
    direction = parent_direction
    is_output = direction == "output"
    is_io = direction == "io"
```

`collect_pin_rows`에 `parent_direction` 인자 추가, 재귀 시 propagate.

### 3.3 렌더링 분기

```python
if row.pin_direction == "hidden":
    # dot 없음, 라벨 muted 회색
    label.setBrush(QBrush(QColor(150, 150, 150)))
elif row.pin_direction == "io":
    # 양쪽 dot
    _draw_dot(0, cy, color)
    _draw_dot(NODE_WIDTH, cy, color)
    # 라벨 중앙
    label.setPos((NODE_WIDTH - label.boundingRect().width()) / 2, ...)
elif row.pin_direction == "output":
    _draw_dot(NODE_WIDTH, cy, color)
else:
    _draw_dot(0, cy, color)
```

### 3.4 PinRow 확장

`PinRow`에 `effective_direction: str` 필드 추가 (Hidden/IO/Output/Input/empty 정규화).

### 3.5 테스트

- Hidden 핀 → QGraphicsEllipseItem 미생성, 라벨 회색
- IO 핀 → dot 2개 (LEFT + RIGHT)
- Output struct 펼친 subpin → 부모 direction 상속해 RIGHT
- Input → LEFT (회귀)

---

## 4. g2 — 실행 핀 우선 정렬 (F22)

### 4.1 디자인

`_build_pin`이 children을 만든 직후 `_sort_pins_exec_first`로 안정 정렬. node.pins 순서가 모든 호출부에 반영.

```python
def _sort_pins_exec_first(pins: list[Pin]) -> list[Pin]:
    """실행 핀을 앞으로 (안정 정렬, 원래 순서 보존)."""
    return sorted(
        enumerate(pins),
        key=lambda iv: (not iv[1].is_execution, iv[0]),
    )
    # enumerate로 stable index 보존, is_execution=True가 (False, idx)로 앞쪽
```

실제로:

```python
def _sort_pins_exec_first(pins: list[Pin]) -> list[Pin]:
    return sorted(pins, key=lambda p: (not p.is_execution,))   # stable sort
```

Python sort는 stable, 같은 key는 원순서 보존. `(not is_execution,)` 키로 True가 앞에 오게.

### 4.2 적용 위치

`_add_node` 내 `pins=[_build_pin(c) for c in obj.children ...]` 결과를 `_sort_pins_exec_first()`로 wrap.

```python
pins = [_build_pin(c) for c in obj.children if t.is_pin_class(c.cls) or c.cls is None]
node = Node(..., pins=_sort_pins_exec_first(pins), ...)
```

### 4.3 테스트

- 실행 핀이 후방에 있는 합성 T3D → 정렬 후 첫 번째에 옴
- 다중 실행 핀(주 + Completed) → 그 사이 원순서 유지
- 실행 핀 없는 노드 → 변화 없음

---

## 5. g3 — 인스펙터 헤더 elide (F24)

### 5.1 디자인

`_title` QLabel에 단일 라인 강제 + elide. 풀 텍스트는 툴팁.

```python
self._title = QLabel("(노드를 선택하세요)")
self._title.setWordWrap(False)
self._title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
# 폰트 메트릭으로 한 줄 높이 고정
fm = QFontMetrics(self._title.font())
self._title.setMaximumHeight(fm.lineSpacing() + 4)
```

`show_node` 시점에 elide 적용:

```python
def _set_title(self, raw_text: str) -> None:
    fm = QFontMetrics(self._title.font())
    available = max(self._title.width() - 12, 100)
    elided = fm.elidedText(raw_text, Qt.ElideRight, available)
    self._title.setText(elided)
    self._title.setToolTip(raw_text)
```

`resizeEvent` 오버라이드해 폭 변경 시 재elide.

### 5.2 테스트

- 긴 cls + role 결합 → elided text에 `…` 포함, toolTip은 풀 텍스트
- 짧은 텍스트 → elide 없이 그대로
- height가 한 줄로 제한됨

---

## 6. g4 — Link/Exec 시각 (F25 + F26 + F27)

### 6.1 디자인

**6.1.1 Link 색 = source pin 색 (F25)**

`LinkItem.__init__`에 `pen_color: QColor` + `width: float` + `is_execution: bool` 인자:

```python
class LinkItem(QGraphicsPathItem):
    def __init__(self, p1: QPointF, p2: QPointF, *,
                 pen_color: QColor = QColor("#AAAAAA"),
                 width: float = 1.5,
                 is_execution: bool = False):
        super().__init__(self._build_path(p1, p2))
        pen = QPen(pen_color, width)
        if is_execution:
            pen.setStyle(Qt.DashLine)
            pen.setDashPattern([4, 3])
        self.setPen(pen)
        ...
        if is_execution:
            self._setup_animation()
```

`scene._add_link`가 source pin을 룩업해 색·실행 여부 결정:

```python
def _add_link(self, link, pin_colors):
    src_pin = self._lookup_pin(link.source_path)
    if src_pin is not None and pin_colors is not None:
        resolved = pin_colors.resolve(src_pin.cpp_type)
        color = resolved.color
        is_exec = src_pin.is_execution
    else:
        color = QColor("#AAAAAA")
        is_exec = False
    width = 3.0 if is_exec else 1.5
    item = LinkItem(p1, p2, pen_color=color, width=width, is_execution=is_exec)
```

**6.1.2 실행 핀 굵게 (F26)**

NodeItem 렌더링에서 `is_execution` 핀의 dot 반경 6px로:

```python
radius = 6.0 if row.pin.is_execution else PIN_RADIUS  # 4.0
dot = QGraphicsEllipseItem(mx - radius, cy - radius, 2*radius, 2*radius, self)
```

실행 핀 라벨도 굵게:

```python
font = label.font()
if row.pin.is_execution:
    font.setBold(True)
    label.setFont(font)
```

**6.1.3 실행 핀 색 + 애니메이션 (F27)**

`pin_colors.toml` 갱신:

```toml
[palette]
exec = "#FFB000"  # 앰버 — 다크 배경에서 확실히 보임 (기존 #FFFFFF)
```

사용자 파일 마이그레이션: `PinColorTable.load`가 사용자 파일에서 `exec=#FFFFFF`(legacy default) 발견 시 디폴트(`#FFB000`)로 자동 갱신 + statusBar 통지. `migration` 메커니즘은 ω-A2 마이그레이션 패턴 차용.

실행 link 애니메이션 — QTimer 기반 dash phase 회전:

```python
class LinkItem(QGraphicsPathItem):
    def _setup_animation(self):
        self._dash_phase = 0.0
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(50)  # 20fps
        self._anim_timer.timeout.connect(self._advance_dash)
        self._anim_timer.start()

    def _advance_dash(self):
        self._dash_phase -= 0.5
        pen = self.pen()
        pen.setDashOffset(self._dash_phase)
        self.setPen(pen)
        self.update()
```

성능: 실행 link만 애니메이션(데이터 link는 정적). Orion 샘플 기준 실행 link 수 ~50 정도 — 충분.

### 6.2 테스트

- Link 색이 source pin의 cpp_type → palette 색과 일치
- 실행 link는 dash + width 3px + animation
- 실행 핀 dot 반경 6px, 라벨 bold
- 팔레트 마이그레이션 — 사용자 파일 exec=#FFFFFF → 자동 #FFB000 갱신

---

## 7. g5 — 함수/서브그래프 시각 구분 (F28)

**사용자 명확화**: 노드 직접 더블클릭으로 진입은 정상 동작. 본질은 "그래프상에서 함수/서브그래프 노드를 시각적으로 확인할 수 없음". (별개 이슈: 미니맵 "그래프 위치 메뉴"에서 함수 진입은 §9 Out-of-scope 별도 조사 항목으로 deferred.)

### 7.1 디자인

`RigVMCollapseNode`/`RigVMFunctionReferenceNode` 클래스면 항상 chevron 표시. 색으로 상태 구분:

```python
def _function_entry_state(self) -> tuple[str, QColor] | None:
    """function-like 노드의 진입 가능 상태.

    Returns (chevron_char, color) or None if not function-like.
    """
    suffix = (self.node.cls or "").rsplit(".", 1)[-1]
    if suffix not in ("RigVMCollapseNode", "RigVMFunctionReferenceNode"):
        return None
    if self.node.subgraph is not None:
        return "▶", QColor("#90EE90")    # green — enterable
    # subgraph 없음 — 사유 추정
    if suffix == "RigVMFunctionReferenceNode":
        return "▶", QColor("#FFD700")    # yellow — resolver 필요
    return "▶", QColor("#888888")        # gray — collapse without graph (rare)
```

NodeItem 헤더 렌더링에서 호출:

```python
state = self._function_entry_state()
if state is not None:
    char, color = state
    chev = QGraphicsSimpleTextItem(char, self)
    chev.setBrush(QBrush(color))
    chev.setPos(NODE_WIDTH - 16, 5)
    self.setToolTip(self._function_entry_tooltip(color))
```

### 7.2 더블클릭 동작 — 현 동작 유지

기존 `_try_emit_enter_subgraph`는 `subgraph is not None` 조건 그대로 (subgraph 있는 노드만 진입). 사용자가 명확화한 대로 현 진입 동작은 정상이므로 변경 없음. 단 함수 참조(`RigVMFunctionReferenceNode`)가 진입 불가하면 chevron 색이 안내(노랑)으로 사용자가 그 사실을 즉시 인지.

### 7.3 툴팁 보강

함수 진입 불가 상태(노랑 chevron) 노드에 툴팁:

```python
if state[1] == QColor("#FFD700"):
    self.setToolTip(
        "함수 참조 — 함수 본문이 외부 파일에 있음.\n"
        "에셋 폴더 열기로 함수 라이브러리 등록 필요."
    )
```

### 7.4 테스트

- CollapseNode with subgraph → chevron 녹색 (#90EE90)
- FunctionReferenceNode without subgraph → chevron 노랑 (#FFD700) + 안내 툴팁
- CollapseNode without subgraph (드물) → chevron 회색 (#888888)
- 일반 노드 → chevron 없음

---

## 8. 슬라이스 의존

| 슬라이스 | 의존 | 진입 |
|---|---|---|
| g1 F21 direction | 없음 | 1차 |
| g2 F22 exec sort | 없음 | 1차 (병렬) |
| g3 F24 elide | 없음 | 1차 (병렬) |
| g4 F25/26/27 visual | 없음 (items.py 공유) | 1차 (g1과 같은 파일 — 머지 순서 코디네이션) |
| g5 F28 entry guidance | 없음 (items.py 공유) | 1차 (g1·g4와 같은 파일) |

g1·g4·g5 모두 items.py 만짐 — 1차 병렬 디스패치 후 implementer rebase 처리. g2·g3는 다른 파일 — 완전 독립.

---

## 9. Out-of-scope

- `TemplateNotation` 기반 Dispatch 노드 파라미터 재정렬 (F23 완전 해결) — g1+g2 효과 검증 후 별도 슬라이스 검토
- 함수 진입 시 자동 폴더 검색 (현재 디렉터리 + 부모 디렉터리 글로벌) — 다음 cycle FEAT
- 데이터 link 애니메이션 — 산만함, 실행만 적용
- **미니맵 "그래프 위치 메뉴"에서 함수 진입 정상화** — 사용자가 별개 이슈로 보고. 미니맵 navigation handler 분리 검토 필요. 다음 사이클 별도 슬라이스 후보

---

## 10. 자율 루프

본 batch는 사용자 직접 트리거 (autonomous loop 종료 후 새 사이클). 5 슬라이스 디스패치 → 머지 → improver 사이클. 시간 budget 자유.
