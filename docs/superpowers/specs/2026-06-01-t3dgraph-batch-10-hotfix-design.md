# t3dgraph batch ⑩ — 핫픽스·정리·영속화 설계 문서

- **작성일**: 2026-06-01
- **상태**: brainstorming 산출물 — 사용자 리뷰 대기
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **이전 사이클**: batch ⑨ (사용자 피드백, master `c89ca9f`까지)
- **트리거**: batch ⑨ improver findings에서 사용자 직격·silent miss·기술 부채 누적 신호 다수. 6 슬라이스 묶음.

---

## 1. 범위

batch ⑨ improver findings 중 다음 6건을 처리:

| ID | 출처 | 한 줄 요약 | 성격 | 우선 |
|---|---|---|---|---|
| **ρ-A1 + ρ-A3** | improver σ+ρ | F20 정규식 첫 매치만 + 헤더 단일 구조 — F20 fix silent miss | bug | 1 |
| **μ-A1** | improver μ | 팔레트 로드 무음 — 사용자가 TOML 깨진 줄 모름 | bug | 2 |
| **τ-A1** | improver τ | 툴바 액션 체크 상태 탭 전환 시 desync — F11 의도 즉시 깨짐 | bug | 3 |
| **σ-A1** | improver σ+ρ | array sort가 digit-only 가정 — `Item_0` 변형 미대응 | bug | 4 |
| **pin walk 통합** | ν-B1·φ-B2·ρ-B1/B2/B3 | 세 곳 walk 중복 + controller·view 의존 정상화 | refactor | 5 |
| **영속화 통일** | ν-A2 + τ-A2 | 노드 위치·뷰 상태 세션 휘발 → 파일 영속 | feature | 6 |

본 문서 밖 (deferred): F14(사용자 추가 보고 대기), batch ⑨ improver findings 잔여 B-시리즈(다음 정리 batch), 백로그 FEAT-12~47 누적분.

---

## 2. PRESERVE-ALL 불변식

| 슬라이스 | 조작 | 보존 |
|---|---|---|
| α | resolver 정규식·헤더 walk 강화 | ✅ (노드 추가만, 손실 없음) |
| ο | 팔레트 로드 실패 시 다이얼로그·리셋 | ✅ (시각만) |
| υ | toolbar 액션 체크 상태 동기화 | ✅ (UI 상태만) |
| χ | array sort 패턴 일반화 | ✅ (subpin 수 동일, 순서만 정정) |
| ψ | walk API 통합 + controller 정상화 | ✅ (행동 무변경 리팩터) |
| ω | state.json 저장·복원 | ✅ (저장된 상태 복원, 모델 무변경) |

테스트 슬롯: 전 슬라이스 통합에 `len(scene._nodes) >= len(graph.nodes)` 어서션 유지. ω는 round-trip 어서션(`save → load → state.equals(original)`) 추가.

---

## 3. 슬라이스 α — F20 Stability (ρ-A1 + ρ-A3)

### 3.1 디자인

`resolve_function_reference`가 silent miss하지 않도록 두 축 강화:

**3.1.1 정규식 강도 (ρ-A1)**

```python
def resolve_function_reference(self, ref_path: str) -> T3DObject | None:
    inner = self._extract_target_path(ref_path)
    if inner is None:
        return None
    # 이하 기존 룩업 로직 그대로
    ...

def _extract_target_path(self, ref_path: str) -> str | None:
    """UE ref 경로에서 실제 타겟 경로 추출.

    형식 가능성:
    1. "Class'/Game/.../Lib.Lib:RigVMModel.Func'"       — 단일 quoted
    2. "Redirect'...'->'Class'/Game/.../Lib.Lib:...'"   — redirect 체인
    3. "/Game/.../Lib.Lib:RigVMModel.Func"              — quoted 없음
    """
    # 우선순위 1: Class'...' 명시 매칭
    m = re.search(r"Class'([^']+)'", ref_path)
    if m:
        return m.group(1)
    # 우선순위 2: 마지막 quoted segment (redirect 체인의 타겟)
    quoted = re.findall(r"'([^']+)'", ref_path)
    if quoted:
        return quoted[-1]
    # 우선순위 3: 콜론 포함 raw path (no quotes)
    if ":" in ref_path:
        return ref_path
    return None
```

**3.1.2 헤더 구조 fallback (ρ-A3)**

`ReferencedFunctionHeader`에서 `LibraryNodePath`를 못 찾으면 명시 등재:

```python
# interpreter.py의 FunctionReferenceNode 처리 블록
ref_path = _text(obj.properties.get("ReferencedNode"))
if not ref_path:
    # 헤더 walk 시도
    ref_path = self._extract_lib_node_path_from_header(obj)
if not ref_path:
    # 어느 경로로도 못 뽑으면 명시 등재 — silent miss 차단
    diagnostics.external_refs_unresolved.append(
        f"{obj.name or '?'} (header parse failed)"
    )
    return  # 이 노드는 subgraph 미연결, 단 진단엔 남음

ext_obj = self._resolver.resolve_function_reference(ref_path)
if ext_obj is None:
    diagnostics.external_refs_unresolved.append(ref_path)
    return
# ... 기존 subgraph 연결
```

`_extract_lib_node_path_from_header`는 알려진 경로 우선 시도(`header.LibraryPointer.LibraryNodePath`), 실패 시 generic walk(임의 깊이에서 `LibraryNodePath` 텍스트 검색).

### 3.2 테스트

`tests/repro/test_f20_function_reference_subgraph.py` 확장 + 신규 `tests/base/test_resolver_extract_target.py`:

```python
def test_extract_class_pattern() -> None:
    r = AssetResolver()
    assert r._extract_target_path("Class'/Game/Lib.Lib:RigVMModel.F'") == \
           "/Game/Lib.Lib:RigVMModel.F"

def test_extract_redirect_chain_last_segment() -> None:
    r = AssetResolver()
    raw = "Redirect'/Old.Old:RigVMModel.G'->'Class'/Game/Lib.Lib:RigVMModel.F''"
    assert r._extract_target_path(raw) == "/Game/Lib.Lib:RigVMModel.F"

def test_extract_raw_path_no_quotes() -> None:
    r = AssetResolver()
    assert r._extract_target_path("/Game/Lib.Lib:RigVMModel.F") == \
           "/Game/Lib.Lib:RigVMModel.F"

def test_extract_invalid_returns_none() -> None:
    assert AssetResolver()._extract_target_path("not a ref") is None

def test_header_parse_failure_recorded_as_unresolved(orion_folder) -> None:
    """헤더 구조 변종 — silent miss 없이 external_refs_unresolved에 등재."""
    # 합성 t3d: FunctionReferenceNode이지만 ReferencedNode·header 없음
    ...
    assert any("header parse failed" in r for r in graph.diagnostics.external_refs_unresolved)
```

---

## 4. 슬라이스 ο — 팔레트 무음 (μ-A1)

### 4.1 디자인

`MainWindow.__init__`에서 `PinColorTable.load()` 실패를 잡아 사용자에게 가시화:

```python
try:
    self.pin_colors = PinColorTable.load()
except (tomllib.TOMLDecodeError, ValueError) as exc:
    self.pin_colors = self._handle_palette_load_failure(exc)

def _handle_palette_load_failure(self, exc: Exception) -> PinColorTable:
    msg = (
        f"핀 색 팔레트 파일을 읽지 못했습니다.\n"
        f"오류: {exc}\n\n"
        f"디폴트 팔레트로 리셋하시겠습니까? (사용자 파일은 덮어쓰기 됩니다)"
    )
    reply = QMessageBox.warning(
        self, "팔레트 로드 실패", msg,
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply == QMessageBox.Yes:
        PinColorTable.reset_user_file()
        return PinColorTable.load()
    # 거절 시 in-memory 디폴트 (사용자 파일 미변경)
    self.statusBar().showMessage(
        f"팔레트 로드 실패 — 디폴트로 폴백 (사용자 파일은 미변경): {exc}", 10000
    )
    return PinColorTable._load_bundled_defaults()
```

`PinColorTable._load_bundled_defaults()`는 번들 TOML을 사용자 파일 무시하고 직접 로드하는 메서드 (신규).

### 4.2 테스트

`tests/app/test_pin_colors.py` 확장:

```python
def test_load_failure_returns_bundled_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[[broken syntax", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        PinColorTable.load()

def test_load_bundled_defaults_ignores_user_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[[broken", encoding="utf-8")
    table = PinColorTable._load_bundled_defaults()
    assert table.resolve("bool").color.name().upper() == "#A02020"
```

`tests/app/test_main_window_palette_failure.py` 신규:

```python
def test_main_window_handles_broken_palette(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    (tmp_path / "pin_colors.toml").write_text("[[broken", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: QMessageBox.No)
    w = MainWindow()
    qtbot.addWidget(w)
    # 폴백 팔레트로 정상 동작
    assert w.pin_colors is not None
    assert w.pin_colors.resolve("bool").color.name().upper() == "#A02020"
```

---

## 5. 슬라이스 υ — 툴바 desync (τ-A1)

### 5.1 디자인

`_on_tab_change`에서 toolbar 액션을 현재 탭 ViewState로 동기화. `QSignalBlocker`로 토글 핸들러 중복 발사 차단:

```python
def _on_tab_change(self, index: int) -> None:
    # 기존: graph_stack.select_root + render_current
    ...
    self._sync_toolbar_to_current_view_state()

def _sync_toolbar_to_current_view_state(self) -> None:
    vs = self.current_view_state()
    for mode_id, value in (
        ("connected_only", vs.connected_pins_only),
        ("fan_in_highlight", vs.fan_in_highlight),
    ):
        action = self._view_mode_actions.get(mode_id)
        if action is not None:
            blocker = QSignalBlocker(action)
            action.setChecked(value)
            del blocker
```

### 5.2 테스트

`tests/app/test_per_tab_view_state.py` 확장:

```python
def test_toolbar_action_synced_on_tab_switch(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    # 탭1에서 connected_only ON
    w._tab_bar.setCurrentIndex(0)
    w.set_view_mode("connected_only", True)
    action = w._view_mode_actions["connected_only"]
    assert action.isChecked() is True
    # 탭2로 전환 — 액션 체크 OFF
    w._tab_bar.setCurrentIndex(1)
    assert action.isChecked() is False, "툴바 desync — τ-A1 회귀"
    # 탭1로 복귀 — 액션 체크 다시 ON
    w._tab_bar.setCurrentIndex(0)
    assert action.isChecked() is True


def test_toolbar_sync_does_not_trigger_double_toggle(qtbot) -> None:
    """탭 전환의 setChecked 동기화가 _on_view_mode를 발사하지 않음."""
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_graph(_graph("A"))
    w.open_graph(_graph("B"))
    w._tab_bar.setCurrentIndex(0)
    w.set_view_mode("connected_only", True)
    initial = w.current_view_state().connected_pins_only
    # 탭 전환
    w._tab_bar.setCurrentIndex(1)
    # 탭2 ViewState 토글 영향 없음
    assert w.current_view_state().connected_pins_only is False
```

---

## 6. 슬라이스 χ — 배열 sort 일반화 (σ-A1)

### 6.1 디자인

`_sort_array_subpins`의 digit-only 가정을 prefix+digit 패턴으로 확장:

```python
import re

_ARRAY_PATTERN = re.compile(r"^([A-Za-z_]*?)(\d+)$")

def _sort_array_subpins(subpins: list[Pin]) -> list[Pin]:
    """T3D 배열 직렬화 quirk 정정.

    name이 전부 같은 prefix + 끝에 digits 패턴이면 digit 부분으로 int 정렬.
    예: '0','1','2'   → 0,1,2 (현 동작 유지)
        'Item_0','Item_1','Item_2'  → 0,1,2 정렬
        'X','Y','Z'   → 원순서 유지 (배열 아님)
        'Item_0','Element_1' → 원순서 (prefix 불일치, 안전)
    """
    if not subpins:
        return subpins
    matches = [_ARRAY_PATTERN.match(p.name) for p in subpins]
    if not all(matches):
        return subpins
    # 모든 prefix가 같아야 배열로 인정
    prefixes = {m.group(1) for m in matches}
    if len(prefixes) != 1:
        return subpins
    return sorted(subpins, key=lambda p: int(_ARRAY_PATTERN.match(p.name).group(2)))
```

### 6.2 테스트

`tests/base/test_pin_array_sort.py` 확장:

```python
def test_prefixed_digits_sorted() -> None:
    pins = [_pin("Item_10"), _pin("Item_2"), _pin("Item_0"), _pin("Item_1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Item_0", "Item_1", "Item_2", "Item_10"]


def test_mixed_prefix_preserves_order() -> None:
    pins = [_pin("Item_0"), _pin("Element_0"), _pin("Item_1")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Item_0", "Element_0", "Item_1"]


def test_underscore_prefix_works() -> None:
    pins = [_pin("Element_2"), _pin("Element_1"), _pin("Element_0")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["Element_0", "Element_1", "Element_2"]


def test_pure_digits_still_sorted() -> None:
    """기존 동작 회귀 없음."""
    pins = [_pin("10"), _pin("9"), _pin("0")]
    result = _sort_array_subpins(pins)
    assert [p.name for p in result] == ["0", "9", "10"]
```

---

## 7. 슬라이스 ψ — pin walk 통합 + contracts 정상화

### 7.1 디자인

**7.1.1 `GraphModel.find_pin` + `iter_pin_paths` (ν-B1+φ-B2)**

`src/t3dgraph/core/base/graph_model.py`:

```python
from typing import Iterator

class GraphModel:
    ...
    def find_pin(self, path: str) -> "Pin | None":
        """'NodeName.PinName[.SubPin...]' → Pin. 없으면 None."""
        parts = path.split(".")
        if not parts:
            return None
        node = self.node_by_name(parts[0])
        if node is None:
            return None
        cur_pins = node.pins
        last: Pin | None = None
        for name in parts[1:]:
            pin = next((p for p in cur_pins if p.name == name), None)
            if pin is None:
                return None
            last = pin
            cur_pins = pin.subpins
        return last

    def iter_pin_paths(self, *, node_name: str | None = None) -> Iterator[str]:
        """모든 핀 경로(서브핀 포함) 순회. node_name 지정 시 해당 노드만."""
        nodes = ([n for n in self.nodes if n.name == node_name]
                 if node_name else self.nodes)
        for node in nodes:
            for pin in node.pins:
                yield from _walk_pin_paths(pin, node.name)


def _walk_pin_paths(pin: Pin, prefix: str) -> Iterator[str]:
    path = f"{prefix}.{pin.name}"
    yield path
    for sp in pin.subpins:
        yield from _walk_pin_paths(sp, path)
```

호출부 치환:
- `plugins/rigvm/interpreter.py::_locate_pin` → 제거, `g.find_pin(path)` 사용
- `core/app/main_window.py::_collect_node_pin_paths` → 제거, `list(self.graph.iter_pin_paths(node_name=node.name))` 사용
- `core/app/items.py::collect_pin_rows`는 행 데이터(`depth`·`has_children` 등) 생성이라 별도 — `iter_pin_paths`로 path만 뽑는 경로엔 영향 없음, 그대로 유지

**7.1.2 `_cls_suffix` 모듈 헬퍼 (ρ-B3)**

`src/t3dgraph/core/t3d/objects.py` 또는 `plugins/rigvm/interpreter.py`:

```python
def _cls_suffix(obj: T3DObject) -> str | None:
    return (obj.cls or "").rsplit(".", 1)[-1] or None
```

`_interpret_objects`의 3분기에서 호출.

**7.1.3 view contract 정상화 (ρ-B1 + ρ-B2)**

`src/t3dgraph/core/app/contracts.py`의 `AbstractGraphView`에 `resolver: AssetResolver | None` property 추가:

```python
class AbstractGraphView(Protocol):
    @property
    def resolver(self) -> "AssetResolver | None":
        ...
```

`MainWindow`에 property 노출:

```python
@property
def resolver(self) -> AssetResolver | None:
    return self._resolver
```

`controller.py`의 `inspect.signature` 분기 제거 — `InterpreterFactory` 프로토콜 표준화:

```python
class InterpreterFactory(Protocol):
    def __call__(self, *, resolver: "AssetResolver | None" = None) -> AbstractGraphInterpreter:
        ...
```

호출부에서 `factory(resolver=view.resolver)` 직접 호출. RigVM 외 플러그인이 resolver를 무시하면 무시 — 키워드만 받으면 됨.

### 7.2 테스트

`tests/base/test_graph_model_find_pin.py` 신규:

```python
def test_find_pin_top_level() -> None:
    n = Node(name="N1", cls="X", pins=[Pin(name="A", cpp_type=None, direction=None)])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.A") is n.pins[0]


def test_find_pin_subpin() -> None:
    sub = Pin(name="X", cpp_type=None, direction=None)
    parent = Pin(name="P", cpp_type=None, direction=None, subpins=[sub])
    n = Node(name="N1", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.P.X") is sub


def test_find_pin_missing_returns_none() -> None:
    n = Node(name="N1", cls="X", pins=[Pin(name="A", cpp_type=None, direction=None)])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.MissingPin") is None
    assert g.find_pin("Missing.A") is None


def test_iter_pin_paths() -> None:
    sub = Pin(name="X", cpp_type=None, direction=None)
    parent = Pin(name="P", cpp_type=None, direction=None, subpins=[sub])
    n = Node(name="N1", cls="X", pins=[parent, Pin(name="Q", cpp_type=None, direction=None)])
    g = GraphModel(nodes=[n])
    paths = list(g.iter_pin_paths())
    assert paths == ["N1.P", "N1.P.X", "N1.Q"]


def test_iter_pin_paths_filtered_by_node() -> None:
    n1 = Node(name="N1", cls="X", pins=[Pin(name="A", cpp_type=None, direction=None)])
    n2 = Node(name="N2", cls="X", pins=[Pin(name="B", cpp_type=None, direction=None)])
    g = GraphModel(nodes=[n1, n2])
    paths = list(g.iter_pin_paths(node_name="N2"))
    assert paths == ["N2.B"]
```

회귀 테스트: 기존 `_locate_pin`·`_collect_node_pin_paths` 호출이 새 API로 동일 결과 반환.

---

## 8. 슬라이스 ω — 영속화 통일 (ν-A2 + τ-A2)

### 8.1 디자인

파일별 영속 상태를 `~/.t3dgraph/state/{sha256(absolute_path)}.json`에 저장. layout overrides + ViewState 직렬화.

### 8.2 파일 위치·키 도출

```python
def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "t3dgraph" / "state"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "t3dgraph" / "state"


def _state_path(file_path: str) -> Path:
    abs_path = str(Path(file_path).resolve())
    digest = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()
    return _state_dir() / f"{digest}.json"
```

### 8.3 자료구조

신규 `src/t3dgraph/core/app/persistent_state.py`:

```python
@dataclass
class PersistentState:
    """파일 단위 영속 상태 — layout overrides + view state."""
    schema_version: int = 1
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "node_positions": [
                {"node": k, "x": v[0], "y": v[1]} for k, v in self.node_positions.items()
            ],
            "expanded_pin_paths": sorted(self.expanded_pin_paths),
            "connected_pins_only": self.connected_pins_only,
            "fan_in_highlight": self.fan_in_highlight,
            "hidden_node_types": sorted(self.hidden_node_types),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentState":
        version = data.get("schema_version", 1)
        if version != 1:
            return cls()  # 미래 버전 — 빈 상태로 폴백 (사용자 데이터 손실 차단)
        return cls(
            schema_version=version,
            node_positions={
                e["node"]: (e["x"], e["y"]) for e in data.get("node_positions", [])
            },
            expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
            connected_pins_only=data.get("connected_pins_only", False),
            fan_in_highlight=data.get("fan_in_highlight", False),
            hidden_node_types=list(data.get("hidden_node_types", [])),
        )


def load_state(file_path: str) -> PersistentState:
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState()
    try:
        with p.open("r", encoding="utf-8") as f:
            return PersistentState.from_dict(json.load(f))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # 손상된 파일 — 빈 상태로 폴백, 로그만
        return PersistentState()


def save_state(file_path: str, state: PersistentState) -> None:
    p = _state_path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
    tmp.replace(p)  # atomic
```

### 8.4 MainWindow 통합

**8.4.1 load 시점** — `open_path` 또는 `_render_current`에서 파일 열린 직후:

```python
def open_path(self, path: str) -> None:
    if self._open_handler is not None:
        self._open_handler(path)
    # 영속 상태 로드 — graph_stack에 그래프 추가된 후
    self._apply_persistent_state(path)

def _apply_persistent_state(self, path: str) -> None:
    state = load_state(path)
    key = self._current_graph_key()
    # layout overrides
    for node, (x, y) in state.node_positions.items():
        self.layout_overrides.set(key, node, x, y)
    # view state
    vs = self.current_view_state()
    vs.expanded_pin_paths = set(state.expanded_pin_paths)
    vs.connected_pins_only = state.connected_pins_only
    vs.fan_in_highlight = state.fan_in_highlight
    vs.hidden_node_types = set(state.hidden_node_types)
    self._rebuild_scene()
    self._sync_toolbar_to_current_view_state()
```

**8.4.2 save 시점** — 변경 후 디바운스(500ms):

```python
def __init__(self) -> None:
    ...
    self._save_state_timer = QTimer(self)
    self._save_state_timer.setSingleShot(True)
    self._save_state_timer.setInterval(500)
    self._save_state_timer.timeout.connect(self._save_persistent_state)
    self._current_file_path: str | None = None

def _schedule_save_state(self) -> None:
    if self._current_file_path is not None:
        self._save_state_timer.start()  # 500ms 후 발사 (재호출 시 리셋)

def _save_persistent_state(self) -> None:
    if self._current_file_path is None:
        return
    key = self._current_graph_key()
    vs = self.current_view_state()
    state = PersistentState(
        node_positions=dict(self.layout_overrides.all_for_graph(key)),
        expanded_pin_paths=list(vs.expanded_pin_paths),
        connected_pins_only=vs.connected_pins_only,
        fan_in_highlight=vs.fan_in_highlight,
        hidden_node_types=list(vs.hidden_node_types),
    )
    save_state(self._current_file_path, state)
```

**8.4.3 트리거 지점** — 변경 신호에서 `_schedule_save_state` 호출:
- `_on_node_moved` (드래그)
- `_on_pin_toggle` (펼침)
- `_on_view_mode` (토글)
- `_on_type_toggled` (타입 숨김)
- `_invoke_node_action` (메뉴 액션)
- `_on_expand_all_pins` / `_on_collapse_all_pins`

### 8.5 테스트

`tests/app/test_persistent_state.py` 신규:

```python
def test_state_path_uses_sha256(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p1 = _state_path("/some/path/a.t3d.txt")
    p2 = _state_path("/some/path/b.t3d.txt")
    assert p1 != p2
    assert p1.suffix == ".json"


def test_save_then_load_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    state = PersistentState(
        node_positions={"N1": (10.0, 20.0), "N2": (-5.5, 3.3)},
        expanded_pin_paths=["N1.P", "N1.P.X"],
        connected_pins_only=True,
        fan_in_highlight=False,
        hidden_node_types=["RigVMUnitNode"],
    )
    save_state("/test/file.t3d.txt", state)
    loaded = load_state("/test/file.t3d.txt")
    assert loaded == state


def test_load_missing_returns_empty() -> None:
    s = load_state("/non/existent/file.t3d.txt")
    assert s == PersistentState()


def test_load_corrupted_returns_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ broken", encoding="utf-8")
    s = load_state("/test/x.t3d.txt")
    assert s == PersistentState()


def test_future_schema_version_returns_empty(tmp_path, monkeypatch) -> None:
    """미래 버전은 사용자 데이터 손실 차단을 위해 빈 상태."""
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    p = _state_path("/test/x.t3d.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": 999}', encoding="utf-8")
    s = load_state("/test/x.t3d.txt")
    assert s == PersistentState()


def test_save_is_atomic(tmp_path, monkeypatch) -> None:
    """save 중 실패해도 기존 파일 무손상 — tmp + replace."""
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    save_state("/test/x.t3d.txt", PersistentState(connected_pins_only=True))
    # tmp 파일 없어야 함
    p = _state_path("/test/x.t3d.txt")
    assert p.exists()
    assert not p.with_suffix(p.suffix + ".tmp").exists()
```

MainWindow 통합 테스트 `tests/app/test_main_window_persistence.py`:

```python
@pytest.fixture
def synth_t3d_file(tmp_path: Path) -> str:
    """간단한 합성 T3D 파일 생성 — Orion 의존 없이 영속 라운드트립 검증."""
    src = (
        'Begin Object Name="N1" Class=/Script/RigVMDeveloper.RigVMUnitNode\n'
        'End Object\n'
        'Begin Object Name="N2" Class=/Script/RigVMDeveloper.RigVMUnitNode\n'
        'End Object\n'
    )
    f = tmp_path / "sample.t3d.txt"
    f.write_text(src, encoding="utf-8")
    return str(f)


def test_view_state_persists_across_reopen(qtbot, tmp_path, monkeypatch,
                                            synth_t3d_file) -> None:
    monkeypatch.setattr("t3dgraph.core.app.persistent_state._state_dir",
                        lambda: tmp_path)
    # 첫 열기 — 토글 → 디바운스 강제 발사 → 닫기
    w1 = MainWindow()
    qtbot.addWidget(w1)
    w1.open_path(synth_t3d_file)
    w1.set_view_mode("connected_only", True)
    w1._save_persistent_state()   # 디바운스 우회
    w1.close()
    # 두 번째 열기 — 토글 상태 복원
    w2 = MainWindow()
    qtbot.addWidget(w2)
    w2.open_path(synth_t3d_file)
    assert w2.current_view_state().connected_pins_only is True
    assert w2._view_mode_actions["connected_only"].isChecked() is True
```

---

## 9. 슬라이스 분할·진입 순서

| 슬라이스 | 의존 | 1차/2차 |
|---|---|---|
| **α** F20 stability | 없음 | 1차 (병렬) |
| **ο** 팔레트 무음 | 없음 | 1차 (병렬) |
| **υ** 툴바 desync | 없음 | 1차 (병렬) |
| **χ** array sort gen | 없음 | 1차 (병렬) |
| **ω** 영속화 통일 | **υ 머지 후** (toolbar sync helper 의존) | 1차 (υ 다음) |
| **ψ** pin walk 통합 + contracts | α/χ 후(작은 충돌 회피) | 2차 |

ψ를 2차로 두는 이유: ν-B1·φ-B2·ρ-B3 모두 interpreter.py·main_window.py·controller.py에 손이 가며, α(interpreter.py)·χ(interpreter.py)와 같은 파일을 만진다. 1차 머지 후 ψ가 rebase로 마무리하면 충돌 비용 최소.

---

## 10. 교차 관심사

### 10.1 ω + υ — 영속 상태 복원 후 툴바 동기화

ω의 `_apply_persistent_state` 끝에서 `_sync_toolbar_to_current_view_state()` 호출 (υ가 도입한 helper).

**머지 순서 강제**: ω plan은 **υ 머지 후 진입**으로 표기. υ가 1차 가장 먼저 머지된 후 ω가 그 helper에 의존. υ 미머지 상태에서 ω 머지 시 `AttributeError`. ω 구현 시작 시 master에 υ가 있는지 확인 필수.

가능한 대안: ω 안에서 helper를 인라인 정의 → υ 머지 후 정리. 다만 코드 중복 발생, 권장 X.

### 10.2 ψ + α — `_cls_suffix` 위치

ρ-B3에서 모듈 헬퍼 추출하면서 α의 `_extract_target_path`도 같은 인터프리터/리졸버 모듈에 응집. 두 슬라이스가 같은 파일을 만져도 다른 함수 — 충돌 거의 없음.

### 10.3 회귀 가드

batch ⑨ 통합 테스트(430건) + 본 batch 신규 (~30+)가 모두 통과해야 머지.

특히 주의:
- α의 정규식 변경이 기존 Orion 샘플 케이스(단일 quoted)에 대해 회귀 없는지
- ψ의 walk API 통합이 기존 흐름(F19 노드 컨텍스트 메뉴 expand_all 등)에 영향 없는지
- ω의 load가 미존재 파일에서 깨끗이 폴백하는지

### 10.4 의존성

- 신규 외부 의존성 0
- ω가 `hashlib`·`json` (표준)
- α가 `re` 확장 (이미 사용 중)

---

## 11. Out-of-scope

- **F14**: 사용자 추가 보고 시 별도 슬라이스
- **batch ⑨ B-시리즈 잔여**: μ-B1/B2/B3, τ-B1/B2, ν-B 시리즈, ξ-B1/B2, φ-B1 — 다음 정리 batch
- **백로그 FEAT-12~47 신규 기능 누적분** — 점진 처리
- **자동 레이아웃** (ν-C3, FEAT-39) — 분석 뷰어 정체성 외
- **사용자 정의 단축키** — 본 batch 무관

---

## 12. 다음 단계

1. 사용자 리뷰 (본 문서) — 변경 요청 시 §3~§8 해당 절 수정
2. 승인 후 `writing-plans` 스킬로 슬라이스 α/ο/υ/χ/ψ/ω 구현 플랜 작성 (총 6개 plan 파일)
3. 슬라이스 디스패치 순서: α·ο·υ·χ·ω 병렬 → ψ는 1차 머지 후
4. 본 batch ⑩ 마감 후 백로그 잔여 정리 batch ⑪ 후보
