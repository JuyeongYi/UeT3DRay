# batch ⑬ g8 — Isolated 판정 시 exec 연결도 고려 (F30) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `analyze_data_flow`의 isolated 판정이 exec link도 포함해 "어떤 연결도 없는 노드"만 isolated로 표시. Entry/Return 같이 exec만 연결된 노드가 잘못 isolated로 보고되는 문제 해결.

**Spec:** §12 (추가)

**Pre-condition:** master `f167973` 이상. 다른 슬라이스와 파일 충돌 없음 (`core/analysis/data_flow.py` 단독).

---

## Task 1: isolated 판정 — 모든 link 기준

**Files:**
- Modify: `src/t3dgraph/core/analysis/data_flow.py`
- Modify: `tests/core/analysis/test_data_flow.py` 또는 신규

- [ ] **Step 1: 테스트**

```python
"""g8 (F30) — isolated 판정에서 exec 연결도 포함."""
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.data_flow import analyze_data_flow


def _exec_pin(name: str, direction: str) -> Pin:
    return Pin(name=name, cpp_type="FRigVMExecuteContext",
               direction=direction, is_execution=True)


def _data_pin(name: str, direction: str) -> Pin:
    return Pin(name=name, cpp_type="float", direction=direction)


def test_entry_with_only_exec_not_isolated() -> None:
    """Entry 노드가 exec link로만 연결돼도 isolated 아님."""
    entry = Node(name="Entry", cls="X",
                 pins=[_exec_pin("ExecuteContext", "Output")])
    body = Node(name="Body", cls="X",
                pins=[_exec_pin("ExecuteContext", "Input"),
                      _data_pin("A", "Input"),
                      _data_pin("B", "Output")])
    consumer = Node(name="Consumer", cls="X",
                    pins=[_data_pin("B", "Input")])
    g = GraphModel(
        nodes=[entry, body, consumer],
        links=[
            Link(source_path="Entry.ExecuteContext", target_path="Body.ExecuteContext"),
            Link(source_path="Body.B", target_path="Consumer.B"),
        ],
    )
    result = analyze_data_flow(g)
    assert "Entry" not in result.isolated, (
        f"Entry는 exec link로 연결됨 — isolated 잘못 표시: {result.isolated}"
    )


def test_return_with_only_exec_not_isolated() -> None:
    """Return 노드가 exec link로만 들어와도 isolated 아님."""
    src = Node(name="Src", cls="X",
               pins=[_exec_pin("ExecOut", "Output")])
    return_node = Node(name="Return", cls="X",
                       pins=[_exec_pin("ExecIn", "Input")])
    g = GraphModel(
        nodes=[src, return_node],
        links=[
            Link(source_path="Src.ExecOut", target_path="Return.ExecIn"),
        ],
    )
    result = analyze_data_flow(g)
    assert "Return" not in result.isolated


def test_node_with_no_link_is_isolated() -> None:
    """진짜 link가 0인 노드는 isolated 유지 (회귀 없음)."""
    floating = Node(name="Floating", cls="X",
                    pins=[_data_pin("A", "Input")])
    g = GraphModel(nodes=[floating], links=[])
    result = analyze_data_flow(g)
    assert "Floating" in result.isolated


def test_data_flow_edges_unchanged() -> None:
    """isolated 검사 변경이 data_edges (exec 제외)에 영향 없음."""
    entry = Node(name="Entry", cls="X",
                 pins=[_exec_pin("ExecOut", "Output")])
    body = Node(name="Body", cls="X",
                pins=[_exec_pin("ExecIn", "Input"),
                      _data_pin("Result", "Output")])
    consumer = Node(name="Consumer", cls="X",
                    pins=[_data_pin("In", "Input")])
    g = GraphModel(
        nodes=[entry, body, consumer],
        links=[
            Link(source_path="Entry.ExecOut", target_path="Body.ExecIn"),
            Link(source_path="Body.Result", target_path="Consumer.In"),
        ],
    )
    result = analyze_data_flow(g)
    # data_edges는 exec 제외 — 1건만
    assert len(result.data_edges) == 1
    edge_paths = [(e.source_node, e.target_node) for e in result.data_edges]
    assert ("Body", "Consumer") in edge_paths
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/core/analysis/test_data_flow.py -v -k isolated`
Expected: 신규 isolated 테스트 FAIL (Entry/Return isolated로 잘못 표시).

- [ ] **Step 3: `analyze_data_flow` 수정**

`src/t3dgraph/core/analysis/data_flow.py`:

```python
def analyze_data_flow(graph: GraphModel) -> DataFlowResult:
    exec_refs = _collect_exec_pin_refs(graph)
    edges: list[DataFlowEdge] = []

    for link in graph.links:
        src = PinRef.parse(link.source_path)
        tgt = PinRef.parse(link.target_path)
        if src in exec_refs or tgt in exec_refs:
            continue
        edges.append(DataFlowEdge(source=src, target=tgt))

    inputs_of: dict[str, list[DataFlowEdge]] = {}
    outputs_of: dict[str, list[DataFlowEdge]] = {}
    for e in edges:
        outputs_of.setdefault(e.source_node, []).append(e)
        inputs_of.setdefault(e.target_node, []).append(e)

    incoming_nodes = {tgt: sorted({e.source_node for e in es})
                      for tgt, es in inputs_of.items()}
    outgoing_nodes = {src: sorted({e.target_node for e in es})
                      for src, es in outputs_of.items()}

    all_nodes = [n.name for n in graph.nodes]
    nodes_with_data = set(incoming_nodes) | set(outgoing_nodes)
    sources = sorted(n for n in nodes_with_data
                     if not incoming_nodes.get(n) and outgoing_nodes.get(n))
    sinks = sorted(n for n in nodes_with_data
                   if incoming_nodes.get(n) and not outgoing_nodes.get(n))

    # F30: isolated 판정은 모든 link 기준 — exec 연결도 "고립 아님"으로 인정
    nodes_with_any_connection: set[str] = set()
    for link in graph.links:
        nodes_with_any_connection.add(PinRef.parse(link.source_path).node)
        nodes_with_any_connection.add(PinRef.parse(link.target_path).node)
    isolated = sorted(n for n in all_nodes if n not in nodes_with_any_connection)

    return DataFlowResult(
        data_edges=edges,
        inputs_of=inputs_of,
        outputs_of=outputs_of,
        incoming_nodes=incoming_nodes,
        outgoing_nodes=outgoing_nodes,
        sinks=sinks,
        sources=sources,
        isolated=isolated,
        all_nodes=all_nodes,
    )
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/core/analysis/test_data_flow.py -v`
Expected: 전체 통과.

Run: `pytest tests -v`
Expected: 전체 통과 (기존 테스트가 Entry/Return을 isolated로 가정하면 갱신 — 보통 아님).

- [ ] **Step 5: 커밋**

```bash
git add tests/core/analysis/test_data_flow.py src/t3dgraph/core/analysis/data_flow.py
git commit -m "fix(analysis): isolated detection considers all links (incl exec) — F30 Entry/Return"
```

## 완료 후

F30 해소 — Entry/Return이 exec link로 연결돼 있으면 isolated 미표시. data_edges는 기존대로 exec 제외 유지 (의미 보존).
