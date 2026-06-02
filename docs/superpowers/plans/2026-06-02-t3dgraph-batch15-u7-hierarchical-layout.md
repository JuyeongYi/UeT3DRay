# batch ⑮ u7 — 위상적 자동 정렬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** exec link 기반 위상적 layered layout. 부모 노드의 출력 핀 순서에 따라 자식 노드 수직 정렬. 단순 overlap 해소(g11)와 별도 — "보기 → 위상 정렬" 메뉴 액션.

**알고리즘**: 단순 Sugiyama 변형
1. exec link 추출 → DAG (cycle 무시)
2. Longest-path layer assignment (sources column 0, 그 다음 column 1, …)
3. 각 layer 내 — 부모의 outgoing 핀 인덱스 median으로 노드 정렬
4. 데이터 link 노드는 해당 layer의 적절한 위치에 배치

**Pre-condition:** master 최신. g11 `auto_layout.py` 모듈 존재 (overlap 해소).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/auto_layout.py` | 수정 (`hierarchical_arrange` 신규 함수) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (메뉴 "위상 정렬" + 핸들러) |
| `tests/app/test_hierarchical_layout.py` | 신규 |

---

## Task 1: hierarchical_arrange — 알고리즘 + 메뉴

**Files:**
- Modify: `src/t3dgraph/core/app/auto_layout.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_hierarchical_layout.py`

- [ ] **Step 1: 테스트**

```python
"""u7 — 위상적 layered layout."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.auto_layout import hierarchical_arrange


def _exec(name, direction):
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def test_linear_chain_layers() -> None:
    """A → B → C 가 column 0, 1, 2에."""
    a = Node(name="A", cls="X", pins=[_exec("Out", "Output")])
    b = Node(name="B", cls="X",
             pins=[_exec("In", "Input"), _exec("Out", "Output")])
    c = Node(name="C", cls="X", pins=[_exec("In", "Input")])
    g = GraphModel(
        nodes=[a, b, c],
        links=[Link(source_path="A.Out", target_path="B.In"),
               Link(source_path="B.Out", target_path="C.In")],
    )
    positions = hierarchical_arrange(g)
    ax, _ = positions["A"]
    bx, _ = positions["B"]
    cx, _ = positions["C"]
    assert ax < bx < cx


def test_pin_order_determines_child_vertical_order() -> None:
    """A의 출력 핀 a(위), b(아래) — a에 연결된 X 위, b에 연결된 Y 아래."""
    a = Node(name="A", cls="X",
             pins=[
                 _exec("a", "Output"),
                 _exec("b", "Output"),
             ])
    x_node = Node(name="X", cls="X",
                  pins=[_exec("In", "Input")])
    y_node = Node(name="Y", cls="X",
                  pins=[_exec("In", "Input")])
    g = GraphModel(
        nodes=[a, x_node, y_node],
        links=[
            Link(source_path="A.a", target_path="X.In"),
            Link(source_path="A.b", target_path="Y.In"),
        ],
    )
    positions = hierarchical_arrange(g)
    _, x_y = positions["X"]
    _, y_y = positions["Y"]
    assert x_y < y_y, f"X y={x_y} should be above Y y={y_y}"


def test_unconnected_nodes_placed_separately() -> None:
    """exec link 없는 노드는 별도 위치(다른 column 또는 최하단)."""
    a = Node(name="A", cls="X")
    isolated = Node(name="Floating", cls="X")
    g = GraphModel(nodes=[a, isolated], links=[])
    positions = hierarchical_arrange(g)
    assert "A" in positions
    assert "Floating" in positions
    # 둘이 다른 위치
    assert positions["A"] != positions["Floating"]


def test_returns_dict_for_all_nodes() -> None:
    g = GraphModel(nodes=[
        Node(name="N1", cls="X"),
        Node(name="N2", cls="X"),
    ])
    positions = hierarchical_arrange(g)
    assert set(positions.keys()) == {"N1", "N2"}
```

- [ ] **Step 2: 알고리즘 구현**

`src/t3dgraph/core/app/auto_layout.py`에 추가:

```python
def hierarchical_arrange(graph) -> dict[str, tuple[float, float]]:
    """exec link 기반 위상적 layered layout.

    1. exec link → DAG (cycle 무시 — visited 추적)
    2. layer assignment — source부터 BFS, depth = layer index
    3. 각 layer 내 — 부모의 outgoing pin index median으로 정렬
    4. 좌표: x = layer_idx * COL_WIDTH, y = position * ROW_HEIGHT
    """
    COL_WIDTH = 300.0
    ROW_HEIGHT = 150.0

    # exec link만 추출
    exec_edges: list[tuple[str, str]] = []
    pin_index: dict[str, dict[str, int]] = {}   # node → pin_name → index_in_outputs
    for node in graph.nodes:
        out_pins = [p for p in node.pins if p.is_execution
                    and (p.direction or "").lower() in ("output", "io")]
        pin_index[node.name] = {p.name: i for i, p in enumerate(out_pins)}
    for link in graph.links:
        s_node, s_pin = link.source_path.split(".", 1)
        s_pin_top = s_pin.split(".", 1)[0]
        # exec 핀인지 검사 — pin_index에 있으면 exec output
        if s_node in pin_index and s_pin_top in pin_index[s_node]:
            t_node = link.target_path.split(".", 1)[0]
            exec_edges.append((s_node, t_node))

    # adjacency + in-degree
    children: dict[str, list[str]] = {}
    in_count: dict[str, int] = {}
    for s, t in exec_edges:
        children.setdefault(s, []).append(t)
        in_count[t] = in_count.get(t, 0) + 1
    
    all_nodes = [n.name for n in graph.nodes]
    sources = [n for n in all_nodes if in_count.get(n, 0) == 0]

    # layer assignment — BFS from sources
    layer: dict[str, int] = {}
    queue: list[tuple[str, int]] = [(s, 0) for s in sources]
    visited: set[str] = set()
    while queue:
        node, depth = queue.pop(0)
        if node in visited:
            layer[node] = max(layer.get(node, depth), depth)
            continue
        visited.add(node)
        layer[node] = max(layer.get(node, depth), depth)
        for c in children.get(node, []):
            queue.append((c, depth + 1))
    # isolated 노드는 별도 column 끝에
    max_layer = max(layer.values(), default=-1)
    for n in all_nodes:
        if n not in layer:
            layer[n] = max_layer + 1

    # 각 layer 내 정렬 — 부모 pin index median
    layers_by_idx: dict[int, list[str]] = {}
    for n, l in layer.items():
        layers_by_idx.setdefault(l, []).append(n)
    
    # node의 "rank" = 부모(들)의 outgoing pin index 평균
    def rank(node_name: str) -> float:
        parents = [(s, t) for s, t in exec_edges if t == node_name]
        if not parents:
            return float("inf")
        indices = []
        for s, _ in parents:
            for link in graph.links:
                if link.target_path.split(".", 1)[0] != node_name:
                    continue
                if link.source_path.split(".", 1)[0] != s:
                    continue
                s_pin = link.source_path.split(".", 1)[1].split(".", 1)[0]
                if s in pin_index and s_pin in pin_index[s]:
                    indices.append(pin_index[s][s_pin])
        return sum(indices) / len(indices) if indices else float("inf")
    
    positions: dict[str, tuple[float, float]] = {}
    for l_idx in sorted(layers_by_idx.keys()):
        layer_nodes = layers_by_idx[l_idx]
        layer_nodes.sort(key=lambda n: (rank(n), n))  # rank tie → 이름 정렬
        for row_idx, name in enumerate(layer_nodes):
            positions[name] = (l_idx * COL_WIDTH, row_idx * ROW_HEIGHT)
    return positions
```

- [ ] **Step 3: MainWindow 메뉴 액션**

```python
def _build_menu(self):
    # ... 기존 "자동 정렬" 다음에:
    view_menu.addAction("위상 정렬").triggered.connect(self._on_hierarchical_arrange)

def _on_hierarchical_arrange(self) -> None:
    if self.graph is None:
        return
    from .auto_layout import hierarchical_arrange
    new_positions = hierarchical_arrange(self.graph)
    key = self._current_graph_key()
    for name, (x, y) in new_positions.items():
        self.layout_overrides.set(key, name, x, y)
    self._schedule_save_state()
    self._rebuild_scene()
    self.statusBar().showMessage("위상 정렬 완료", 4000)
```

- [ ] **Step 4: 실행**

Run: `pytest tests/app/test_hierarchical_layout.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

Orion 샘플 함수 그래프 진입 → "보기 → 위상 정렬" → Entry가 좌측, Return이 우측, 중간 노드들이 부모 핀 순서로 수직 배치.

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_hierarchical_layout.py src/t3dgraph/core/app/auto_layout.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): hierarchical_arrange — exec DAG layered layout (u7)"
```

## 완료 후

g11(overlap 해소) + u7(위상 정렬) 두 메뉴 액션. 사용자가 상황에 맞게 선택. 추후 시각 cross 최소화 휴리스틱 추가 가능.
