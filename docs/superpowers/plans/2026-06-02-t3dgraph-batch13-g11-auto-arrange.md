# batch ⑬ g11 — 자동 재배치 (F31) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** "보기 → 자동 정렬" 메뉴 액션 — 겹치는 노드를 단순 overlap 해소 알고리즘으로 분리. 결과 위치는 `LayoutOverrides`에 저장(영속). 외부 의존성 0.

**Pre-condition:** master `185b639` 이상. g10이 노드 폭 정확히 알려주면 더 정확 — g10 후 진입 권장.

---

## Task 1: `auto_arrange` 알고리즘 + 메뉴 액션

**Files:**
- Create: `src/t3dgraph/core/app/auto_layout.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_auto_layout.py`

- [ ] **Step 1: 테스트**

```python
"""g11 (F31) — 자동 재배치 overlap 해소."""
from t3dgraph.core.app.auto_layout import resolve_overlaps


def test_no_overlap_no_change() -> None:
    """겹치지 않는 노드는 위치 유지."""
    positions = {"A": (0.0, 0.0), "B": (500.0, 0.0)}
    sizes = {"A": (200.0, 100.0), "B": (200.0, 100.0)}
    result = resolve_overlaps(positions, sizes)
    assert result["A"] == (0.0, 0.0)
    assert result["B"] == (500.0, 0.0)


def test_overlap_pushed_apart() -> None:
    """겹치는 노드를 밀어내기."""
    positions = {"A": (0.0, 0.0), "B": (100.0, 50.0)}
    sizes = {"A": (200.0, 100.0), "B": (200.0, 100.0)}
    result = resolve_overlaps(positions, sizes)
    # 더 이상 겹치지 않음
    a_x, a_y = result["A"]
    b_x, b_y = result["B"]
    a_w, a_h = sizes["A"]
    b_w, b_h = sizes["B"]
    horizontal_gap = abs(a_x - b_x) >= (a_w + b_w) / 2
    vertical_gap = abs(a_y - b_y) >= (a_h + b_h) / 2
    assert horizontal_gap or vertical_gap


def test_converges_within_iter_cap() -> None:
    """많은 겹침도 iteration cap(100) 안에 수렴 또는 종료."""
    positions = {f"N{i}": (0.0, 0.0) for i in range(10)}
    sizes = {f"N{i}": (200.0, 100.0) for i in range(10)}
    result = resolve_overlaps(positions, sizes, max_iter=100)
    assert len(result) == 10


def test_preserves_keys() -> None:
    positions = {"A": (10.0, 20.0)}
    sizes = {"A": (200.0, 100.0)}
    result = resolve_overlaps(positions, sizes)
    assert set(result.keys()) == {"A"}
```

- [ ] **Step 2: 알고리즘 구현**

`src/t3dgraph/core/app/auto_layout.py`:

```python
"""노드 위치 자동 재배치 — overlap 해소."""
from __future__ import annotations


def resolve_overlaps(
    positions: dict[str, tuple[float, float]],
    sizes: dict[str, tuple[float, float]],
    *,
    max_iter: int = 100,
    padding: float = 20.0,
) -> dict[str, tuple[float, float]]:
    """겹치는 노드 쌍을 반복적으로 밀어내 overlap 해소.

    각 iteration:
      - 모든 노드 쌍 검사
      - bbox 겹침 발견 시 두 노드 중심점 잇는 방향으로 밀어내기
      - overlap 양만큼 절반씩 양쪽 이동

    수렴 또는 max_iter 도달 시 종료.
    """
    pos = dict(positions)
    nodes = list(pos.keys())
    for _ in range(max_iter):
        moved = False
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                ax, ay = pos[a]
                bx, by = pos[b]
                aw, ah = sizes[a]
                bw, bh = sizes[b]
                # bbox 겹침 계산 — 중심간 거리 < (size+padding)
                dx = bx - ax
                dy = by - ay
                overlap_x = (aw + bw) / 2 + padding - abs(dx)
                overlap_y = (ah + bh) / 2 + padding - abs(dy)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                # 작은 축으로 밀어내기 (덜 움직임)
                if overlap_x < overlap_y:
                    shift = overlap_x / 2 + 1
                    sign = 1 if dx >= 0 else -1
                    pos[a] = (ax - sign * shift, ay)
                    pos[b] = (bx + sign * shift, by)
                else:
                    shift = overlap_y / 2 + 1
                    sign = 1 if dy >= 0 else -1
                    pos[a] = (ax, ay - sign * shift)
                    pos[b] = (bx, by + sign * shift)
                moved = True
        if not moved:
            break
    return pos
```

- [ ] **Step 3: MainWindow 메뉴 액션**

`src/t3dgraph/core/app/main_window.py`:

```python
def _build_menu(self):
    # ... 기존 ...
    view_menu.addAction("자동 정렬").triggered.connect(self._on_auto_arrange)

def _on_auto_arrange(self) -> None:
    if self.graph is None:
        return
    from .auto_layout import resolve_overlaps
    # 현재 위치 수집 — layout_overrides 우선, 아니면 node.position
    key = self._current_graph_key()
    positions: dict[str, tuple[float, float]] = {}
    sizes: dict[str, tuple[float, float]] = {}
    for node in self.graph.nodes:
        override = self.layout_overrides.get(key, node.name)
        if override is not None:
            x, y = override
        elif node.position is not None:
            x, y = node.position
        else:
            x, y = 0.0, 0.0
        positions[node.name] = (x, y)
        item = self.scene.node_item(node.name)
        if item is not None:
            br = item.boundingRect()
            sizes[node.name] = (br.width(), br.height())
        else:
            sizes[node.name] = (200.0, 100.0)
    new_positions = resolve_overlaps(positions, sizes)
    # LayoutOverrides에 저장 + scene 갱신
    for name, (x, y) in new_positions.items():
        self.layout_overrides.set(key, name, x, y)
    self._schedule_save_state()
    self._rebuild_scene()
    self.statusBar().showMessage("노드 자동 정렬 완료", 4000)
```

- [ ] **Step 4: 실행**

Run: `pytest tests/app/test_auto_layout.py -v`
Expected: 4 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

겹친 노드 있는 파일 열어 "보기 → 자동 정렬" 실행 → 모든 노드가 분리됨.

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_auto_layout.py src/t3dgraph/core/app/auto_layout.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): auto-arrange action — resolve node overlaps (F31)"
```

## 완료 후

F31 해소. 사용자가 메뉴 액션으로 자동 정렬 가능. 결과는 `LayoutOverrides` 영속화.
