# t3dgraph batch ⑫ — 정리 (autonomous loop) 설계 문서

- **작성일**: 2026-06-02
- **상태**: 사용자 위임 자율 루프 (cycle 2) — 직접 디스패치
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **이전 사이클**: batch ⑪ (`d125fc8`~h5 머지 후)

---

## 1. 범위

batch ⑨~⑪ 누적 B-시리즈·boundary leak·작은 패턴 정리. 11 finding을 4 슬라이스로 묶음.

| 슬라이스 | 출처 | 한 줄 |
|---|---|---|
| **c1** boundaries | ⑪-A1 + ⑪-A2 + ⑪-A3 | LayoutOverrides·AssetResolver public API + DeprecationWarning stacklevel |
| **c2** persistent state cleanup | ⑪-B1 + ψ-B2 + ⑪-B2 + FEAT-50 | ViewState 팩토리 + from_dict v2 정규화 + migration toast |
| **c3** values structs | α-A1 + α-B1 | _walk_struct cycle guard + Struct 메서드 |
| **c4** misc | ψ-B1 + ο-B1 + υ-B1 | Pin.iter_paths + _from_toml_bytes + QSignalBlocker with |

본 문서 밖: FEAT-46/48/49 (unresolved 도크 + state export/import) → 별도 batch ⑬ 후보. 오래된 ζ-λ B-시리즈는 시간 허락 시 추가 흡수.

---

## 2. PRESERVE-ALL

전 슬라이스 행동 무변경 리팩터/UX 보조. 모델·노드 보존 ✅.

---

## 3. c1 — Boundary public API

### 3.1 LayoutOverrides.graph_keys (⑪-A1)

`src/t3dgraph/core/app/layout_overrides.py`:

```python
def graph_keys(self) -> Iterable[str]:
    """현재 보관 중인 graph_key 목록. 직렬화/cleanup용 public."""
    return self._by_graph.keys()
```

`main_window._save_persistent_state`에서 `self.layout_overrides._by_graph.keys()` → `self.layout_overrides.graph_keys()`.

### 3.2 AssetResolver.extract_target_path (⑪-A2)

`src/t3dgraph/core/t3d/resolver.py`:

`_extract_target_path` → `extract_target_path` (public 리네임). 호환을 위해 `_extract_target_path = extract_target_path` 별칭 한 사이클 유지.

`interpreter.py`의 호출부 `self._resolver._extract_target_path(...)` → `self._resolver.extract_target_path(...)`.

추가 검토: `resolve_function_reference`가 `tuple[T3DObject | None, str | None]`(객체 + 사유)을 돌려주게 하면 인터프리터는 public 메서드 외에 plugin internals 안 만져도 됨. 본 슬라이스에 포함.

```python
def resolve_function_reference(self, ref_path: str) -> tuple[T3DObject | None, str | None]:
    """반환: (객체 또는 None, 사유 메시지). 사유 None이면 정상 해결."""
    target = self.extract_target_path(ref_path)
    if target is None:
        return None, "ref unparseable"
    # ... 기존 룩업
    return obj, None or (None, "asset not found in resolver")
```

호출부도 같이 갱신.

### 3.3 DeprecationWarning stacklevel (⑪-A3)

`controller.py::_call_interpreter_factory`의 `stacklevel=2` → `stacklevel=3` (호출자의 호출자 = 사용자 코드).

### 3.4 테스트

- `LayoutOverrides.graph_keys()` 단위
- `AssetResolver.extract_target_path` public 호출 가능
- `resolve_function_reference` 튜플 반환 + 인터프리터 회귀
- DeprecationWarning이 호출자 모듈을 가리키는지 (stacklevel=3 검증)

---

## 4. c2 — Persistent state cleanup + migration toast

### 4.1 ViewState.from_graph_state 팩토리 (⑪-B1 + ψ-B2)

`src/t3dgraph/core/app/view_state.py`:

```python
@classmethod
def from_graph_state(cls, gs: "GraphState") -> "ViewState":
    vs = cls(
        connected_pins_only=gs.connected_pins_only,
        fan_in_highlight=gs.fan_in_highlight,
    )
    vs.expanded_pin_paths = set(gs.expanded_pin_paths)
    vs.hidden_node_types = set(gs.hidden_node_types)
    return vs
```

(필요 시 `set_*` setter 사용으로 전환 가능 — 다만 expanded_pin_paths·hidden_node_types는 직접 set 대입이 더 간결. setter 우회 finding은 setter 부재가 아닌 패턴 일관성 — 팩토리 내부에 한정되어 OK.)

`_apply_persistent_state`의 두 분기를 다음으로 단순화:

```python
def _apply_persistent_state(self, path: str) -> None:
    state, error = load_state(path)
    if error:
        self.statusBar().showMessage(f"영속 상태 로드 실패: {error}", 10000)
    for key, gs in state.per_graph.items():
        for node, (x, y) in gs.node_positions.items():
            self.layout_overrides.set(key, node, x, y)
        self._view_states[key] = ViewState.from_graph_state(gs)
    self._rebuild_scene()
    self._sync_toolbar_to_current_view_state()
```

### 4.2 from_dict v2 정규화 (⑪-B2)

`persistent_state.PersistentState.from_dict`가 v1 입력을 항상 v2 표현으로 정규화:

```python
@classmethod
def from_dict(cls, data: dict) -> "PersistentState":
    version = data.get("schema_version", _SCHEMA_VERSION)
    if version == 1:
        # v1을 v2로 정규화 — 단일 키 ""("currrent") 부여
        gs = GraphState(
            node_positions={...},  # 기존 v1 필드에서 추출
            ...
        )
        return cls(schema_version=2, per_graph={"": gs})
    if version != _SCHEMA_VERSION:
        return cls()
    return cls(schema_version=version, per_graph={...})
```

호출부 `_apply_persistent_state`는 v1 분기 제거 가능. 다만 "" 키가 들어오면 현재 graph_key로 흡수해야 — 흡수 로직만 유지.

```python
def _apply_persistent_state(self, path: str) -> None:
    state, error = load_state(path)
    if error:
        self.statusBar().showMessage(...)
    # "" 키(v1 잔재)를 현재 graph_key로 이관
    if "" in state.per_graph:
        state.per_graph[self._current_graph_key()] = state.per_graph.pop("")
    for key, gs in state.per_graph.items():
        ...
```

### 4.3 schema migration toast (FEAT-50)

`load_state`가 (state, error, migrated: bool) 세 요소 또는 별도 플래그를 돌려주게. 또는 `error` 메시지에 "v1 → v2 변환" 사유를 statusBar 4초 메시지로 전달.

간단한 방법: `from_dict`가 v1 변환했으면 결과 객체에 `_migrated_from_v1: bool` 표시. MainWindow가 이를 보고 statusBar 알림.

```python
@dataclass
class PersistentState:
    ...
    migrated_from_v1: bool = field(default=False, compare=False)


# from_dict:
if version == 1:
    state = cls(..., migrated_from_v1=True)
    return state

# MainWindow:
if state.migrated_from_v1:
    self.statusBar().showMessage(
        "영속 상태 v1 → v2 자동 변환됨 (저장 시 v2로 덮어쓰기)", 4000
    )
```

`compare=False`로 dataclass equality에서 제외 — 기존 테스트(라운드트립 equals) 보존.

### 4.4 .bak 백업 통일 + 회전 (⑪h5-A1/A2/B1)

`load_state`의 모든 폴백 분기(JSON decode·schema mismatch·구조 오류)를 같은 `.bak` 경로로 통일. 백업 충돌 시 timestamp suffix로 회전:

```python
def _backup_corrupted(p: Path) -> Path:
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak.{ts}")
    try:
        p.replace(bak)
    except OSError:
        return p   # 백업 실패 시 그대로
    return bak


def load_state(file_path: str) -> tuple[PersistentState, str | None]:
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState(), None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        bak = _backup_corrupted(p)
        return PersistentState(), f"JSON 해독 실패 — {bak.name}으로 백업: {exc}"
    version = data.get("schema_version", _SCHEMA_VERSION)
    if version not in (1, _SCHEMA_VERSION):
        bak = _backup_corrupted(p)
        return PersistentState(), (
            f"미지원 schema_version={version} — {bak.name}으로 백업"
        )
    try:
        return PersistentState.from_dict(data), None
    except (KeyError, TypeError, ValueError) as exc:
        bak = _backup_corrupted(p)
        return PersistentState(), f"구조 오류 — {bak.name}으로 백업: {exc}"
```

### 4.5 테스트

- `ViewState.from_graph_state` 단위
- `from_dict` v1 입력 → 정규화된 v2 결과 + `migrated_from_v1=True`
- MainWindow toast 표시 (v1 파일 로드 시)
- schema_version 미지원 → `.bak.{ts}` 생성
- `from_dict` 구조 오류 → `.bak.{ts}` 생성
- 백업 충돌 시 ts 다른 파일 두 개 보존

---

## 5. c3 — Values 구조 helpers + cycle guard

### 5.1 `_walk_struct_find_key` cycle/depth guard (α-A1)

`src/t3dgraph/plugins/rigvm/interpreter.py`의 `_walk_struct_find_key`에 `max_depth=8` 인자 + 재귀 시 감소:

```python
def _walk_struct_find_key(self, value, target_key: str, max_depth: int = 8) -> str | None:
    if max_depth <= 0 or not isinstance(value, Struct):
        return None
    for k, v in value.items:
        if k == target_key:
            text = _text(v)
            if text:
                return text
        if isinstance(v, Struct):
            found = self._walk_struct_find_key(v, target_key, max_depth - 1)
            if found:
                return found
    return None
```

### 5.2 `Struct.find_path` + `Struct.find_first` 메서드 (α-B1)

`src/t3dgraph/core/t3d/values.py`:

```python
@dataclass(frozen=True)
class Struct(Value):
    items: list[tuple[str, "Value"]]

    def find_path(self, *keys: str) -> "Value | None":
        cur: Value | None = self
        for key in keys:
            if not isinstance(cur, Struct):
                return None
            cur = next((v for k, v in cur.items if k == key), None)
            if cur is None:
                return None
        return cur

    def find_first(self, target_key: str, *, max_depth: int = 8) -> "Value | None":
        if max_depth <= 0:
            return None
        for k, v in self.items:
            if k == target_key:
                return v
            if isinstance(v, Struct):
                found = v.find_first(target_key, max_depth=max_depth - 1)
                if found is not None:
                    return found
        return None
```

인터프리터의 `_walk_struct`/`_walk_struct_find_key` → `Struct.find_path`/`find_first` 사용:

```python
def _extract_lib_node_path_from_header(self, obj):
    header = obj.properties.get("ReferencedFunctionHeader")
    if not isinstance(header, Struct):
        return None
    known = header.find_path("LibraryPointer", "LibraryNodePath")
    if known is not None:
        return _text(known)
    found = header.find_first("LibraryNodePath")
    return _text(found) if found else None
```

`_walk_struct`/`_walk_struct_find_key` 메서드 자체 제거.

### 5.3 테스트

- `Struct.find_path` 단위 (정상 경로 + 누락 시 None)
- `Struct.find_first` 단위 (얕은 매치 + 깊은 매치 + cycle/cap)
- F20 헤더 폴백 회귀

---

## 6. c4 — Misc cleanup

### 6.1 Pin.iter_paths 메서드 (ψ-B1)

`src/t3dgraph/core/base/graph_model.py`:

```python
@dataclass
class Pin:
    ...
    def iter_paths(self, prefix: str) -> Iterator[str]:
        path = f"{prefix}.{self.name}"
        yield path
        for sp in self.subpins:
            yield from sp.iter_paths(path)
```

`GraphModel.iter_pin_paths`는 단순 위임:

```python
def iter_pin_paths(self, *, node_name: str | None = None) -> Iterator[str]:
    nodes = ([n for n in self.nodes if n.name == node_name]
             if node_name else self.nodes)
    for node in nodes:
        for pin in node.pins:
            yield from pin.iter_paths(node.name)
```

모듈-level `_walk_pin_paths` 제거.

### 6.2 PinColorTable._from_toml_bytes (ο-B1)

`src/t3dgraph/core/app/pin_colors.py`:

```python
@classmethod
def _from_toml_bytes(cls, data: bytes) -> "PinColorTable":
    parsed = tomllib.loads(data.decode("utf-8"))
    palette = {k: QColor(v) for k, v in parsed.get("palette", {}).items()}
    bucket = dict(parsed.get("bucket", {}))
    special = parsed.get("special", {})
    return cls(
        palette=palette,
        bucket=bucket,
        exec_marker=special.get("exec_marker", "ExecuteContext"),
        array_marker=special.get("array_marker", "TArray<"),
    )

@classmethod
def load(cls) -> "PinColorTable":
    user_file = cls._user_dir() / "pin_colors.toml"
    if not user_file.exists():
        ...
    return cls._from_toml_bytes(user_file.read_bytes())

@classmethod
def _load_bundled_defaults(cls) -> "PinColorTable":
    return cls._from_toml_bytes(cls._bundle_path().read_bytes())
```

### 6.3 QSignalBlocker with (υ-B1)

`main_window._sync_toolbar_to_current_view_state`:

```python
def _sync_toolbar_to_current_view_state(self) -> None:
    vs = self.current_view_state()
    for mode_id, value in (
        ("connected_only", vs.connected_pins_only),
        ("fan_in_highlight", vs.fan_in_highlight),
    ):
        action = self._view_mode_actions.get(mode_id)
        if action is None:
            continue
        with QSignalBlocker(action):
            action.setChecked(value)
```

### 6.4 테스트

- `Pin.iter_paths` 단위
- `PinColorTable._from_toml_bytes` 단위
- toolbar sync 회귀 (기존 테스트로 충분)

---

## 7. 슬라이스 의존

| 슬라이스 | 의존 | 진입 |
|---|---|---|
| c1 boundaries | 없음 | 1차 (병렬) |
| c2 persistent | h5 머지 후 | 1차 (h5 머지 후) |
| c3 values | 없음 | 1차 (병렬) |
| c4 misc | 없음 | 1차 (병렬) |

c2가 main_window.py·persistent_state.py 공유하므로 h5 머지 필수.

---

## 8. 회귀 가드

기존 487+ 테스트 100% 통과 필수. 추가 ~20+ 신규 테스트(단위·통합).

---

## 9. Out-of-scope

- 오래된 ζ-λ B-시리즈 (시간 허락 시 후속 batch)
- FEAT-46/48/49 (unresolved 도크 + export/import) → batch ⑬ 후보
- 신규 사용자 피드백

---

## 10. 자율 루프 컨텍스트

`memory/project_autonomous_loop_2026_06_01.md` cycle 2. h5 머지 + h5 improver 사이클 직후 c1·c3·c4 병렬 디스패치, c2는 h5 머지 시점에 같이 진입. batch ⑫ 마감 후 시간 허락 시 batch ⑬(FEAT 통합) 또는 사용자 보고 후 종료.
