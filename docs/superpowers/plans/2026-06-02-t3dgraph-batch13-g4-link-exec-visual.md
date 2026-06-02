# batch ⑬ g4 — Link/Exec 시각 (F25 + F26 + F27) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** (F25) Link 색을 source pin 색으로, (F26) 실행 핀 dot/라벨 굵게·확대, (F27) 실행 핀 색 `#FFFFFF` → `#FFB000` + 애니메이션.

**Spec:** §6

**Pre-condition:** master `f8fa09d` 이상. g1·g5와 items.py 공유 — 머지 순서 코디네이션.

---

## Task 1: LinkItem 색·두께·is_execution 파라미터화

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `src/t3dgraph/core/app/scene.py`
- Create: `tests/app/test_link_color.py`

- [ ] **Step 1: 테스트**

```python
"""g4 (F25/F26/F27) — Link 색·두께·exec 애니메이션."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from t3dgraph.core.app.items import LinkItem


def test_link_uses_specified_color() -> None:
    item = LinkItem(QPointF(0,0), QPointF(100,0),
                    pen_color=QColor("#FF0000"))
    assert item.pen().color() == QColor("#FF0000")


def test_link_default_color() -> None:
    item = LinkItem(QPointF(0,0), QPointF(100,0))
    assert item.pen().color() == QColor("#AAAAAA")


def test_link_exec_thicker() -> None:
    item = LinkItem(QPointF(0,0), QPointF(100,0),
                    is_execution=True, width=3.0)
    assert item.pen().widthF() == 3.0


def test_link_exec_has_dash() -> None:
    item = LinkItem(QPointF(0,0), QPointF(100,0), is_execution=True)
    from PySide6.QtCore import Qt
    assert item.pen().style() == Qt.DashLine or len(item.pen().dashPattern()) > 0
```

- [ ] **Step 2: LinkItem 시그니처 확장**

`src/t3dgraph/core/app/items.py`:

```python
class LinkItem(QGraphicsPathItem):
    def __init__(self, p1: QPointF, p2: QPointF, *,
                 pen_color: QColor | None = None,
                 width: float = 1.5,
                 is_execution: bool = False):
        super().__init__(self._build_path(p1, p2))
        color = pen_color if pen_color is not None else QColor("#AAAAAA")
        pen = QPen(color, width)
        if is_execution:
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([4, 3])
        self.setPen(pen)
        self.setZValue(-1)
        self._is_execution = is_execution
        self._dash_phase = 0.0
        if is_execution:
            self._setup_animation()

    def _setup_animation(self) -> None:
        from PySide6.QtCore import QTimer
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(50)
        self._anim_timer.timeout.connect(self._advance_dash)
        self._anim_timer.start()

    def _advance_dash(self) -> None:
        self._dash_phase -= 0.5
        pen = self.pen()
        pen.setDashOffset(self._dash_phase)
        self.setPen(pen)
        self.update()
```

- [ ] **Step 3: scene._add_link이 source pin 룩업해 색·exec 결정**

`src/t3dgraph/core/app/scene.py`:

```python
def populate(self, graph, *, view_state=None, flow=None, pin_colors=None,
             layout_overrides=None, graph_key=""):
    # ... 기존 ...
    self._graph = graph   # find_pin용 보관
    self._pin_colors = pin_colors
    # ... NodeItem 생성 ...
    for link in graph.links:
        self._add_link(link)
    # ...

def _add_link(self, link) -> None:
    s_node, t_node = node_of(link.source_path), node_of(link.target_path)
    src, dst = self._nodes.get(s_node), self._nodes.get(t_node)
    if src is None or dst is None:
        return
    s_sub = link.source_path.split(".", 1)[1] if "." in link.source_path else ""
    t_sub = link.target_path.split(".", 1)[1] if "." in link.target_path else ""
    p1 = src.pin_anchor(s_sub, "Output")
    p2 = dst.pin_anchor(t_sub, "Input")
    # source pin 룩업 → 색·exec
    color = None
    is_exec = False
    if self._graph is not None:
        src_pin = self._graph.find_pin(link.source_path)
        if src_pin is not None:
            is_exec = src_pin.is_execution
            if self._pin_colors is not None:
                color = self._pin_colors.resolve(src_pin.cpp_type).color
    width = 3.0 if is_exec else 1.5
    item = LinkItem(p1, p2, pen_color=color, width=width, is_execution=is_exec)
    self.addItem(item)
    self._links.append((item, s_node, s_sub, t_node, t_sub))
```

- [ ] **Step 4: 실행 — 통과**

Run: `pytest tests/app/test_link_color.py -v`
Expected: 4 passed.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_link_color.py src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py
git commit -m "feat(app): LinkItem color/width/exec animation (F25 + F26 + F27 link side)"
```

---

## Task 2: 실행 핀 dot 확대 + 라벨 bold (F26)

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `tests/app/test_items_exec_visual.py` 신규

- [ ] **Step 1: 테스트**

```python
def test_exec_pin_dot_larger(qtbot) -> None:
    from PySide6.QtWidgets import QGraphicsEllipseItem
    from t3dgraph.core.base.graph_model import Node, Pin
    from t3dgraph.core.app.items import NodeItem
    exec_pin = Pin(name="X", cpp_type="FRigVMExecuteContext",
                   direction="Output", is_execution=True)
    data_pin = Pin(name="Y", cpp_type="float", direction="Output")
    n = Node(name="N", cls="T", pins=[exec_pin, data_pin])
    item = NodeItem(n)
    dots = [c for c in item.childItems() if isinstance(c, QGraphicsEllipseItem)]
    # 두 dot 중 하나는 더 큼
    radii = sorted([d.rect().width() / 2 for d in dots])
    assert radii[-1] > radii[0]


def test_exec_pin_label_bold(qtbot) -> None:
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    from t3dgraph.core.base.graph_model import Node, Pin
    from t3dgraph.core.app.items import NodeItem
    exec_pin = Pin(name="ExecPin", cpp_type="FRigVMExecuteContext",
                   direction="Output", is_execution=True)
    n = Node(name="N", cls="T", pins=[exec_pin])
    item = NodeItem(n)
    label = next(c for c in item.childItems()
                 if isinstance(c, QGraphicsSimpleTextItem) and c.text() == "ExecPin")
    assert label.font().bold() is True
```

- [ ] **Step 2: NodeItem 변경**

핀 행 렌더 루프 (`for i, row in enumerate(rows):`)에서 `row.pin.is_execution` 검사:

```python
is_exec_pin = row.pin.is_execution
dot_radius = 6.0 if is_exec_pin else PIN_RADIUS  # 4.0
# dot 생성 시 radius 사용 (기존 PIN_RADIUS 대체)
dot = QGraphicsEllipseItem(
    mx - dot_radius, cy - dot_radius,
    2 * dot_radius, 2 * dot_radius, self)
# ...
# 라벨
font = label.font()
if is_exec_pin:
    font.setBold(True)
    label.setFont(font)
```

- [ ] **Step 3: 실행 + 회귀**

Run: `pytest tests -v`

- [ ] **Step 4: 커밋**

```bash
git add tests/app/test_items_exec_visual.py src/t3dgraph/core/app/items.py
git commit -m "feat(app): exec pin dot larger + label bold (F26)"
```

---

## Task 3: 팔레트 exec 색 변경 + 사용자 파일 마이그레이션 (F27)

**Files:**
- Modify: `src/t3dgraph/core/app/resources/pin_colors.toml`
- Modify: `src/t3dgraph/core/app/pin_colors.py`
- Modify: `tests/app/test_pin_colors.py` 또는 신규

- [ ] **Step 1: 번들 TOML 갱신**

`src/t3dgraph/core/app/resources/pin_colors.toml`:

```toml
[palette]
exec    = "#FFB000"   # 앰버 — 다크 배경 가독성 (기존 #FFFFFF)
bool    = "#A02020"
# ...
```

- [ ] **Step 2: PinColorTable.load에 마이그레이션**

```python
@classmethod
def load(cls) -> "PinColorTable":
    user_file = cls._user_dir() / "pin_colors.toml"
    if not user_file.exists():
        user_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cls._bundle_path(), user_file)
        return cls._from_toml_bytes(user_file.read_bytes())
    # 마이그레이션 — exec=#FFFFFF (legacy) → 디폴트로 갱신
    data = user_file.read_bytes()
    table = cls._from_toml_bytes(data)
    exec_color = table._palette.get("exec")
    if exec_color is not None and exec_color.name().upper() == "#FFFFFF":
        # 번들 디폴트로 exec만 갱신
        bundle = cls._from_toml_bytes(cls._bundle_path().read_bytes())
        table._palette["exec"] = bundle._palette["exec"]
        # 사용자 파일에도 반영
        cls._write_exec_color(user_file, bundle._palette["exec"])
    return table

@classmethod
def _write_exec_color(cls, user_file: Path, new_color: QColor) -> None:
    """사용자 TOML의 [palette] exec만 안전 치환 — 다른 줄은 보존."""
    import re
    text = user_file.read_text(encoding="utf-8")
    new_text = re.sub(
        r'(^\s*exec\s*=\s*)"[^"]*"',
        rf'\1"{new_color.name().upper()}"',
        text, count=1, flags=re.MULTILINE,
    )
    if new_text != text:
        user_file.write_text(new_text, encoding="utf-8")
```

- [ ] **Step 3: 테스트**

```python
def test_legacy_exec_color_migrated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    # 옛 사용자 파일 (#FFFFFF)
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text(
        '[palette]\nexec = "#FFFFFF"\nbool = "#A02020"\ndefault = "#C8C878"\n'
        '[bucket]\nbool = "bool"\n'
        '[special]\nexec_marker = "ExecuteContext"\narray_marker = "TArray<"\n',
        encoding="utf-8",
    )
    table = PinColorTable.load()
    assert table._palette["exec"].name().upper() == "#FFB000"
    # 사용자 파일도 갱신됨
    assert "#FFB000" in user_file.read_text(encoding="utf-8")
    assert "#FFFFFF" not in user_file.read_text(encoding="utf-8")


def test_user_custom_exec_color_preserved(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "pin_colors.toml"
    user_file.write_text(
        '[palette]\nexec = "#00FF00"\nbool = "#A02020"\ndefault = "#C8C878"\n'
        '[bucket]\nbool = "bool"\n'
        '[special]\nexec_marker = "ExecuteContext"\narray_marker = "TArray<"\n',
        encoding="utf-8",
    )
    table = PinColorTable.load()
    # 사용자 커스텀 색은 보존
    assert table._palette["exec"].name().upper() == "#00FF00"
```

- [ ] **Step 4: 실행**

Run: `pytest tests/app/test_pin_colors.py -v`
Expected: 전 통과.

Run: `pytest tests -v`

- [ ] **Step 5: 커밋**

```bash
git add src/t3dgraph/core/app/resources/pin_colors.toml src/t3dgraph/core/app/pin_colors.py tests/app/test_pin_colors.py
git commit -m "feat(app): exec palette #FFB000 + legacy #FFFFFF migration (F27)"
```

## 완료 후

F25/F26/F27 해소.
