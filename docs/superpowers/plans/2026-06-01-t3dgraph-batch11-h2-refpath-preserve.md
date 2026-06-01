# batch ⑪ h2 — F20 ref_path 보존 (α-A2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `_extract_target_path` 실패 시 원본 `ref_path`를 `external_refs_unresolved`에 명시 보존해 디버깅성 회복.

**Architecture:** 인터프리터의 FunctionReferenceNode 처리에서 `_extract_target_path`(또는 resolver 룩업) 실패 분기 시 `external_refs_unresolved`에 raw ref_path + 사유 메타 등재.

**Spec:** §4

**Pre-condition:** master `6ebd03d` 이상. h1/h3/h4와 병렬.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (FunctionReferenceNode 처리) |
| `src/t3dgraph/core/t3d/resolver.py` | 가능: `_extract_target_path`를 public으로 노출 또는 모듈 함수로 재호출 가능하게 |
| `tests/repro/test_f20_ref_path_preserved.py` | 신규 |

---

## Task 1: ref_path 보존 메타 — TDD

- [ ] **Step 1: 테스트 작성**

`tests/repro/test_f20_ref_path_preserved.py`:

```python
"""h2 (α-A2) — _extract_target_path 실패 시 raw ref_path 보존."""
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.resolver import AssetResolver
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_ref_path_preserved_when_extract_fails() -> None:
    """비표준 ref_path → unresolved에 원본 + 사유 메타."""
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        '   ReferencedNode="ThisIsAnUnparseableRef"\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter(resolver=AssetResolver()).interpret(doc)
    assert g.diagnostics is not None
    unresolved = g.diagnostics.external_refs_unresolved
    assert any(
        "ThisIsAnUnparseableRef" in r for r in unresolved
    ), f"ref_path 정보 손실 — unresolved={unresolved}"


def test_normal_ref_path_listed_as_is_without_resolver() -> None:
    """resolver 미주입 시 정상 ref도 그대로 등재."""
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        '   ReferencedNode="Class\'/Game/Lib.Lib:RigVMModel.Func\'"\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    unresolved = g.diagnostics.external_refs_unresolved
    assert any("Class'/Game/Lib.Lib:RigVMModel.Func'" in r for r in unresolved), (
        f"정상 ref 등재 실패 — {unresolved}"
    )
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/repro/test_f20_ref_path_preserved.py -v`
Expected: FAIL — unresolved 메시지가 `(header parse failed)`로 한정되거나 ref_path 없음.

- [ ] **Step 3: 인터프리터 변경**

`src/t3dgraph/plugins/rigvm/interpreter.py`의 FunctionReferenceNode 블록 갱신:

```python
if (
    node.subgraph is None
    and (obj.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"
):
    ref_path_raw = _text(obj.properties.get("ReferencedNode"))
    if not ref_path_raw:
        ref_path_raw = self._extract_lib_node_path_from_header(obj)
    if not ref_path_raw:
        diagnostics.external_refs_unresolved.append(
            f"{obj.name or '?'} (header parse failed)"
        )
    else:
        # resolver 룩업 시도 — 실패 시 raw ref 보존
        ext_obj = None
        if self._resolver is not None:
            ext_obj = self._resolver.resolve_function_reference(ref_path_raw)
        if ext_obj is None:
            # 실패 사유 구분 — extract도 실패한 케이스
            if self._resolver is not None:
                extracted = self._resolver._extract_target_path(ref_path_raw)
                if extracted is None:
                    diagnostics.external_refs_unresolved.append(
                        f"{obj.name or '?'} (ref unparseable: {ref_path_raw})"
                    )
                else:
                    diagnostics.external_refs_unresolved.append(ref_path_raw)
            else:
                diagnostics.external_refs_unresolved.append(ref_path_raw)
        else:
            ext_graph_children = [
                c for c in ext_obj.children if t.is_graph_class(c.cls)
            ]
            diagnostics.contained_graph_count += len(ext_graph_children)
            for j, ext_child in enumerate(ext_graph_children):
                ext_sub = self._interpret_objects(
                    ext_child.children,
                    label=f"{node.name}/(ext){ext_child.name or 'graph'}",
                    parent_node=node.name,
                    diagnostics=diagnostics,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                if j == 0 and node.subgraph is None:
                    node.subgraph = ext_sub
                else:
                    node.extra_subgraphs.append(ext_sub)
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/repro/test_f20_ref_path_preserved.py -v`
Expected: 2 passed.

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 6: 커밋**

```bash
git add tests/repro/test_f20_ref_path_preserved.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "fix(rigvm): preserve raw ref_path in external_refs_unresolved (α-A2)"
```

## 완료 후

α-A2 해소.
