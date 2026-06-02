# batch ⑬ g15 — DataFlowPanel 고립/미연결 그룹이 `r.isolated` 사용 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `data_flow_panel.py`의 "고립/미연결" 그룹이 dependency_tree에 안 들어간 모든 노드가 아닌, `analyze_data_flow`가 계산한 `result.isolated` (g8에서 exec link 포함하도록 수정)를 직접 사용. exec-only 연결된 Return·Sequence가 더 이상 isolated로 잘못 표시되지 않음.

**Pre-condition:** master 최신. data_flow_panel.py 단독 변경.

---

## Task 1: 패널이 r.isolated 직접 사용

**Files:**
- Modify: `src/t3dgraph/core/app/data_flow_panel.py`
- Modify: `tests/app/test_data_flow_panel.py` 또는 신규

- [ ] **Step 1: 테스트**

```python
"""g15 — DataFlowPanel '고립/미연결' 그룹이 r.isolated만 표시."""
from PySide6.QtWidgets import QTreeWidgetItem

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.app.data_flow_panel import DataFlowPanel
from t3dgraph.core.analysis.data_flow import analyze_data_flow


def _exec_pin(name: str, direction: str) -> Pin:
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def _data_pin(name: str, direction: str) -> Pin:
    return Pin(name=name, cpp_type="float", direction=direction)


def test_exec_only_connected_node_not_in_isolated_group(qtbot) -> None:
    """exec link로만 연결된 노드는 '고립/미연결'에 표시되지 않음."""
    entry = Node(name="Entry", cls="X",
                 pins=[_exec_pin("ExecOut", "Output")])
    body = Node(name="Body", cls="X",
                pins=[_exec_pin("ExecIn", "Input"),
                      _data_pin("Out", "Output")])
    consumer = Node(name="Consumer", cls="X",
                    pins=[_data_pin("In", "Input")])
    g = GraphModel(
        nodes=[entry, body, consumer],
        links=[
            Link(source_path="Entry.ExecOut", target_path="Body.ExecIn"),
            Link(source_path="Body.Out", target_path="Consumer.In"),
        ],
    )
    result = analyze_data_flow(g)
    panel = DataFlowPanel()
    qtbot.addWidget(panel)
    panel.show_result(result)

    # "고립/미연결" 그룹 텍스트 안 노드명 확인
    isolated_group = None
    for i in range(panel._tree.topLevelItemCount()):
        item = panel._tree.topLevelItem(i)
        if item.text(0) == "고립/미연결":
            isolated_group = item
            break
    if isolated_group is None:
        # 그룹 자체가 없으면 OK (Entry는 어디에도 없음 — exec만 연결)
        return
    isolated_names = {isolated_group.child(i).text(0)
                      for i in range(isolated_group.childCount())}
    # Entry는 exec-only 연결이지만 isolated 아님
    assert "Entry" not in isolated_names


def test_truly_isolated_node_still_in_group(qtbot) -> None:
    """진짜 어떤 link도 없는 노드는 그룹에 표시."""
    lonely = Node(name="Lonely", cls="X",
                  pins=[_data_pin("A", "Input")])
    connected_a = Node(name="A", cls="X", pins=[_data_pin("Out", "Output")])
    connected_b = Node(name="B", cls="X", pins=[_data_pin("In", "Input")])
    g = GraphModel(
        nodes=[lonely, connected_a, connected_b],
        links=[Link(source_path="A.Out", target_path="B.In")],
    )
    result = analyze_data_flow(g)
    panel = DataFlowPanel()
    qtbot.addWidget(panel)
    panel.show_result(result)

    isolated_group = None
    for i in range(panel._tree.topLevelItemCount()):
        item = panel._tree.topLevelItem(i)
        if item.text(0) == "고립/미연결":
            isolated_group = item
            break
    assert isolated_group is not None
    names = {isolated_group.child(i).text(0)
             for i in range(isolated_group.childCount())}
    assert "Lonely" in names
    assert "A" not in names and "B" not in names
```

- [ ] **Step 2: data_flow_panel.py 수정**

`src/t3dgraph/core/app/data_flow_panel.py`의 "고립/미연결" 그룹 생성 부분(line 52-61):

```python
# 기존
shown = set(self._items.keys())
unshown = [n for n in r.all_nodes if n not in shown]
if unshown:
    group = QTreeWidgetItem(["고립/미연결"])
    self._tree.addTopLevelItem(group)
    for name in unshown:
        child = QTreeWidgetItem([name])
        child.setData(0, _NODE_ROLE, name)
        group.addChild(child)
        self._items.setdefault(name, []).append(child)

# 변경 — r.isolated 직접 사용 (exec 연결 노드 포함 X)
if r.isolated:
    group = QTreeWidgetItem(["고립/미연결"])
    self._tree.addTopLevelItem(group)
    for name in r.isolated:
        child = QTreeWidgetItem([name])
        child.setData(0, _NODE_ROLE, name)
        group.addChild(child)
        self._items.setdefault(name, []).append(child)
```

- [ ] **Step 3: 실행**

Run: `pytest tests/app/test_data_flow_panel.py -v`
Expected: 신규 2 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 4: 수동 검증**

```bash
uv run t3dgraph-gui
```

함수 서브그래프 들어가서 Return, Sequence 노드 — "고립/미연결" 그룹에 안 나타남.

- [ ] **Step 5: 커밋**

```bash
git add tests/app/test_data_flow_panel.py src/t3dgraph/core/app/data_flow_panel.py
git commit -m "fix(app): DataFlowPanel '고립/미연결' uses r.isolated (g8 sync) — Return/Sequence 오탐 해소"
```

## 완료 후

g8의 isolated 정의(exec link 포함)가 UI에 반영됨. Return·Sequence 등 exec-only 연결 노드 오탐 해소.
