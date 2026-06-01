# batch ⑫ c4 — Misc Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 작은 cleanup 3건 — `Pin.iter_paths` 메서드(ψ-B1), `PinColorTable._from_toml_bytes` 헬퍼(ο-B1), `QSignalBlocker with` 컨텍스트 매니저(υ-B1).

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-12-cleanup-design.md` §6

**Pre-condition:** master `0d5892c` 이상. c1/c2/c3와 병렬.

---

## Task 1: Pin.iter_paths 메서드 (ψ-B1)

**Files:**
- Modify: `src/t3dgraph/core/base/graph_model.py`
- Modify: `tests/base/test_graph_model_find_pin.py`

- [ ] **Step 1: 테스트**

```python
def test_pin_iter_paths_top_only() -> None:
    p = Pin(name="A", cpp_type=None, direction=None)
    assert list(p.iter_paths("N1")) == ["N1.A"]


def test_pin_iter_paths_with_subpins() -> None:
    sub = Pin(name="X", cpp_type=None, direction=None)
    p = Pin(name="P", cpp_type=None, direction=None, subpins=[sub])
    paths = list(p.iter_paths("N1"))
    assert paths == ["N1.P", "N1.P.X"]


def test_pin_iter_paths_deep() -> None:
    leaf = Pin(name="L", cpp_type=None, direction=None)
    mid = Pin(name="M", cpp_type=None, direction=None, subpins=[leaf])
    top = Pin(name="T", cpp_type=None, direction=None, subpins=[mid])
    paths = list(top.iter_paths("N1"))
    assert paths == ["N1.T", "N1.T.M", "N1.T.M.L"]
```

- [ ] **Step 2: 구현**

`graph_model.py`:

```python
@dataclass
class Pin:
    ...
    def iter_paths(self, prefix: str) -> Iterator[str]:
        """이 핀 + 서브핀의 전체 경로 yield."""
        path = f"{prefix}.{self.name}"
        yield path
        for sp in self.subpins:
            yield from sp.iter_paths(path)
```

`GraphModel.iter_pin_paths` 위임:

```python
def iter_pin_paths(self, *, node_name: str | None = None) -> Iterator[str]:
    nodes = ([n for n in self.nodes if n.name == node_name]
             if node_name else self.nodes)
    for node in nodes:
        for pin in node.pins:
            yield from pin.iter_paths(node.name)
```

모듈-level `_walk_pin_paths` 제거.

- [ ] **Step 3: 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/base/test_graph_model_find_pin.py src/t3dgraph/core/base/graph_model.py
git commit -m "refactor(base): Pin.iter_paths method (ψ-B1)"
```

---

## Task 2: PinColorTable._from_toml_bytes 헬퍼 (ο-B1)

**Files:**
- Modify: `src/t3dgraph/core/app/pin_colors.py`
- Modify: `tests/app/test_pin_colors.py`

- [ ] **Step 1: 테스트**

```python
def test_from_toml_bytes_parses_minimal() -> None:
    data = (
        b'[palette]\nbool = "#A02020"\ndefault = "#C8C878"\n'
        b'[bucket]\nbool = "bool"\n'
        b'[special]\nexec_marker = "ExecuteContext"\narray_marker = "TArray<"\n'
    )
    table = PinColorTable._from_toml_bytes(data)
    assert table.resolve("bool").color.name().upper() == "#A02020"


def test_load_uses_from_toml_bytes(tmp_path, monkeypatch) -> None:
    """load → _from_toml_bytes 위임 (중복 코드 제거 확인)."""
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = PinColorTable.load()
    # 정상 로드 검증 — 본 finding은 로직 변경 없음
    assert table.resolve("bool").color.name().upper() == "#A02020"
```

- [ ] **Step 2: 구현**

`pin_colors.py`:

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
        user_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cls._bundle_path(), user_file)
    return cls._from_toml_bytes(user_file.read_bytes())

@classmethod
def _load_bundled_defaults(cls) -> "PinColorTable":
    return cls._from_toml_bytes(cls._bundle_path().read_bytes())
```

- [ ] **Step 3: 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_pin_colors.py src/t3dgraph/core/app/pin_colors.py
git commit -m "refactor(app): PinColorTable._from_toml_bytes shared parser (ο-B1)"
```

---

## Task 3: QSignalBlocker `with` 컨텍스트 매니저 (υ-B1)

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 변경**

`_sync_toolbar_to_current_view_state` 본문:

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

- [ ] **Step 2: 회귀**

Run: `pytest tests -v`
Expected: τ 슬라이스 테스트 그대로 통과.

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/core/app/main_window.py
git commit -m "refactor(app): QSignalBlocker context manager in toolbar sync (υ-B1)"
```

## 완료 후

ψ-B1, ο-B1, υ-B1 해소. batch ⑫ 완전 마감 후보.
