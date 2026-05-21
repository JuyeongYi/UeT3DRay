# Slice ζ: CLI 삼총사 (FEAT-1 --lenient + FEAT-4 --json + FEAT-6 dataflow) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** CLI를 argparse 서브커맨드(`summary`, `dataflow`)로 재편. `--lenient` 플래그로 부분 결과 보존. `--json`으로 구조화 출력.

**Architecture:** `cli.py`를 서브커맨드 디스패처 + per-subcommand 핸들러로 재편. `_load.py`(신규)에 `lenient_load` wrapper. JSON 직렬화는 `_serialize.py`에 격리.

**Tech Stack:** Python 3.11+, argparse, json, pytest.

**Spec ref:** `docs/superpowers/specs/2026-05-22-t3dgraph-batch-5-cli-trio-design.md`.

---

## 파일 구조

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/cli.py` | argparse 서브커맨드 + dispatch | 수정 |
| `src/t3dgraph/_cli/load.py` | `lenient_load` + strict_load wrapper | 신규 |
| `src/t3dgraph/_cli/serialize.py` | JSON 직렬화 (summary, dataflow) | 신규 |
| `src/t3dgraph/_cli/__init__.py` | export | 신규 |
| `tests/test_cli_lenient.py` | --lenient 동작 | 신규 |
| `tests/test_cli_json.py` | --json 출력 | 신규 |
| `tests/test_cli_dataflow.py` | dataflow 서브커맨드 | 신규 |
| `tests/test_cli_backcompat.py` | 단일 인자 호환 | 신규 |

---

### Task 1: `_cli/load.py` 모듈 — strict + lenient

**Files:**
- Create: `src/t3dgraph/_cli/__init__.py`
- Create: `src/t3dgraph/_cli/load.py`
- Create: `tests/test_cli_lenient.py`

- [ ] **Step 1: Tests**

```python
from pathlib import Path
from t3dgraph._cli.load import strict_load, lenient_load


def test_strict_load_returns_graph_for_valid(tmp_path):
    p = tmp_path / "x.t3d.txt"
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="X"\n'
        'End Object\n', encoding="utf-8")
    graph, warnings = strict_load(p)
    assert graph is not None
    assert any(n.name == "X" for n in graph.nodes)


def test_strict_load_raises_on_parse_error(tmp_path):
    import pytest
    from t3dgraph.core.t3d.objects import T3DParseError
    p = tmp_path / "bad.t3d.txt"
    p.write_text("Begin Object Class=X Name=\"Y\"\n", encoding="utf-8")
    with pytest.raises(T3DParseError):
        strict_load(p)


def test_lenient_load_returns_partial_on_parse_error(tmp_path):
    p = tmp_path / "bad.t3d.txt"
    p.write_text("Begin Object Class=X Name=\"Y\"\n", encoding="utf-8")
    graph, warnings = lenient_load(p)
    assert graph is None
    assert any("parse" in w.lower() for w in warnings)


def test_lenient_load_captures_interpreter_warnings(tmp_path):
    """interpreter가 g.warnings에 남긴 항목이 lenient_load 결과에 포함."""
    p = tmp_path / "x.t3d.txt"
    # Unknown class — generic 폴백 + warning
    p.write_text(
        'Begin Object Class=/Script/Unknown.WeirdNode Name="W"\n'
        'End Object\n', encoding="utf-8")
    graph, warnings = lenient_load(p)
    assert graph is not None
    assert any("알 수 없는 클래스" in w for w in warnings)
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

`src/t3dgraph/_cli/__init__.py`: 빈 파일 또는 export.

`src/t3dgraph/_cli/load.py`:

```python
"""CLI 로드 헬퍼 — strict/lenient 두 모드."""
from __future__ import annotations
from pathlib import Path
from ..core.t3d.document import parse_document
from ..core.t3d.objects import T3DParseError
from ..core.t3d.encoding import read_t3d_text
from ..core.registry import default_registry
from ..core.base.graph_model import GraphModel


def strict_load(path: Path) -> tuple[GraphModel, list[str]]:
    """파싱·해석 — 실패 시 예외 raise. 반환은 (graph, warnings)."""
    doc = parse_document(read_t3d_text(path))
    plugin = default_registry().detect(doc)
    graph = plugin.interpreter_factory().interpret(doc)
    return graph, list(graph.warnings)


def lenient_load(path: Path) -> tuple[GraphModel | None, list[str]]:
    """파싱·해석 — 실패 시 warning에 누적하고 부분 결과 반환."""
    warnings: list[str] = []
    try:
        doc = parse_document(read_t3d_text(path))
    except (UnicodeDecodeError, T3DParseError) as e:
        warnings.append(f"parse 실패: {e}")
        return None, warnings
    try:
        plugin = default_registry().detect(doc)
    except LookupError as e:
        warnings.append(f"plugin 탐지 실패: {e}")
        return None, warnings
    try:
        graph = plugin.interpreter_factory().interpret(doc)
    except Exception as e:
        warnings.append(f"해석 실패: {e}")
        return None, warnings
    warnings.extend(graph.warnings)
    return graph, warnings
```

- [ ] **Step 4: Run — pass**

```
pytest tests/test_cli_lenient.py -v
```

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/_cli/__init__.py src/t3dgraph/_cli/load.py tests/test_cli_lenient.py
git commit -m "feat(cli): strict/lenient load helpers (FEAT-1 prep)"
```

---

### Task 2: `_cli/serialize.py` — JSON 직렬화

**Files:**
- Create: `src/t3dgraph/_cli/serialize.py`
- Create: `tests/test_cli_json.py`

- [ ] **Step 1: Tests**

```python
import json
from t3dgraph._cli.serialize import summary_dict, dataflow_dict
from t3dgraph.core.base.graph_model import GraphModel, Node, Pin, Link
from t3dgraph.core.analysis.bundle import run as run_analyses


def _simple_graph():
    return GraphModel(
        nodes=[
            Node(name="A", cls="X", pins=[Pin(name="O", cpp_type="float", direction="Output")]),
            Node(name="B", cls="X", pins=[Pin(name="I", cpp_type="float", direction="Input")]),
        ],
        links=[Link(source_path="A.O", target_path="B.I")],
    )


def test_summary_dict_has_expected_keys():
    g = _simple_graph()
    b = run_analyses(g)
    d = summary_dict("rigvm", g, b)
    assert d["graph_type"] == "rigvm"
    assert d["nodes"]["total"] == 2
    assert d["links"] == 1
    assert "execution" in d
    assert "warnings" in d


def test_summary_dict_is_json_serializable():
    g = _simple_graph()
    b = run_analyses(g)
    s = json.dumps(summary_dict("rigvm", g, b))
    parsed = json.loads(s)
    assert parsed["graph_type"] == "rigvm"


def test_dataflow_dict_emits_pin_paths():
    g = _simple_graph()
    b = run_analyses(g)
    d = dataflow_dict(b.data_flow)
    assert d["data_edges"] == [{"source": "A.O", "target": "B.I"}]
    assert d["incoming_nodes"] == {"B": ["A"]}
    assert d["outgoing_nodes"] == {"A": ["B"]}
    assert "X" not in d["isolated"]  # 없는 노드는 isolated 아님
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

`src/t3dgraph/_cli/serialize.py`:

```python
"""CLI JSON 직렬화 — summary / dataflow."""
from __future__ import annotations
from ..core.base.graph_model import GraphModel
from ..core.analysis.bundle import AnalysisBundle
from ..core.analysis.data_flow import DataFlowResult


def summary_dict(graph_type: str, graph: GraphModel,
                 bundle: AnalysisBundle) -> dict:
    return {
        "graph_type": graph_type,
        "nodes": {
            "total": len(graph.nodes),
            "generic": sum(1 for n in graph.nodes if n.is_generic),
        },
        "links": len(graph.links),
        "variable_refs": len(graph.variable_refs),
        "external_refs": len(graph.external_refs),
        "execution": {
            "edges": len(bundle.flow.execution_edges),
            "convergence_points": list(bundle.flow.convergence_points),
            "branch_points": list(bundle.flow.branch_points),
            "steps": len(bundle.execution_order),
        },
        "warnings": list(graph.warnings),
    }


def dataflow_dict(result: DataFlowResult) -> dict:
    return {
        "data_edges": [
            {"source": e.source.full, "target": e.target.full}
            for e in result.data_edges
        ],
        "sinks": list(result.sinks),
        "sources": list(result.sources),
        "isolated": list(result.isolated),
        "incoming_nodes": {k: list(v) for k, v in result.incoming_nodes.items()},
        "outgoing_nodes": {k: list(v) for k, v in result.outgoing_nodes.items()},
        "all_nodes": list(result.all_nodes),
    }
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/_cli/serialize.py tests/test_cli_json.py
git commit -m "feat(cli): summary/dataflow JSON serializers (FEAT-4, FEAT-6 prep)"
```

---

### Task 3: cli.py 서브커맨드 재편

**Files:**
- Modify: `src/t3dgraph/cli.py`
- Create: `tests/test_cli_dataflow.py`
- Create: `tests/test_cli_backcompat.py`

- [ ] **Step 1: Tests**

`tests/test_cli_dataflow.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


def _sample(tmp_path: Path) -> Path:
    p = tmp_path / "x.t3d.txt"
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
        '    CPPType="float"\n    Direction=Output\n'
        '  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="B"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="I"\n'
        '    CPPType="float"\n    Direction=Input\n'
        '  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
        '  SourcePinPath="A.O"\n  TargetPinPath="B.I"\n'
        'End Object\n',
        encoding="utf-8",
    )
    return p


def test_dataflow_subcommand_json(tmp_path):
    p = _sample(tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "dataflow", str(p), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert {"source": "A.O", "target": "B.I"} in data["data_edges"]


def test_dataflow_subcommand_text(tmp_path):
    p = _sample(tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "dataflow", str(p)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr
    assert "A.O" in r.stdout
    assert "B.I" in r.stdout
```

`tests/test_cli_backcompat.py`:

```python
import subprocess
import sys


def test_single_file_arg_works(tmp_path):
    """t3dgraph <file> 단일 인자 — summary와 동일 동작."""
    p = tmp_path / "x.t3d.txt"
    p.write_text(
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="X"\n'
        'End Object\n', encoding="utf-8")
    r1 = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", str(p)],
        capture_output=True, text=True, encoding="utf-8",
    )
    r2 = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "summary", str(p)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r1.returncode == 0
    assert r2.returncode == 0
    assert r1.stdout == r2.stdout


def test_lenient_flag_warns_on_bad_parse(tmp_path):
    p = tmp_path / "bad.t3d.txt"
    p.write_text('Begin Object Class=X Name="X"\n', encoding="utf-8")    # 닫는 End Object 없음
    r = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "summary", str(p), "--lenient"],
        capture_output=True, text=True, encoding="utf-8",
    )
    # lenient: exit 0 + warning (strict면 비-0)
    assert r.returncode == 0
    assert "warning" in r.stdout.lower() or "warning" in r.stderr.lower() or "실패" in r.stdout or "실패" in r.stderr


def test_strict_default_fails_on_bad(tmp_path):
    p = tmp_path / "bad.t3d.txt"
    p.write_text('Begin Object Class=X Name="X"\n', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "summary", str(p)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode != 0
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement — cli.py 재작성**

```python
"""t3dgraph CLI — summary / dataflow 서브커맨드 + lenient/json 옵션."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .core.t3d.objects import T3DParseError
from .core.analysis.bundle import run as run_analyses
from ._cli.load import strict_load, lenient_load
from ._cli.serialize import summary_dict, dataflow_dict


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="t3dgraph",
                                     description="UE T3D 그래프 파서·분석")
    subs = parser.add_subparsers(dest="subcommand")

    p_sum = subs.add_parser("summary", help="그래프 요약(노드/링크/실행 흐름)")
    p_sum.add_argument("file")
    p_sum.add_argument("--lenient", action="store_true")
    p_sum.add_argument("--json", action="store_true")

    p_df = subs.add_parser("dataflow", help="데이터 흐름 분석 덤프")
    p_df.add_argument("file")
    p_df.add_argument("--lenient", action="store_true")
    p_df.add_argument("--json", action="store_true")

    return parser


def _load(path: Path, lenient: bool):
    if lenient:
        return lenient_load(path)
    return strict_load(path)


def _resolve_plugin_id(graph):
    """원래는 plugin.id를 따왔지만 strict_load는 graph만 반환 — 후처리에서 cls suffix로 추정."""
    if not graph or not graph.nodes:
        return "unknown"
    sample = graph.nodes[0].cls or ""
    if "RigVM" in sample:
        return "rigvm"
    return "unknown"


def _cmd_summary(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2
    try:
        graph, warnings = _load(path, args.lenient)
    except (UnicodeDecodeError, T3DParseError, LookupError) as e:
        print(f"실패: {e}", file=sys.stderr)
        return 4
    if graph is None:
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        return 0 if args.lenient else 4
    bundle = run_analyses(graph)
    plugin_id = _resolve_plugin_id(graph)
    if args.json:
        d = summary_dict(plugin_id, graph, bundle)
        d["warnings"] = warnings
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print(f"graph type: {plugin_id}")
        print(f"nodes: {len(graph.nodes)}  (generic: {sum(n.is_generic for n in graph.nodes)})")
        print(f"links: {len(graph.links)}")
        print(f"variable refs: {len(graph.variable_refs)}")
        print(f"external refs: {len(graph.external_refs)}")
        print(f"execution edges: {len(bundle.flow.execution_edges)}")
        print(f"convergence points (fan-in): {bundle.flow.convergence_points or '없음'}")
        print(f"execution steps: {len(bundle.execution_order)}")
        for w in warnings:
            print(f"  warning: {w}", file=sys.stderr)
    return 0


def _cmd_dataflow(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2
    try:
        graph, warnings = _load(path, args.lenient)
    except (UnicodeDecodeError, T3DParseError, LookupError) as e:
        print(f"실패: {e}", file=sys.stderr)
        return 4
    if graph is None:
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        return 0 if args.lenient else 4
    bundle = run_analyses(graph)
    if args.json:
        d = dataflow_dict(bundle.data_flow)
        d["warnings"] = warnings
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        r = bundle.data_flow
        print(f"data edges: {len(r.data_edges)}")
        for e in r.data_edges:
            print(f"  {e.source.full} -> {e.target.full}")
        print(f"sources: {', '.join(r.sources) or '없음'}")
        print(f"sinks: {', '.join(r.sinks) or '없음'}")
        print(f"isolated: {', '.join(r.isolated) or '없음'}")
    return 0


def run(argv: list[str]) -> int:
    # 단일 인자 호환 — 첫 인자가 파일이면 summary로 라우팅.
    if argv and not argv[0] in ("summary", "dataflow", "-h", "--help"):
        if Path(argv[0]).exists():
            argv = ["summary"] + argv
    parser = _make_parser()
    args = parser.parse_args(argv)
    if args.subcommand == "summary":
        return _cmd_summary(args)
    if args.subcommand == "dataflow":
        return _cmd_dataflow(args)
    parser.print_help()
    return 2


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — pass**

```
pytest tests/test_cli_dataflow.py tests/test_cli_backcompat.py tests/test_cli_json.py -v
```

- [ ] **Step 5: Commit**

```
git add src/t3dgraph/cli.py tests/test_cli_dataflow.py tests/test_cli_backcompat.py tests/test_cli_json.py
git commit -m "feat(cli): subcommands (summary/dataflow) + --lenient + --json (FEAT-1, 4, 6)"
```

---

### Task 4: 회귀

```
pytest tests/ -v
```
Expected: PASS.

---

## 완료 정의

- [ ] Task 1-4 PASS
- [ ] `t3dgraph summary <file>` / `t3dgraph dataflow <file>` 두 서브커맨드
- [ ] `--lenient` 시 부분 결과 + warning, exit 0
- [ ] `--json` 시 구조화 출력
- [ ] `t3dgraph <file>` 단일 인자 호환
