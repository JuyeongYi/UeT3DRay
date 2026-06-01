# batch ⑩ α (alpha) — F20 Stability (ρ-A1 + ρ-A3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** F20 fix가 silent miss되는 두 함정 차단 — resolver 정규식이 UE redirect 체인·메타 섞임에 견고, `ReferencedFunctionHeader` 구조 변형 시 `external_refs_unresolved`에 명시 등재.

**Architecture:** `AssetResolver._extract_target_path` 신설 — `Class'...'` 명시 패턴 → 마지막 quoted segment → raw path 우선순위. `RigVMGraphInterpreter`의 FunctionReferenceNode 처리에 헤더 구조 폴백 + 명시 등재 추가.

**Tech Stack:** Python 3.11 (`re`), pytest. 외부 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-10-hotfix-design.md` §3

**Pre-condition:** master `d07a130` 이상. ο·υ·χ·ψ·ω와 병렬 가능 (interpreter.py·resolver.py 일부 공유 — 작은 패치라 rebase 비용 적음).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/t3d/resolver.py` | 수정 (`_extract_target_path` 신설 + `resolve_function_reference` 위임) |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (FunctionReferenceNode 처리에 헤더 폴백 + 명시 등재) |
| `tests/base/test_resolver_extract_target.py` | 신규 |
| `tests/repro/test_f20_function_reference_subgraph.py` | 확장 (헤더 폴백 케이스) |

---

## Task 1: `_extract_target_path` helper — TDD

**Files:**
- Create: `tests/base/test_resolver_extract_target.py`
- Modify: `src/t3dgraph/core/t3d/resolver.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/base/test_resolver_extract_target.py`:

```python
"""α (ρ-A1) — UE ref 경로 추출 정규식 강도."""
from __future__ import annotations

from t3dgraph.core.t3d.resolver import AssetResolver


def test_extract_class_pattern() -> None:
    """Class'...' 명시 패턴 우선 — 단순 케이스."""
    r = AssetResolver()
    assert r._extract_target_path("Class'/Game/Lib.Lib:RigVMModel.F'") == \
           "/Game/Lib.Lib:RigVMModel.F"


def test_extract_redirect_chain_takes_last_quoted() -> None:
    """Redirect 체인에서 마지막 quoted segment(타겟)."""
    r = AssetResolver()
    raw = "Redirect'/Old.Old:RigVMModel.G'->'/Game/Lib.Lib:RigVMModel.F'"
    assert r._extract_target_path(raw) == "/Game/Lib.Lib:RigVMModel.F"


def test_extract_class_pattern_in_redirect() -> None:
    """Redirect 체인에 Class'...'가 있으면 그것을 우선."""
    r = AssetResolver()
    raw = "Redirect'/Old.Old:RigVMModel.G'->'Class'/Game/Lib.Lib:RigVMModel.F''"
    assert r._extract_target_path(raw) == "/Game/Lib.Lib:RigVMModel.F"


def test_extract_raw_path_no_quotes() -> None:
    """quoted 없이 raw 경로 — colon 포함이면 그대로."""
    r = AssetResolver()
    assert r._extract_target_path("/Game/Lib.Lib:RigVMModel.F") == \
           "/Game/Lib.Lib:RigVMModel.F"


def test_extract_invalid_returns_none() -> None:
    """quoted 없고 colon도 없으면 None."""
    assert AssetResolver()._extract_target_path("not a ref") is None


def test_extract_empty_string() -> None:
    assert AssetResolver()._extract_target_path("") is None
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_resolver_extract_target.py -v`
Expected: FAIL — `_extract_target_path` 미존재.

- [ ] **Step 3: `_extract_target_path` 구현**

`src/t3dgraph/core/t3d/resolver.py` `AssetResolver` 클래스에 메서드 추가 (상단 `import re` 있는지 확인, 없으면 추가):

```python
import re

class AssetResolver:
    ...

    def _extract_target_path(self, ref_path: str) -> str | None:
        """UE ref 경로에서 실제 타겟 경로 추출.

        형식 가능성:
        1. "Class'/Game/.../Lib.Lib:RigVMModel.Func'"       — 단일 quoted
        2. "Redirect'...'->'Class'/Game/.../Lib.Lib:...'"   — redirect 체인
        3. "/Game/.../Lib.Lib:RigVMModel.Func"              — quoted 없음
        """
        if not ref_path:
            return None
        m = re.search(r"Class'([^']+)'", ref_path)
        if m:
            return m.group(1)
        quoted = re.findall(r"'([^']+)'", ref_path)
        if quoted:
            return quoted[-1]
        if ":" in ref_path:
            return ref_path
        return None
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/base/test_resolver_extract_target.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/base/test_resolver_extract_target.py src/t3dgraph/core/t3d/resolver.py
git commit -m "feat(resolver): _extract_target_path with Class/quoted/raw priority (ρ-A1)"
```

---

## Task 2: `resolve_function_reference`가 `_extract_target_path` 사용하도록 변경

**Files:**
- Modify: `src/t3dgraph/core/t3d/resolver.py`

- [ ] **Step 1: 기존 정규식 줄을 helper 호출로 교체**

`resolve_function_reference` 메서드의 inner 추출 부분:

```python
# 변경 전
m = re.search(r"'([^']+)'", ref_path)
inner = m.group(1) if m else ref_path

# 변경 후
inner = self._extract_target_path(ref_path)
if inner is None:
    return None
```

- [ ] **Step 2: 기존 F20 repro 회귀 확인 (Orion 샘플 있으면)**

Run: `T3DGRAPH_ORION_SAMPLE=Orion_WorkStation_Rig_Analysis/<sample>.t3d.txt pytest tests/repro/test_f20_function_reference_subgraph.py -v`
Expected: 기존 통과 케이스 그대로 PASS (Orion ref가 단일 quoted라 새 helper도 같은 결과).

- [ ] **Step 3: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/core/t3d/resolver.py
git commit -m "refactor(resolver): use _extract_target_path in resolve_function_reference (ρ-A1)"
```

---

## Task 3: 헤더 구조 폴백 + 명시 등재 (ρ-A3)

**Files:**
- Create: `tests/repro/test_f20_header_fallback.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/repro/test_f20_header_fallback.py`:

```python
"""α (ρ-A3) — ReferencedFunctionHeader 구조 폴백 + 명시 등재."""
from __future__ import annotations

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


def test_header_parse_failure_recorded_as_unresolved() -> None:
    """FunctionReferenceNode가 ReferencedNode·header 모두 없으면
    external_refs_unresolved에 'header parse failed' 사유로 명시 등재."""
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    unresolved = g.diagnostics.external_refs_unresolved
    assert any("header parse failed" in r and "FR1" in r for r in unresolved), (
        f"FR1 미등재 — silent miss (ρ-A3 회귀). unresolved={unresolved}"
    )


def test_header_with_referenced_node_uses_extracted_path() -> None:
    """ReferencedNode 속성이 있으면 정상 추출 — 회귀 없음."""
    src = (
        'Begin Object Name="FR1" '
        'Class=/Script/RigVMDeveloper.RigVMFunctionReferenceNode\n'
        '   ReferencedNode="Class\'/Game/Lib.Lib:RigVMModel.Func\'"\n'
        'End Object\n'
    )
    doc = parse_document(src)
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    # resolver 없으니 unresolved에 등재되지만 사유는 "header parse failed"가 아니어야 함
    # (정상 경로 추출 후 resolver 미주입으로 실패)
    unresolved = g.diagnostics.external_refs_unresolved
    assert not any("header parse failed" in r for r in unresolved)
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/repro/test_f20_header_fallback.py -v`
Expected: FAIL — 헤더 fallback 미구현.

- [ ] **Step 3: 인터프리터 FunctionReferenceNode 처리 강화**

`src/t3dgraph/plugins/rigvm/interpreter.py`의 `_add_node` 내 FunctionReferenceNode 블록을 다음으로 교체:

```python
# F20: FunctionReferenceNode에 자체 ContainedGraph가 없으면 resolver로 외부 함수 룩업
if (
    node.subgraph is None
    and (obj.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"
):
    ref_path = _text(obj.properties.get("ReferencedNode"))
    if not ref_path:
        ref_path = self._extract_lib_node_path_from_header(obj)
    if not ref_path:
        # 어느 경로로도 못 뽑으면 명시 등재 — silent miss 차단
        diagnostics.external_refs_unresolved.append(
            f"{obj.name or '?'} (header parse failed)"
        )
    elif self._resolver is not None:
        ext_obj = self._resolver.resolve_function_reference(ref_path)
        if ext_obj is None:
            diagnostics.external_refs_unresolved.append(ref_path)
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
    else:
        # resolver 없으면 ref_path만 등재 (사용자가 폴더를 안 열은 정상 상태)
        diagnostics.external_refs_unresolved.append(ref_path)
```

`_extract_lib_node_path_from_header` helper 추가 (메서드 같은 클래스 내):

```python
def _extract_lib_node_path_from_header(self, obj: T3DObject) -> str | None:
    """ReferencedFunctionHeader → LibraryNodePath 텍스트 추출.

    알려진 경로(header.LibraryPointer.LibraryNodePath) 우선,
    실패 시 generic walk으로 'LibraryNodePath' 키 검색.
    """
    header = obj.properties.get("ReferencedFunctionHeader")
    if not isinstance(header, Struct):
        return None
    # 알려진 경로
    known = self._walk_struct(header, ("LibraryPointer", "LibraryNodePath"))
    if known is not None:
        return known
    # generic walk
    return self._walk_struct_find_key(header, "LibraryNodePath")


def _walk_struct(self, value, path: tuple[str, ...]) -> str | None:
    """tuple의 키 시퀀스를 따라 struct 내려가서 텍스트 반환."""
    cur = value
    for key in path:
        if not isinstance(cur, Struct):
            return None
        cur = next((v for k, v in cur.items if k == key), None)
        if cur is None:
            return None
    return _text(cur)


def _walk_struct_find_key(self, value, target_key: str) -> str | None:
    """struct 트리에서 target_key 첫 매치 텍스트 반환 (generic fallback)."""
    if not isinstance(value, Struct):
        return None
    for k, v in value.items:
        if k == target_key:
            text = _text(v)
            if text:
                return text
        if isinstance(v, Struct):
            found = self._walk_struct_find_key(v, target_key)
            if found:
                return found
    return None
```

상단 import에 `Struct` 추가 확인 (`from ...core.t3d.values import Value, Scalar, QuotedString, Struct`).

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/repro/test_f20_header_fallback.py -v`
Expected: 2 passed

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과. Orion 샘플 케이스도 그대로 작동.

- [ ] **Step 6: 커밋**

```bash
git add tests/repro/test_f20_header_fallback.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "feat(rigvm): F20 header fallback + explicit unresolved listing (ρ-A3)"
```

---

## Self-Review 체크리스트

- Spec §3.1.1 정규식 우선순위(Class > 마지막 quoted > raw) — Task 1 ✅
- Spec §3.1.2 헤더 구조 fallback + 명시 등재 — Task 3 ✅
- Spec §3.2 테스트 4종(Class·redirect·raw·header 실패) — Task 1 + Task 3 ✅
- PRESERVE-ALL — 노드 추가만 ✅
- 회귀 가드 — Orion 단일 quoted 케이스 — Task 2 Step 2 ✅

---

## 완료 후

머지 후:
- improver 자동 리뷰 → backlog
- F20 silent miss 차단 완료. `project_f20_resolver_regex_fragile.md` memory 상태 갱신 (해소됨).
- ω·ψ 머지 시 충돌 없음 (다른 함수)
