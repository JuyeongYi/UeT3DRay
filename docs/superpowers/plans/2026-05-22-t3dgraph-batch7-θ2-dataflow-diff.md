# Slice θ-2: dataflow diff CLI (FEAT-7) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 두 `.t3d` 파일 간 데이터 흐름 차이를 sink 기준으로 비교하는 CLI 서브커맨드 `t3dgraph diff`.

**Architecture:** `core/analysis/data_flow_diff.py`(신규) — `diff_data_flow(a, b) -> DataFlowDiff`. cli.py에 `diff` 서브커맨드 추가.

**Spec ref:** `2026-05-22-t3dgraph-batch-7-analysis-vis-design.md` §θ-2.

---

### Task 1: 분석기 — `diff_data_flow`

**Files:**
- Create: `src/t3dgraph/core/analysis/data_flow_diff.py`
- Create: `tests/core/analysis/test_data_flow_diff.py`

- [ ] **Step 1: Tests**

```python
from t3dgraph.core.analysis.data_flow import DataFlowResult
from t3dgraph.core.analysis.data_flow_diff import diff_data_flow, DataFlowDiff


def _result(sinks, incoming):
    return DataFlowResult(
        sinks=sinks, sources=[], isolated=[],
        incoming_nodes=incoming, outgoing_nodes={},
        all_nodes=list({n for ns in incoming.values() for n in ns} | set(sinks)),
        data_edges=[], inputs_of={}, outputs_of={},
    )


def test_sinks_only_in_a():
    a = _result(["X", "Y"], {"X": ["A"], "Y": ["B"]})
    b = _result(["X"], {"X": ["A"]})
    d = diff_data_flow(a, b)
    assert d.sinks_only_in_a == ["Y"]
    assert d.sinks_only_in_b == []
    assert d.sinks_common == ["X"]


def test_per_sink_added_ancestor():
    a = _result(["S"], {"S": ["A"]})
    b = _result(["S"], {"S": ["A", "B"], "B": []})
    d = diff_data_flow(a, b)
    assert "B" in d.per_sink["S"].added_ancestors


def test_per_sink_removed_ancestor():
    a = _result(["S"], {"S": ["A", "B"]})
    b = _result(["S"], {"S": ["A"]})
    d = diff_data_flow(a, b)
    assert "B" in d.per_sink["S"].removed_ancestors


def test_per_sink_depth_change():
    a = _result(["S"], {"S": ["A"], "A": []})
    b = _result(["S"], {"S": ["B"], "B": ["A"], "A": []})
    d = diff_data_flow(a, b)
    # A는 양쪽에 있지만 깊이가 다름 (1 vs 2)
    assert "A" in d.per_sink["S"].depth_changes
    da, db = d.per_sink["S"].depth_changes["A"]
    assert da == 1
    assert db == 2
```

- [ ] **Step 2: Implement**

```python
"""두 DataFlowResult 사이의 sink별 ancestor diff."""
from __future__ import annotations
from dataclasses import dataclass, field
from .data_flow import DataFlowResult
from .compute_trace import compute_trace


@dataclass
class PerSinkDiff:
    added_ancestors: list[str] = field(default_factory=list)
    removed_ancestors: list[str] = field(default_factory=list)
    depth_changes: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class DataFlowDiff:
    sinks_only_in_a: list[str] = field(default_factory=list)
    sinks_only_in_b: list[str] = field(default_factory=list)
    sinks_common: list[str] = field(default_factory=list)
    per_sink: dict[str, PerSinkDiff] = field(default_factory=dict)


def _depth_map(sink: str, incoming: dict[str, list[str]]) -> dict[str, int]:
    levels = compute_trace(sink, incoming)
    out: dict[str, int] = {}
    for lv in levels:
        for n in lv.nodes:
            out.setdefault(n, lv.depth)
    return out


def diff_data_flow(a: DataFlowResult, b: DataFlowResult) -> DataFlowDiff:
    sa = set(a.sinks)
    sb = set(b.sinks)
    diff = DataFlowDiff(
        sinks_only_in_a=sorted(sa - sb),
        sinks_only_in_b=sorted(sb - sa),
        sinks_common=sorted(sa & sb),
    )
    for s in diff.sinks_common:
        da = _depth_map(s, a.incoming_nodes)
        db = _depth_map(s, b.incoming_nodes)
        added = sorted(set(db) - set(da))
        removed = sorted(set(da) - set(db))
        depth_changes = {
            n: (da[n], db[n]) for n in (set(da) & set(db))
            if da[n] != db[n]
        }
        diff.per_sink[s] = PerSinkDiff(
            added_ancestors=added,
            removed_ancestors=removed,
            depth_changes=depth_changes,
        )
    return diff
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/analysis/data_flow_diff.py tests/core/analysis/test_data_flow_diff.py
git commit -m "feat(analysis): data_flow_diff per-sink ancestor diff (FEAT-7)"
```

---

### Task 2: CLI `diff` 서브커맨드

**Files:**
- Modify: `src/t3dgraph/cli.py`
- Modify: `src/t3dgraph/_cli/serialize.py`
- Create: `tests/test_cli_diff.py`

- [ ] **Step 1: serialize 확장**

`_cli/serialize.py`:

```python
from ..core.analysis.data_flow_diff import DataFlowDiff


def diff_dict(d: DataFlowDiff) -> dict:
    return {
        "sinks_only_in_a": list(d.sinks_only_in_a),
        "sinks_only_in_b": list(d.sinks_only_in_b),
        "sinks_common": list(d.sinks_common),
        "per_sink": {
            s: {
                "added_ancestors": v.added_ancestors,
                "removed_ancestors": v.removed_ancestors,
                "depth_changes": {n: list(pair) for n, pair in v.depth_changes.items()},
            }
            for s, v in d.per_sink.items()
        },
    }
```

- [ ] **Step 2: cli.py 서브커맨드 추가**

```python
# _make_parser에 추가
p_diff = subs.add_parser("diff", help="두 파일의 데이터 흐름 diff")
p_diff.add_argument("file_a")
p_diff.add_argument("file_b")
p_diff.add_argument("--lenient", action="store_true")
p_diff.add_argument("--json", action="store_true")


def _cmd_diff(args) -> int:
    from .core.analysis.data_flow_diff import diff_data_flow
    from ._cli.serialize import diff_dict
    pa = Path(args.file_a); pb = Path(args.file_b)
    for p in (pa, pb):
        if not p.is_file():
            print(f"파일을 찾을 수 없습니다: {p}", file=sys.stderr)
            return 2
    try:
        ga, wa = _load(pa, args.lenient)
        gb, wb = _load(pb, args.lenient)
    except (UnicodeDecodeError, T3DParseError, LookupError) as e:
        print(f"실패: {e}", file=sys.stderr)
        return 4
    if ga is None or gb is None:
        for w in wa + wb:
            print(f"warning: {w}", file=sys.stderr)
        return 0 if args.lenient else 4
    from .core.analysis.bundle import run as run_analyses
    ba = run_analyses(ga); bb = run_analyses(gb)
    d = diff_data_flow(ba.data_flow, bb.data_flow)
    if args.json:
        print(json.dumps(diff_dict(d), ensure_ascii=False, indent=2))
    else:
        print(f"sinks only in A: {', '.join(d.sinks_only_in_a) or '(없음)'}")
        print(f"sinks only in B: {', '.join(d.sinks_only_in_b) or '(없음)'}")
        print(f"sinks common: {len(d.sinks_common)}")
        for s, v in d.per_sink.items():
            if not (v.added_ancestors or v.removed_ancestors or v.depth_changes):
                continue
            print(f"  {s}:")
            if v.added_ancestors:
                print(f"    +ancestors: {', '.join(v.added_ancestors)}")
            if v.removed_ancestors:
                print(f"    -ancestors: {', '.join(v.removed_ancestors)}")
            if v.depth_changes:
                for n, (da, db) in v.depth_changes.items():
                    print(f"    ~depth {n}: {da} → {db}")
    return 0


# run에 dispatch 추가
if args.subcommand == "diff":
    return _cmd_diff(args)
```

- [ ] **Step 3: Test**

```python
import subprocess, sys, json
from pathlib import Path


def _make_file(p: Path, body: str):
    p.write_text(body, encoding="utf-8")


def test_diff_basic(tmp_path):
    a = tmp_path / "a.t3d.txt"
    b = tmp_path / "b.t3d.txt"
    _make_file(a,
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
        '    CPPType="float"\n    Direction=Output\n  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="S"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="I"\n'
        '    CPPType="float"\n    Direction=Input\n  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
        '  SourcePinPath="A.O"\n  TargetPinPath="S.I"\n'
        'End Object\n')
    _make_file(b,
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="A"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
        '    CPPType="float"\n    Direction=Output\n  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="B"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="O"\n'
        '    CPPType="float"\n    Direction=Output\n  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMUnitNode Name="S"\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="I"\n'
        '    CPPType="float"\n    Direction=Input\n  End Object\n'
        '  Begin Object Class=/Script/RigVMDeveloper.RigVMPin Name="J"\n'
        '    CPPType="float"\n    Direction=Input\n  End Object\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L0"\n'
        '  SourcePinPath="A.O"\n  TargetPinPath="S.I"\n'
        'End Object\n'
        'Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L1"\n'
        '  SourcePinPath="B.O"\n  TargetPinPath="S.J"\n'
        'End Object\n')
    r = subprocess.run(
        [sys.executable, "-m", "t3dgraph.cli", "diff", str(a), str(b), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert "S" in data["sinks_common"]
    assert "B" in data["per_sink"]["S"]["added_ancestors"]
```

- [ ] **Step 4: Run·Commit**

```
git add src/t3dgraph/cli.py src/t3dgraph/_cli/serialize.py tests/test_cli_diff.py
git commit -m "feat(cli): diff subcommand for two t3d files (FEAT-7)"
```

---

### Task 3: 회귀

```
pytest tests/ -v
```

---

## 완료 정의

- [ ] Task 1-3 PASS
- [ ] `diff_data_flow(a, b)` 함수
- [ ] `t3dgraph diff <a> <b>` 서브커맨드 (--json)
