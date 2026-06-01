# batch ⑨ μ (mu) — 핀 시각 어휘 (F10 + F12) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 핀 dot에 타입별 색을 입히고(F10), 구조체/배열 핀 행에 disclosure indicator(▶/▼)를 추가해 펼침 토글을 발견 가능하게 만든다(F12).

**Architecture:** TOML 팔레트 + 3계층 룩업(special → bucket → palette)을 `PinColorTable`이 담당. `MainWindow`가 인스턴스 1개를 보유, `scene.populate(..., pin_colors=...)`로 주입. `NodeItem`이 핀 dot brush·outline 결정과 disclosure indicator 그리기 + 화살표 영역 단일 클릭 토글 담당.

**Tech Stack:** Python 3.11 `tomllib`(신규 의존성 0), PySide6 (`QGraphicsEllipseItem`, `QGraphicsSimpleTextItem`), pytest + pytest-qt.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-1-vis-rendering-design.md` §3·§4

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/resources/__init__.py` | 신규 (패키지 마커) |
| `src/t3dgraph/core/app/resources/pin_colors.toml` | 신규 (디폴트 팔레트) |
| `src/t3dgraph/core/app/pin_colors.py` | 신규 (`PinColorTable`, `ResolvedColor`) |
| `src/t3dgraph/core/app/items.py` | 수정 (`PinRow.has_children`, `NodeItem` 핀 색·▶/▼·클릭 토글) |
| `src/t3dgraph/core/app/scene.py` | 수정 (`populate` 시그니처에 `pin_colors`) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`PinColorTable.load()` 보유, `_rebuild_scene`/`_render_current`에 주입, "팔레트 리셋" 메뉴) |
| `tests/app/test_pin_colors.py` | 신규 (PinColorTable 단위) |
| `tests/app/test_items_disclosure.py` | 신규 (NodeItem disclosure + 클릭) |
| `pyproject.toml` | 수정 (`package_data`에 resources/*.toml 포함) |

---

## Task 1: 디폴트 팔레트 TOML

**Files:**
- Create: `src/t3dgraph/core/app/resources/__init__.py`
- Create: `src/t3dgraph/core/app/resources/pin_colors.toml`

- [ ] **Step 1: `resources` 패키지 마커 생성**

`src/t3dgraph/core/app/resources/__init__.py`:

```python
"""핀 색 팔레트 등 리소스 파일 보관 디렉터리."""
```

- [ ] **Step 2: 디폴트 TOML 작성**

`src/t3dgraph/core/app/resources/pin_colors.toml`:

```toml
# t3dgraph 핀 색 팔레트 — UE Blueprint 컨벤션
# 사용자는 이 파일을 OS 설정 디렉터리로 복사한 사본을 편집한다.
# "팔레트 리셋" 메뉴는 사용자 파일을 본 번들로 덮어쓴다.

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
bool         = "bool"
float        = "float"
double       = "float"
int8         = "int"
int16        = "int"
int32        = "int"
int64        = "int"
uint8        = "int"
uint16       = "int"
uint32       = "int"
uint64       = "int"
FName        = "name"
FString      = "string"
FText        = "string"
FVector      = "struct"
FVector2D    = "struct"
FVector4     = "struct"
FRotator     = "struct"
FQuat        = "struct"
FTransform   = "struct"
FMatrix      = "struct"
FColor       = "struct"
FLinearColor = "struct"
FRigElementKey = "struct"
FRigControlValue = "struct"

[special]
exec_marker  = "ExecuteContext"
array_marker = "TArray<"
```

- [ ] **Step 3: pyproject.toml에 package_data 추가**

`pyproject.toml` `[tool.setuptools.packages.find]` 다음에 추가:

```toml
[tool.setuptools.package-data]
"t3dgraph.core.app.resources" = ["*.toml"]
```

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/app/resources/ pyproject.toml
git commit -m "feat(app): default pin_colors.toml palette (F10 prep)"
```

---

## Task 2: `PinColorTable` — 룩업 단위 테스트 (TDD)

**Files:**
- Create: `tests/app/test_pin_colors.py`
- Create: `src/t3dgraph/core/app/pin_colors.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_pin_colors.py`:

```python
"""PinColorTable 단위 테스트 — TOML 룩업·폴백."""
from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtGui import QColor

from t3dgraph.core.app.pin_colors import PinColorTable, ResolvedColor


@pytest.fixture
def bundled_table(tmp_path: Path, monkeypatch) -> PinColorTable:
    """번들 디폴트를 임시 사용자 dir로 로드."""
    monkeypatch.setattr(PinColorTable, "_user_dir", classmethod(lambda cls: tmp_path))
    return PinColorTable.load()


def test_bucket_lookup_bool(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("bool")
    assert r.color == QColor("#A02020")
    assert r.is_array is False


def test_bucket_lookup_int32(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("int32")
    assert r.color == QColor("#1FBEB6")


def test_bucket_lookup_struct(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("FRotator")
    assert r.color == QColor("#5B8FF9")


def test_special_exec_marker(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("FRigVMExecuteContext")
    assert r.color == QColor("#FFFFFF")


def test_special_array_inner_lookup(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("TArray<bool>")
    assert r.color == QColor("#A02020")
    assert r.is_array is True


def test_special_array_struct_inner(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("TArray<FRigElementKey>")
    assert r.color == QColor("#5B8FF9")
    assert r.is_array is True


def test_unknown_falls_back_to_default(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve("FNotInBucket")
    assert r.color == QColor("#C8C878")
    assert r.is_array is False


def test_none_falls_back_to_default(bundled_table: PinColorTable) -> None:
    r = bundled_table.resolve(None)
    assert r.color == QColor("#C8C878")


def test_first_load_copies_bundle_to_user_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir", classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    assert not user_file.exists()
    PinColorTable.load()
    assert user_file.exists()
    # 번들과 바이트 동일
    bundle = PinColorTable._bundle_path()
    assert user_file.read_bytes() == bundle.read_bytes()


def test_reset_user_file_overwrites(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir", classmethod(lambda cls: tmp_path))
    PinColorTable.load()
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text("[palette]\ndefault = \"#000000\"\n", encoding="utf-8")
    PinColorTable.reset_user_file()
    bundle = PinColorTable._bundle_path()
    assert user_file.read_bytes() == bundle.read_bytes()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/app/test_pin_colors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 't3dgraph.core.app.pin_colors'`

- [ ] **Step 3: `PinColorTable` 구현**

`src/t3dgraph/core/app/pin_colors.py`:

```python
"""핀 색 팔레트 룩업 — TOML 기반 3계층 (special → bucket → palette)."""
from __future__ import annotations
import os
import shutil
import sys
import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class ResolvedColor:
    """핀 색 룩업 결과. 배열 핀은 외곽선 변형 신호."""
    color: QColor
    is_array: bool


class PinColorTable:
    """TOML 팔레트에서 cpp_type → 색을 룩업한다.

    런타임은 사용자 파일(`_user_dir() / pin_colors.toml`)만 읽는다.
    첫 호출 시 사용자 파일이 없으면 번들에서 풀 카피한다.
    """

    def __init__(
        self,
        *,
        palette: dict[str, QColor],
        bucket: dict[str, str],
        exec_marker: str,
        array_marker: str,
    ) -> None:
        self._palette = palette
        self._bucket = bucket
        self._exec_marker = exec_marker
        self._array_marker = array_marker

    @classmethod
    def load(cls) -> "PinColorTable":
        user_file = cls._user_dir() / "pin_colors.toml"
        if not user_file.exists():
            user_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(cls._bundle_path(), user_file)
        with user_file.open("rb") as f:
            data = tomllib.load(f)
        palette = {k: QColor(v) for k, v in data.get("palette", {}).items()}
        bucket = dict(data.get("bucket", {}))
        special = data.get("special", {})
        return cls(
            palette=palette,
            bucket=bucket,
            exec_marker=special.get("exec_marker", "ExecuteContext"),
            array_marker=special.get("array_marker", "TArray<"),
        )

    @classmethod
    def reset_user_file(cls) -> Path:
        """사용자 파일을 번들로 덮어쓰고 경로를 반환한다."""
        user_file = cls._user_dir() / "pin_colors.toml"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cls._bundle_path(), user_file)
        return user_file

    def resolve(self, cpp_type: str | None) -> ResolvedColor:
        if cpp_type is None:
            return ResolvedColor(color=self._palette["default"], is_array=False)
        # special — array: 내부 타입 재귀
        if cpp_type.startswith(self._array_marker):
            inner = cpp_type[len(self._array_marker):].rstrip(">").rstrip()
            inner_resolved = self.resolve(inner)
            return ResolvedColor(color=inner_resolved.color, is_array=True)
        # special — exec
        if self._exec_marker in cpp_type:
            return ResolvedColor(color=self._palette.get("exec", self._palette["default"]),
                                 is_array=False)
        # bucket → palette
        key = self._bucket.get(cpp_type)
        if key is not None and key in self._palette:
            return ResolvedColor(color=self._palette[key], is_array=False)
        return ResolvedColor(color=self._palette["default"], is_array=False)

    @classmethod
    def _user_dir(cls) -> Path:
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            return Path(base) / "t3dgraph"
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        return base / "t3dgraph"

    @classmethod
    def _bundle_path(cls) -> Path:
        with resources.as_file(
            resources.files("t3dgraph.core.app.resources") / "pin_colors.toml"
        ) as p:
            return Path(p)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/app/test_pin_colors.py -v`
Expected: 10 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_pin_colors.py src/t3dgraph/core/app/pin_colors.py
git commit -m "feat(app): PinColorTable TOML lookup (F10)"
```

---

## Task 3: `PinRow.has_children` — disclosure 표시 가능 여부

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: `PinRow`에 `has_children` 필드 추가**

`src/t3dgraph/core/app/items.py` `@dataclass(frozen=True) class PinRow:` 블록을 다음으로 교체:

```python
@dataclass(frozen=True)
class PinRow:
    pin: Pin
    path: str
    depth: int
    has_dot: bool
    has_children: bool   # subpins가 비어있지 않으면 True (F12 disclosure 표시)
```

- [ ] **Step 2: `collect_pin_rows` 갱신**

`collect_pin_rows` 함수 내부 `rows.append(PinRow(...))` 두 곳을 다음과 같이 변경:

```python
rows.append(PinRow(pin=pin, path=path, depth=depth,
                   has_dot=True, has_children=bool(pin.subpins)))
```

그리고 children_added 처리 부분:

```python
if my_idx is not None and children_added:
    cur = rows[my_idx]
    rows[my_idx] = PinRow(pin=cur.pin, path=cur.path,
                          depth=cur.depth, has_dot=False,
                          has_children=cur.has_children)
```

- [ ] **Step 3: 기존 테스트 회귀 확인**

Run: `pytest tests/app -v -k "not pin_colors and not disclosure"`
Expected: 기존 테스트 전부 통과 (PinRow 시그니처 변경이 호출부에 영향 없는지 확인). 만약 PinRow를 직접 인스턴스화하는 기존 테스트가 있으면 `has_children=False` 인자 추가.

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/app/items.py
git commit -m "feat(app): PinRow.has_children for disclosure marker (F12 prep)"
```

---

## Task 4: `NodeItem` — 핀 dot 색 적용 (F10)

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: `NodeItem.__init__` 시그니처 확장**

`items.py`의 `NodeItem.__init__` 시그니처를 다음과 같이 변경:

```python
def __init__(
    self, node: Node, *,
    connected_paths: frozenset[str] = frozenset(),
    connected_only: bool = False,
    expanded_paths: frozenset[str] = frozenset(),
    highlighted: bool = False,
    pin_colors: "PinColorTable | None" = None,
):
```

상단에 import 추가:

```python
from .pin_colors import PinColorTable
```

- [ ] **Step 2: dot 그리기 로직에 색 적용**

`if row.has_dot:` 블록을 다음으로 교체:

```python
if row.has_dot:
    dot = QGraphicsEllipseItem(
        mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
    if pin_colors is not None:
        resolved = pin_colors.resolve(row.pin.cpp_type)
        dot.setBrush(QBrush(resolved.color))
        if resolved.is_array:
            dot.setPen(QPen(QColor(40, 40, 40), 1.5))
        else:
            dot.setPen(QPen(Qt.NoPen))
    else:
        dot.setBrush(QBrush(QColor(200, 200, 120)))
        dot.setPen(QPen(Qt.NoPen))
```

`pin_colors=None` 폴백을 두는 이유: 단위 테스트에서 NodeItem 직접 생성 시 색표 없이도 안전 (기존 노랑 유지).

- [ ] **Step 3: 기존 테스트 회귀 확인**

Run: `pytest tests/app -v -k "not pin_colors and not disclosure"`
Expected: 통과 (NodeItem 호출부는 모두 pin_colors 미지정 → 노랑 fallback).

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/app/items.py
git commit -m "feat(app): NodeItem pin dot color via PinColorTable (F10)"
```

---

## Task 5: Disclosure indicator (▶/▼) 그리기 (F12)

**Files:**
- Create: `tests/app/test_items_disclosure.py`
- Modify: `src/t3dgraph/core/app/items.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/app/test_items_disclosure.py`:

```python
"""F12 disclosure indicator — ▶/▼ 표시·클릭 토글."""
from __future__ import annotations
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsSimpleTextItem
from PySide6.QtCore import QPointF

from t3dgraph.core.base.graph_model import Node, Pin
from t3dgraph.core.app.items import NodeItem


def _node_with_struct() -> Node:
    sub_a = Pin(name="X", cpp_type="float", direction="Input")
    sub_b = Pin(name="Y", cpp_type="float", direction="Input")
    parent = Pin(name="P", cpp_type="FVector", direction="Input",
                 subpins=[sub_a, sub_b])
    leaf = Pin(name="Q", cpp_type="bool", direction="Input")
    return Node(name="N", cls="Test", pins=[parent, leaf])


def _arrows_in(item: NodeItem) -> list[str]:
    return [
        c.text() for c in item.childItems()
        if isinstance(c, QGraphicsSimpleTextItem) and c.text() in ("▶", "▼")
    ]


def test_arrow_appears_for_pin_with_subpins(qtbot) -> None:
    item = NodeItem(_node_with_struct())
    arrows = _arrows_in(item)
    # struct 핀 P 한 줄에 ▶ (접힘 상태)
    assert arrows == ["▶"]


def test_arrow_flips_to_down_when_expanded(qtbot) -> None:
    item = NodeItem(_node_with_struct(),
                    expanded_paths=frozenset({"N.P"}))
    arrows = _arrows_in(item)
    # 펼침 ▼ + 자식 두 줄에는 화살표 없음
    assert arrows == ["▼"]


def test_no_arrow_on_leaf_pin(qtbot) -> None:
    leaf_only = Node(name="N", cls="Test",
                     pins=[Pin(name="A", cpp_type="bool", direction="Input")])
    item = NodeItem(leaf_only)
    assert _arrows_in(item) == []


def test_arrow_zone_click_emits_toggle(qtbot, monkeypatch) -> None:
    item = NodeItem(_node_with_struct())
    emitted: list[str] = []
    assert item.bus is not None
    item.bus.pin_toggle_requested.connect(lambda p: emitted.append(p))
    # struct 핀 P 의 화살표 위치 추정 — input pin은 row 좌측 들여쓰기 앞
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT
    row_y = HEADER_HEIGHT + 0 * ROW_HEIGHT + ROW_HEIGHT / 2
    click_pos = QPointF(4, row_y)
    item.toggle_at_pos(click_pos)
    assert emitted == ["N.P"]


def test_arrow_zone_click_outside_arrow_does_not_emit(qtbot) -> None:
    item = NodeItem(_node_with_struct())
    emitted: list[str] = []
    assert item.bus is not None
    item.bus.pin_toggle_requested.connect(lambda p: emitted.append(p))
    from t3dgraph.core.app.items import HEADER_HEIGHT, ROW_HEIGHT, NODE_WIDTH
    row_y = HEADER_HEIGHT + 0 * ROW_HEIGHT + ROW_HEIGHT / 2
    # 노드 중앙(라벨 영역)은 토글 미발사
    item.toggle_at_pos(QPointF(NODE_WIDTH / 2, row_y))
    assert emitted == []
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/app/test_items_disclosure.py -v`
Expected: FAIL — `toggle_at_pos` 메서드 없음 또는 화살표 미존재.

- [ ] **Step 3: `NodeItem` 들여쓰기 조정 + 화살표 그리기**

`items.py`의 `for i, row in enumerate(rows):` 루프를 다음으로 교체:

```python
self._rows: dict[str, float] = {}
self._row_paths: list[str] = [r.path for r in rows]
self._arrow_zones: dict[str, tuple[float, float, float]] = {}  # path -> (x0, x1, cy)
for i, row in enumerate(rows):
    cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
    self._rows[row.path] = cy
    is_input = (row.pin.direction or "").lower() != "output"
    mx = 0.0 if is_input else NODE_WIDTH
    if row.has_dot:
        dot = QGraphicsEllipseItem(
            mx - PIN_RADIUS, cy - PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, self)
        if pin_colors is not None:
            resolved = pin_colors.resolve(row.pin.cpp_type)
            dot.setBrush(QBrush(resolved.color))
            if resolved.is_array:
                dot.setPen(QPen(QColor(40, 40, 40), 1.5))
            else:
                dot.setPen(QPen(Qt.NoPen))
        else:
            dot.setBrush(QBrush(QColor(200, 200, 120)))
            dot.setPen(QPen(Qt.NoPen))
    arrow_w = 12.0
    indent = 18 + row.depth * 12
    if row.has_children:
        arrow_char = "▼" if row.path in expanded_paths else "▶"
        arrow = QGraphicsSimpleTextItem(arrow_char, self)
        arrow.setBrush(QBrush(QColor(210, 210, 210)))
        if is_input:
            ax = indent - 14
            zone = (0.0, indent - 2)
        else:
            ax = NODE_WIDTH - indent + 2
            zone = (NODE_WIDTH - indent + 2, NODE_WIDTH)
        arrow.setPos(ax, cy - ROW_HEIGHT / 2 + 2)
        self._arrow_zones[row.path] = (zone[0], zone[1], cy)
    label = QGraphicsSimpleTextItem(row.pin.name, self)
    label.setBrush(QBrush(QColor(210, 210, 210)))
    lx = indent if is_input else NODE_WIDTH - 8 - label.boundingRect().width()
    label.setPos(lx, cy - ROW_HEIGHT / 2 + 2)
```

- [ ] **Step 4: `toggle_at_pos` 메서드 추가**

`NodeItem` 안 (`toggle_pin_at_row` 다음):

```python
def toggle_at_pos(self, pos: QPointF) -> bool:
    """화살표 zone 좌표에 있으면 토글 발사. 발사 여부 반환."""
    for path, (x0, x1, cy) in self._arrow_zones.items():
        if x0 <= pos.x() <= x1 and abs(pos.y() - cy) <= ROW_HEIGHT / 2:
            if self._bus is not None:
                self._bus.pin_toggle_requested.emit(path)
            return True
    return False
```

- [ ] **Step 5: `mousePressEvent` 추가 — 화살표 클릭 우선**

`mouseDoubleClickEvent` 위에 추가:

```python
def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
    if self.toggle_at_pos(event.pos()):
        event.accept()
        return
    super().mousePressEvent(event)
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `pytest tests/app/test_items_disclosure.py -v`
Expected: 5 passed

- [ ] **Step 7: 회귀 확인**

Run: `pytest tests/app -v`
Expected: 전체 통과 (들여쓰기 변경이 기존 라벨 테스트와 충돌 없는지).

- [ ] **Step 8: 커밋**

```bash
git add tests/app/test_items_disclosure.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): pin row disclosure indicator + arrow-zone click (F12)"
```

---

## Task 6: `scene.populate` — pin_colors 주입 경로

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`

- [ ] **Step 1: `populate` 시그니처 확장**

`scene.py`의 `populate` 시그니처:

```python
def populate(self, graph: GraphModel, *,
             view_state: ViewState | None = None,
             flow: FlowResult | None = None,
             pin_colors: "PinColorTable | None" = None) -> None:
```

상단에 import:

```python
from .pin_colors import PinColorTable
```

`NodeItem(...)` 생성 인자에 `pin_colors=pin_colors` 추가:

```python
item = NodeItem(
    node,
    connected_paths=frozenset(connected.get(node.name, set())),
    connected_only=vs.connected_pins_only,
    expanded_paths=frozenset(
        p for p in vs.expanded_pin_paths if p.startswith(f"{node.name}.")
    ),
    highlighted=vs.fan_in_highlight and node.name in convergence,
    pin_colors=pin_colors,
)
```

- [ ] **Step 2: 테스트 회귀 확인**

Run: `pytest tests/app -v`
Expected: 통과 (인자 추가, 디폴트 None이라 기존 호출부 영향 없음).

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/core/app/scene.py
git commit -m "feat(app): GraphScene.populate accepts pin_colors (F10)"
```

---

## Task 7: `MainWindow` — PinColorTable 보유 + 주입 + 리셋 메뉴

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: `MainWindow.__init__`에 `PinColorTable` 보유**

`main_window.py` 상단 import:

```python
from .pin_colors import PinColorTable
```

`__init__` 본문 `self.view_state = ViewState()` 다음 줄에:

```python
self.pin_colors = PinColorTable.load()
```

- [ ] **Step 2: `_rebuild_scene` / `_render_current`에 주입**

`_rebuild_scene`:

```python
def _rebuild_scene(self) -> None:
    if self.graph is not None:
        self.scene.populate(self.graph, view_state=self.view_state,
                            flow=self._flow, pin_colors=self.pin_colors)
```

`_render_current` 안 `self.scene.populate(...)` 호출도 `pin_colors=self.pin_colors` 추가:

```python
self.scene.populate(current, view_state=self.view_state,
                    flow=bundle.flow, pin_colors=self.pin_colors)
```

- [ ] **Step 3: "팔레트 리셋" 메뉴 액션**

`_build_menu`:

```python
def _build_menu(self) -> None:
    file_menu = self.menuBar().addMenu("파일")
    file_menu.addAction("열기…").triggered.connect(self._on_open)
    file_menu.addAction("에셋 폴더 열기…").triggered.connect(self._on_open_folder)
    file_menu.addAction("종료").triggered.connect(self.close)
    view_menu = self.menuBar().addMenu("보기")
    view_menu.addAction("핀 색 팔레트 리셋").triggered.connect(self._on_reset_palette)
```

`_on_reset_palette` 메서드 추가 (`_on_open_folder` 아래):

```python
def _on_reset_palette(self) -> None:
    PinColorTable.reset_user_file()
    self.pin_colors = PinColorTable.load()
    self._rebuild_scene()
    self.statusBar().showMessage("핀 색 팔레트를 디폴트로 되돌렸습니다.", 4000)
```

- [ ] **Step 4: 수동 검증 — GUI 기동 (선택)**

```bash
uv run t3dgraph-gui
```

Orion 샘플 폴더 열어 핀 dot에 타입별 색이 들어오는지, 구조체 핀에 ▶/▼가 표시되는지 확인. 화살표 클릭 시 펼침 토글 동작.

- [ ] **Step 5: 통합 테스트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 6: 커밋**

```bash
git add src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): MainWindow wires PinColorTable + palette reset (F10)"
```

---

## Self-Review 체크리스트

- Spec §3.2 사용자 파일 카피 — Task 2 Step 3 + `test_first_load_copies_bundle_to_user_dir` ✅
- Spec §3.3 TOML 스키마 — Task 1 Step 2 (palette / bucket / special 3섹션) ✅
- Spec §3.4 `PinColorTable` API — Task 2 Step 3 (`load`, `resolve`, `reset_user_file`) ✅
- Spec §3.5 인스턴스 보유 — Task 7 Step 1 (`MainWindow.pin_colors`) ✅
- Spec §3.6 items 색 적용 + 외곽선 — Task 4 Step 2 ✅
- Spec §3.7 테스트 — Task 2 ✅
- Spec §4 disclosure + 단일 클릭 — Task 5 ✅
- PRESERVE-ALL — NodeItem/LinkItem 생성 로직은 그대로, 시각 옵션만 변경 ✅
- 슬라이스 종속: μ는 ν 진입 전에 머지되어야 함 (items.py 동시 편집 회피)

---

## 완료 후

머지 후 다음:
- 슬라이스 ν 플랜 진입 (F13·F18·F19)
- improver 자동 리뷰 → backlog 등재
