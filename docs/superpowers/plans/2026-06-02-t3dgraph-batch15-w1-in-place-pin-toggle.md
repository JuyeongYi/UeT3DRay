# batch ⑮ w1 — 핀 토글 in-place rebuild + populate 가드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 구조체/컨테이너 핀 펼침/접기 시 `RuntimeError: Internal C++ object (NodeItem) already deleted` 제거.

**원인:** `GraphScene.populate`의 `self.clear()`가 NodeItem들을 파괴하면서 Qt가 `selectionChanged`를 발화 → `MainWindow._on_scene_selection`이 `self.scene._nodes`의 옛 NodeItem 참조에서 `isSelected()` 호출 → 이미 deleted C++ 객체 접근.

**해법 (2 단계 병행):**
- **Task 1 (A 가드)**: `populate` 시 `_nodes` 비우는 순서 + `blockSignals` + `_on_scene_selection` RuntimeError 가드. 다른 rebuild 트리거(`apply_hidden_types` 등)도 동일 패턴 방어.
- **Task 2 (C in-place)**: 핀 토글은 scene 전체 rebuild 대신 해당 NodeItem만 자기 내부 행 재구성 + 관련 LinkItem endpoint 갱신. 객체 파괴 없음 → 시그널 폭발 원천 차단, selection·zoom 유지.

**Pre-condition:** master `187fc9d`, 633 tests.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/scene.py` | 수정 (Task 1: populate 순서·blockSignals / Task 2: `update_node_expansion` 신규) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (Task 1: `_on_scene_selection` 가드 / Task 2: `_on_pin_toggle` in-place 경로) |
| `src/t3dgraph/core/app/items.py` | 수정 (Task 2: NodeItem 상태 보관 + `set_expanded_paths` + `_install_rows` 추출) |
| `tests/app/test_scene_rebuild_safety.py` | 신규 (Task 1) |
| `tests/app/test_in_place_pin_toggle.py` | 신규 (Task 2) |

---

## Task 1: A 가드 — populate 순서 + signal block + selection 슬롯 방어

**Files:**
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_scene_rebuild_safety.py`

- [ ] **Step 1: 테스트 — 재현 + 가드 검증**

```python
"""w1-A — populate 재호출 시 selection 슬롯이 옛 NodeItem 참조로 폭발하지 않는다."""
import pytest
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene


@pytest.fixture
def two_node_graph() -> GraphModel:
    a = Node(name="A", cls="X",
             pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    b = Node(name="B", cls="X",
             pins=[Pin(name="In", cpp_type="float", direction="Input")])
    return GraphModel(
        nodes=[a, b],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )


def test_populate_twice_no_runtime_error(qtbot, two_node_graph) -> None:
    """populate 두 번 호출 — selectionChanged 슬롯이 옛 참조에서 isSelected() 못 한다."""
    scene = GraphScene()
    scene.populate(two_node_graph)
    a_item = scene._nodes["A"]
    a_item.setSelected(True)
    # 이 시점에 selectionChanged 슬롯이 _nodes를 순회하면 옛 a_item이 들어있음
    scene.populate(two_node_graph)   # 옛 a_item 파괴 → 시그널 발화
    # 새 _nodes만 남고, 옛 a_item에 isSelected 호출 시도 없어야 함
    assert len(scene._nodes) == 2
    # 새 객체로 갈아끼움 확인
    assert scene._nodes["A"] is not a_item


def test_main_window_pin_toggle_no_crash(qtbot, tmp_path) -> None:
    """w1-A 재현 — 구조체 핀 토글이 _on_scene_selection 폭발 없이 끝난다."""
    from t3dgraph.core.app.main_window import MainWindow
    from t3dgraph.core.base.graph_model import GraphModel, Node, Pin

    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])

    w = MainWindow()
    qtbot.addWidget(w)
    w.graph = g
    w._render_current_for_test(g) if hasattr(w, "_render_current_for_test") else w._render_current()
    # 노드 selection
    w.scene._nodes["N"].setSelected(True)
    # 핀 토글 — populate 재호출 트리거 (Task 2 후엔 in-place지만 가드는 여전히 유효해야)
    w._on_pin_toggle("N.Pos")   # 폭발 없으면 통과
```

- [ ] **Step 2: scene.py 가드**

`src/t3dgraph/core/app/scene.py` `populate` 메서드 head:

```python
    def populate(self, graph, *, ...) -> None:
        vs = view_state or ViewState()
        keep_selected = self.selected_node_name()
        # w1-A: selectionChanged 시그널이 옛 _nodes 참조 노출하지 않도록 순서 + 블록
        self._nodes = {}     # 옛 dict 참조 끊기 — clear 도중 시그널 발화해도 빈 dict
        self._links = []
        self.blockSignals(True)
        try:
            self.clear()
        finally:
            self.blockSignals(False)
        self._graph = graph
        self._pin_colors = pin_colors
        ...
```

(기존 `self.clear()` 위치 + `self._nodes = {}`·`self._links = []` 라인 제거 후 위 블록으로 대체.)

- [ ] **Step 3: main_window.py 가드**

`src/t3dgraph/core/app/main_window.py` `_on_scene_selection` 시작부에 가드:

```python
    def _on_scene_selection(self) -> None:
        try:
            selected = [item for item in self.scene._nodes.values()
                        if item.isSelected()]
        except RuntimeError:
            # 폭발이 와도 다음 selectionChanged에서 정상 복원
            return
        ...
```

- [ ] **Step 4: 실행**

Run: `pytest tests/app/test_scene_rebuild_safety.py -v`
Expected: 2 passed.

Run: `pytest tests -v`
Expected: 전체 635 통과 (633 + 2 신규).

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_scene_rebuild_safety.py src/t3dgraph/core/app/scene.py src/t3dgraph/core/app/main_window.py
git commit -m "fix(app): guard scene rebuild against stale NodeItem signal handlers (w1-A)"
```

---

## Task 2: C in-place — 핀 토글이 scene rebuild 안 함

**Files:**
- Modify: `src/t3dgraph/core/app/items.py`
- Modify: `src/t3dgraph/core/app/scene.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_in_place_pin_toggle.py`

**설계:**

- `NodeItem`이 `connected_paths`·`changed_paths`·`connected_only`·`expanded_paths`·`pin_colors`를 인스턴스 상태로 보관 (현재 `__init__` 지역 변수).
- `__init__`의 row 행/dot/label/arrow 구성 로직을 `_install_rows()` 메서드로 추출. `__init__` 마지막에 호출.
- `set_expanded_paths(new)` 메서드: 자식 graphics item 중 `_row_children` 그룹만 제거 → rows 재계산 → height/width 갱신 → `_install_rows()` 재호출.
- `GraphScene.update_node_expansion(node_name, expanded_paths_for_node)`: 해당 NodeItem `set_expanded_paths` 호출 + 관련 LinkItem `update_endpoints` 갱신.
- `MainWindow._on_pin_toggle`: 기존 `_render_current()` 대신 `scene.update_node_expansion(...)` 호출.

- [ ] **Step 1: 테스트**

```python
"""w1-C — 핀 토글이 scene rebuild 없이 in-place 처리."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.scene import GraphScene


def test_node_item_identity_preserved_after_toggle(qtbot) -> None:
    """핀 토글 후 NodeItem 객체 동일성 유지 (rebuild 아님)."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])

    scene = GraphScene()
    scene.populate(g)
    item_before = scene._nodes["N"]
    scene.update_node_expansion("N", frozenset({"N.Pos"}))
    item_after = scene._nodes["N"]
    assert item_after is item_before, "in-place rebuild 가 객체를 갈아끼웠다"
    # 자식 행이 늘어났는지 — rows에 N.Pos.X 포함
    assert "N.Pos.X" in item_after._rows


def test_link_endpoint_updates_after_neighbor_expansion(qtbot) -> None:
    """이웃 노드가 펼쳐지면 관련 LinkItem endpoint도 새 anchor로 이동."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    target = Node(name="T", cls="X", pins=[parent])
    src = Node(name="S", cls="X",
               pins=[Pin(name="Out", cpp_type="float", direction="Output")])
    g = GraphModel(
        nodes=[src, target],
        links=[Link(source_path="S.Out", target_path="T.Pos.X")],
    )
    scene = GraphScene()
    scene.populate(g)
    link_item_before = scene._links[0][0]
    # 펼치기 전엔 자식 핀 anchor가 없음 (toggle 안 했을 때 fallback)
    scene.update_node_expansion("T", frozenset({"T.Pos"}))
    # 펼친 후 T.Pos.X anchor가 살아있고 link endpoint가 그 위치 근처
    target_item = scene._nodes["T"]
    new_anchor = target_item.pin_anchor("Pos.X", "Input")
    # link_item이 endpoint 갱신됐는지 — boundingRect 또는 _p2 직접 검사
    assert link_item_before._p2 == new_anchor or link_item_before.boundingRect().contains(new_anchor - link_item_before.pos())


def test_selection_preserved_across_pin_toggle(qtbot) -> None:
    """핀 토글 시 selection 유지."""
    sub = Pin(name="X", cpp_type="float", direction="Input")
    parent = Pin(name="Pos", cpp_type="FVector", direction="Input",
                 subpins=[sub])
    n = Node(name="N", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    scene = GraphScene()
    scene.populate(g)
    scene._nodes["N"].setSelected(True)
    scene.update_node_expansion("N", frozenset({"N.Pos"}))
    assert scene._nodes["N"].isSelected()


def test_update_node_expansion_unknown_name_noop(qtbot) -> None:
    g = GraphModel(nodes=[Node(name="N", cls="X")])
    scene = GraphScene()
    scene.populate(g)
    scene.update_node_expansion("Unknown", frozenset())   # 폭발 없이 noop
```

- [ ] **Step 2: NodeItem 상태 보관 + `_install_rows` 추출 + `set_expanded_paths`**

`src/t3dgraph/core/app/items.py` `NodeItem.__init__` 끝부분에 상태 저장:

```python
        # __init__ 진입 직후 (rows 계산 전): 상태 저장
        self._connected_paths = connected_paths
        self._changed_paths = changed_paths
        self._connected_only = connected_only
        self._expanded_paths = expanded_paths
        self._pin_colors = pin_colors
        # row 행 구성용 자식 item 추적 (set_expanded_paths가 청소할 대상)
        self._row_children: list[QGraphicsItem] = []
        ...
```

기존 `__init__`의 row 행 생성 루프(157~234 라인, `self._rows`·`self._row_paths`·`self._arrow_zones` 초기화부터 라벨 setPos까지)를 별도 메서드로 추출:

```python
    def _install_rows(self) -> None:
        rows = collect_pin_rows(
            self.node,
            connected_subtree=self._connected_paths,
            changed_pins=self._changed_paths,
            connected_only=self._connected_only,
            expanded=self._expanded_paths,
        )
        self._rows = {}
        self._row_paths = [r.path for r in rows]
        self._arrow_zones = {}
        for i, row in enumerate(rows):
            cy = HEADER_HEIGHT + i * ROW_HEIGHT + ROW_HEIGHT / 2
            self._rows[row.path] = cy
            # ... 기존 dot/arrow/label 생성 (각 graphics item 생성 시
            # self._row_children.append(...) 로 추적)
            ...

    def _clear_rows(self) -> None:
        for child in self._row_children:
            scene = self.scene()
            if scene is not None:
                scene.removeItem(child)
            # parent 끊기로 deleteLater 유도
            child.setParentItem(None)
        self._row_children = []
        self._arrow_zones = {}

    def set_expanded_paths(self, expanded: frozenset[str]) -> None:
        if expanded == self._expanded_paths:
            return
        self._expanded_paths = expanded
        self._clear_rows()
        # 새 row 수에 따른 height 재계산
        rows = collect_pin_rows(
            self.node,
            connected_subtree=self._connected_paths,
            changed_pins=self._changed_paths,
            connected_only=self._connected_only,
            expanded=expanded,
        )
        if self._profile.layout_hint == "passthrough":
            height = HEADER_HEIGHT + ROW_HEIGHT
        else:
            height = HEADER_HEIGHT + max(len(rows), 1) * ROW_HEIGHT
        self.setRect(QRectF(0, 0, self._node_width, height))
        self._install_rows()
```

`__init__` 끝에 `self._install_rows()` 호출. 기존 본문의 row 루프는 제거.

**중요:** dot/arrow/label `QGraphicsEllipseItem`·`QGraphicsSimpleTextItem` 생성 시점에 `self._row_children.append(item)` 추가. header title/chevron/var badge는 row와 무관하므로 `_row_children`에 넣지 **않음**.

- [ ] **Step 3: GraphScene.update_node_expansion**

`src/t3dgraph/core/app/scene.py`:

```python
    def update_node_expansion(self, node_name: str,
                              expanded_paths: frozenset[str]) -> None:
        item = self._nodes.get(node_name)
        if item is None:
            return
        item.set_expanded_paths(expanded_paths)
        # 관련 link endpoint 갱신
        for link_item, s_node, s_sub, d_node, d_sub in self._links:
            if s_node != node_name and d_node != node_name:
                continue
            src = self._nodes.get(s_node)
            dst = self._nodes.get(d_node)
            if src is None or dst is None:
                continue
            p1 = src.pin_anchor(s_sub, "Output")
            p2 = dst.pin_anchor(d_sub, "Input")
            link_item.update_endpoints(p1, p2)
```

- [ ] **Step 4: MainWindow._on_pin_toggle 갱신**

`src/t3dgraph/core/app/main_window.py` `_on_pin_toggle` 본문 — 기존 `self._render_current()` 호출 대신:

```python
    def _on_pin_toggle(self, full_path: str) -> None:
        vs = self.current_view_state()
        vs.toggle_pin_expanded(full_path)
        # in-place: 해당 노드만 갱신
        node_name = full_path.split(".", 1)[0]
        expanded_for_node = frozenset(
            p for p in vs.expanded_pin_paths if p.startswith(f"{node_name}.")
        )
        self.scene.update_node_expansion(node_name, expanded_for_node)
        self._schedule_save_state()
```

(기존 호출 흐름이 다르면 핵심: `_render_current()` → `scene.update_node_expansion(...)` 교체.)

- [ ] **Step 5: 실행**

Run: `pytest tests/app/test_in_place_pin_toggle.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 639 통과 (635 + 4 신규).

- [ ] **Step 6: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 샘플 — 구조체/배열 핀 펼침/접기 반복:
- 콘솔 RuntimeError 없음
- 클릭한 노드 selection 유지 (깜빡임 없음)
- LinkItem이 새 핀 위치로 따라옴

- [ ] **Step 7: 커밋**

```bash
git add tests/app/test_in_place_pin_toggle.py src/t3dgraph/core/app/items.py src/t3dgraph/core/app/scene.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): in-place NodeItem rebuild on pin toggle — no scene clear (w1-C)"
```

---

## 무엇이 깨질 수 있나 (CLAUDE.md 룰 3)

| 위험 | 완화 |
|---|---|
| Task 1 가드가 너무 광범위 — populate 진짜 selection 변경도 삼킬 수 있음 | populate가 끝나면 keep_selected 복원으로 정상 selection 복귀; 가드는 try/except 한정 |
| `_row_children` 누락 시 메모리 leak (자식 item 청소 안 됨) | 테스트 1: `len(item.childItems())` 증가 추세 검사 추가 |
| `set_expanded_paths`가 link endpoint 갱신 누락 시 link 끊김 | 테스트 2 (endpoint 갱신 검증) |
| highlight·hidden_types 같은 populate 외 갱신 경로와 충돌 | populate 가드는 모든 rebuild 트리거에 동일 적용 (이미 한 곳 — populate) |
| Task 2의 `_install_rows` 추출이 기존 dot 좌표 한 줄이라도 어긋나면 시각 회귀 | 기존 visual 테스트(`test_node_layout.py` 등) 전부 재실행 |

## 완료 후

- 핀 토글 RuntimeError 영구 차단
- 토글 시 selection·zoom 유지, 깜빡임 없음
- scene 전체 rebuild는 파일 열기·뷰 모드 변경 등 진짜 필요할 때만
