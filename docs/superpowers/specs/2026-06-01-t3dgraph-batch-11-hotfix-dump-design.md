# t3dgraph batch ⑪ — 핫픽스 묶음 (autonomous loop) 설계 문서

- **작성일**: 2026-06-01
- **상태**: 사용자 위임 자율 루프 (2026-06-01T14:25Z 시작, 상한 22:25Z) — 직접 디스패치
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **이전 사이클**: batch ⑩ (`a0b7328`, 473 tests)

---

## 1. 범위

batch ⑩ improver findings 잔여 핫픽스 5건. 모두 작은 surgical fix. 슬라이스 5개로 분할하여 병렬 디스패치.

| 슬라이스 | 출처 | 한 줄 요약 | 우선 |
|---|---|---|---|
| **h1** | ω-A1 | 영속 상태 multi-subgraph 키 손실 — `_view_states`·`layout_overrides`의 모든 키 직렬화 | 1 |
| **h2** | α-A2 | F20 ref_path 정보 손실 — `_extract_target_path` None 시 원본 ref_path 보존 등재 | 2 |
| **h3** | ψ-A1 | `InterpreterFactory` backward break — spec/CHANGELOG 마이그레이션 노트 + `inspect.signature` 한 사이클 deprecation 폴백 복구 | 3 |
| **h4** | ο-A2 | 팔레트 다이얼로그가 `__init__` 중 호출 — `QTimer.singleShot(0, ...)`로 지연 | 4 |
| **h5** | ω-A2 | schema mismatch·JSON decode 실패 silent reset — statusBar + 로그 경고 + `.bak` 백업 | 5 |

본 문서 밖 (deferred): 정리 batch(α-A1/B1, ψ-B1/B2, ο-B1, υ-B1) → batch ⑫. FEAT-46~49 통합 → 별도 batch.

---

## 2. PRESERVE-ALL 불변식

| 슬라이스 | 영향 | 보존 |
|---|---|---|
| h1 | 영속 데이터 풍부화 — 다른 키도 저장 | ✅ |
| h2 | 진단 데이터 보강 — `external_refs_unresolved` 정보 추가 | ✅ |
| h3 | 호환성 회복 — 외부 플러그인 동작 회복 | ✅ |
| h4 | UX 타이밍 — 동작 동일 | ✅ |
| h5 | 사용자 경고 — 데이터 손실 가시화 | ✅ |

---

## 3. h1 — Multi-subgraph 영속 키 보존 (ω-A1)

### 3.1 디자인

`_save_persistent_state`가 모든 `_view_states`·`layout_overrides`의 키를 직렬화. 로드 시 모든 키 복원.

### 3.2 자료구조 확장

`PersistentState`에 dict 필드 추가 (현재 단일 그래프 상태에서 multi로):

```python
@dataclass
class PersistentState:
    schema_version: int = 2     # 1 → 2 bump
    # 기존 필드 — 호환을 위해 현재 활성 키의 단축 표현 유지
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)
    # 신규 — graph_key별 상태 전체
    per_graph: dict[str, "GraphState"] = field(default_factory=dict)


@dataclass
class GraphState:
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)
```

호환성: schema_version=1 로드 시 기존 단일 키 필드를 `per_graph[""]`(루트 키)로 흡수.

### 3.3 MainWindow 저장 변경

```python
def _save_persistent_state(self) -> None:
    if self._current_file_path is None:
        return
    per_graph = {}
    # 모든 활성 graph_key 순회
    all_keys = set(self._view_states.keys()) | set(
        self.layout_overrides._by_graph.keys()  # 또는 public iter
    )
    for key in all_keys:
        vs = self._view_states.get(key, ViewState())
        per_graph[key] = GraphState(
            node_positions=dict(self.layout_overrides.all_for_graph(key)),
            expanded_pin_paths=list(vs.expanded_pin_paths),
            connected_pins_only=vs.connected_pins_only,
            fan_in_highlight=vs.fan_in_highlight,
            hidden_node_types=list(vs.hidden_node_types),
        )
    state = PersistentState(schema_version=2, per_graph=per_graph)
    save_state(self._current_file_path, state)
```

### 3.4 로드 변경

```python
def _apply_persistent_state(self, path: str) -> None:
    state = load_state(path)
    # schema_version=1 호환 — 단일 키를 현재 graph_key로 흡수
    if state.schema_version == 1 and not state.per_graph:
        current_key = self._current_graph_key()
        state.per_graph[current_key] = GraphState(
            node_positions=state.node_positions,
            expanded_pin_paths=state.expanded_pin_paths,
            connected_pins_only=state.connected_pins_only,
            fan_in_highlight=state.fan_in_highlight,
            hidden_node_types=state.hidden_node_types,
        )
    for key, gs in state.per_graph.items():
        for node, (x, y) in gs.node_positions.items():
            self.layout_overrides.set(key, node, x, y)
        vs = ViewState(
            expanded_pin_paths=set(gs.expanded_pin_paths),
            connected_pins_only=gs.connected_pins_only,
            fan_in_highlight=gs.fan_in_highlight,
            hidden_node_types=set(gs.hidden_node_types),
        )
        self._view_states[key] = vs
    self._rebuild_scene()
    self._sync_toolbar_to_current_view_state()
```

### 3.5 테스트

- multi-subgraph 시뮬레이션: 두 graph_key에 다른 ViewState/layout_overrides 설정 → save → load → 모두 복원
- schema_version=1 호환: 옛 JSON 직접 작성 → load → 단일 키 흡수 확인
- 빈 per_graph도 정상 로드

---

## 4. h2 — F20 ref_path 보존 (α-A2)

### 4.1 디자인

`_extract_target_path`가 None 반환 시(비표준 ref 표기) 원본 `ref_path`를 `external_refs_unresolved`에 명시 등재. `(header parse failed)` 한 줄 통합 대신 정확한 ref 정보 노출.

### 4.2 인터프리터 변경

`_add_node`의 FunctionReferenceNode 처리 블록 갱신:

```python
ref_path_raw = _text(obj.properties.get("ReferencedNode"))
if not ref_path_raw:
    ref_path_raw = self._extract_lib_node_path_from_header(obj)
if not ref_path_raw:
    diagnostics.external_refs_unresolved.append(
        f"{obj.name or '?'} (header parse failed)"
    )
    return
# resolver 룩업 시도
if self._resolver is not None:
    extracted = self._resolver._extract_target_path(ref_path_raw)
    if extracted is None:
        # 정규식·prefix 매칭 실패 — 원본 ref_path 보존
        diagnostics.external_refs_unresolved.append(
            f"{obj.name or '?'} (ref unparseable: {ref_path_raw})"
        )
        return
    ext_obj = self._resolver.resolve_function_reference(ref_path_raw)
    if ext_obj is None:
        diagnostics.external_refs_unresolved.append(ref_path_raw)
    else:
        # ... 기존 subgraph 연결
        ...
else:
    diagnostics.external_refs_unresolved.append(ref_path_raw)
```

또는 더 간단히 — `resolve_function_reference` 내부에서 None 반환 시 호출부가 ref_path를 등재하도록 하면 됨. 현 코드가 이미 그렇게 동작 — 다만 `_extract_target_path` None 케이스는 호출부에서 추가 메타 없이 `ref_path`만 들어감. h2는 원본 추가 표시(`(ref unparseable: ...)`)로 충분.

### 4.3 테스트

- 비표준 ref_path(quoted·colon 모두 없음) → unresolved에 "ref unparseable" 메타 포함 등재
- 정상 ref_path → unresolved에 원본 그대로(메타 없음)

---

## 5. h3 — InterpreterFactory 마이그레이션 노트 + deprecation 폴백 (ψ-A1)

### 5.1 디자인

`controller.py`의 `interpreter_factory(resolver=...)` 직접 호출에서 한 사이클 deprecation 폴백 복구:

```python
import inspect
import warnings

def _call_factory(factory, *, resolver):
    sig = inspect.signature(factory)
    if "resolver" in sig.parameters:
        return factory(resolver=resolver)
    warnings.warn(
        f"InterpreterFactory '{factory!r}' does not accept resolver= keyword. "
        f"Update factory signature to InterpreterFactory protocol "
        f"(see contracts.py). Backward-compat fallback will be removed in batch ⑫.",
        DeprecationWarning, stacklevel=2,
    )
    return factory()
```

`docs/superpowers/specs/2026-05-19-t3d-rig-graph-tool-design.md`에 마이그레이션 노트 짧게 추가 — "외부 플러그인은 `InterpreterFactory(resolver: AssetResolver | None = None)` 프로토콜 따를 것".

### 5.2 테스트

- `resolver` 없는 factory → DeprecationWarning + 정상 호출
- `resolver` 있는 factory → 직접 호출 (warning 없음)

---

## 6. h4 — 팔레트 다이얼로그 타이밍 (ο-A2)

### 6.1 디자인

`MainWindow.__init__`의 즉시 `QMessageBox.warning(...)`을 `QTimer.singleShot(0, ...)`로 메인 이벤트 루프 첫 반복 시점으로 지연.

### 6.2 변경

```python
def __init__(self) -> None:
    QMainWindow.__init__(self)
    ...
    try:
        self.pin_colors = PinColorTable.load()
        self._palette_load_exc = None
    except (tomllib.TOMLDecodeError, ValueError, OSError) as exc:
        self.pin_colors = PinColorTable._load_bundled_defaults()
        self._palette_load_exc = exc
    ...
    # 메인 이벤트 루프 첫 반복 시점에 다이얼로그 표시
    if self._palette_load_exc is not None:
        QTimer.singleShot(0, self._show_palette_load_failure_dialog)

def _show_palette_load_failure_dialog(self) -> None:
    exc = self._palette_load_exc
    ...
    reply = QMessageBox.warning(self, "팔레트 로드 실패", msg,
                                QMessageBox.Yes | QMessageBox.No)
    if reply == QMessageBox.Yes:
        PinColorTable.reset_user_file()
        self.pin_colors = PinColorTable.load()
        self._rebuild_scene()
    else:
        self.statusBar().showMessage(
            f"팔레트 로드 실패 — 디폴트로 폴백: {exc}", 10000)
```

기존 `_handle_palette_load_failure` 메서드는 `_show_palette_load_failure_dialog`로 이름 변경 + 시그니처 단순화 (이미 self.pin_colors 결정됐으므로 반환값 X).

### 6.3 테스트

- ο의 기존 테스트들이 그대로 작동하는지 확인 (qtbot로 `QTimer` 발사 처리)
- `_show_palette_load_failure_dialog`가 `__init__` 중 호출되지 않음 검증

---

## 7. h5 — 영속 상태 silent reset 가시화 (ω-A2)

### 7.1 디자인

`load_state`가 폴백할 때(decode error / schema mismatch) 사용자에게 통지. 빈 `PersistentState` 반환은 유지하되, 호출부(MainWindow)가 사유를 알 수 있도록 `LoadResult` 또는 메타 보조 반환.

간단한 방법: `load_state(path) -> tuple[PersistentState, str | None]` — 두 번째 요소가 에러 사유. `None`이면 정상.

또는 더 간단: 로드 실패 시 손상 파일을 `.bak`로 백업하고 statusBar 메시지.

```python
def load_state(file_path: str) -> tuple[PersistentState, str | None]:
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState(), None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        bak = p.with_suffix(p.suffix + ".bak")
        try:
            p.replace(bak)
        except OSError:
            pass
        return PersistentState(), f"JSON 해독 실패 — {bak.name}으로 백업: {exc}"
    version = data.get("schema_version", _SCHEMA_VERSION)
    if version != _SCHEMA_VERSION and version != 1:
        # 1은 호환(h1으로 흡수), 그 외는 미래 버전 폴백
        return PersistentState(), f"미지원 schema_version={version} — 무시"
    try:
        return PersistentState.from_dict(data), None
    except (KeyError, TypeError, ValueError) as exc:
        return PersistentState(), f"구조 오류 — 무시: {exc}"
```

`MainWindow._apply_persistent_state`:

```python
state, error = load_state(path)
if error:
    self.statusBar().showMessage(f"영속 상태 로드 실패 — 디폴트로 폴백: {error}", 10000)
...
```

기존 호출부 시그니처 변경 — 다른 테스트가 `load_state` 직접 호출하면 같이 갱신.

### 7.2 테스트

- 손상 JSON → `.bak` 생성 + 빈 state + error 메시지
- 미지원 schema_version → 빈 state + error 메시지 (백업 없음)
- 정상 → state + None

---

## 8. 슬라이스 분할 + 진입

| 슬라이스 | 의존 | 진입 |
|---|---|---|
| h1 ω-A1 multi-key | 없음 | 1차 (병렬) |
| h2 α-A2 ref_path | 없음 | 1차 (병렬) |
| h3 ψ-A1 deprecation | 없음 | 1차 (병렬) |
| h4 ο-A2 dialog timing | 없음 | 1차 (병렬) |
| h5 ω-A2 silent reset | h1 머지 후 (schema_version=2 호환 코드 충돌) | 2차 |

h1과 h5 모두 `persistent_state.py`를 만지므로 직렬화. h2·h3·h4는 서로·h1과 다른 파일 — 완전 병렬 가능.

---

## 9. PRESERVE-ALL + 회귀 가드

- 모든 슬라이스 행동 보강 / UI 추가만 — 데이터 손실 0
- 기존 473 테스트 100% 통과 필수
- h1 schema_version=1 → 2 호환 로직이 핵심 회귀 가드

---

## 10. Out-of-scope

- 정리 batch ⑫ (α-A1/B1, ψ-B1/B2, ο-B1, υ-B1)
- FEAT-46/48/49 (도크 + export/import) 별도 batch
- 신규 사용자 피드백 (F14 deferred 유지)

---

## 11. 자율 루프 컨텍스트

본 batch는 사용자 위임 [autonomous loop](`memory/project_autonomous_loop_2026_06_01.md`) 1차 산출물. 디스패치 직후 ψ·ω 머지 시점부터 사이클 시작 시간에 의존해 자율 진행. 완성도 도달 시(예: h1~h5 모두 머지 + improver 사이클) 또는 22:25Z 마감 시 중지.
