# batch ⑨ ρ (rho) — F20 Fix · AssetResolver Wiring + π Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** F20 실원인(π 데이터로 확정)을 잡는다 — `RigVMFunctionReferenceNode`가 가리키는 외부 함수 라이브러리의 그래프를 `AssetResolver`로 룩업해 노드의 `subgraph`에 연결. 동시에 π improver findings(A1·A2·A3) 동승 처리.

**Architecture:** `AssetResolver`를 `RigVMGraphInterpreter`에 선택적 주입(`__init__(resolver: AssetResolver | None = None)`). `_add_node`에서 노드 cls가 `RigVMFunctionReferenceNode`이고 자체 `ContainedGraph`가 없으면 resolver로 외부 함수 룩업 → 해당 함수의 ContainedGraph를 `node.subgraph`로 연결. resolver 미주입 또는 미해결 시 `diagnostics.external_refs_unresolved`에 기록(현 동작 유지).

**Tech Stack:** Python 3.11, PySide6 (MainWindow integration), pytest.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-9-spec-2-data-state-bugs-design.md` §4.4

**Pre-condition:** master `ad934a5` 이상 — π 머지. φ 머지는 무관 (충돌 없음, σ와는 interpreter.py 공유 — 머지 순서 무관, rebase 비용 작음).

**Data-informed scope (π 데이터로 확정)**:
- Orion 샘플 `dropped=0`, `max_depth=1` → NODE_CLASS_SUFFIXES 확장·재귀 강화 **scope에서 제외**
- 실원인 = `RigVMFunctionReferenceNode` ↔ `AssetResolver` 미연결 (backlog κ-A2 동치)
- 본 슬라이스가 κ-A2 백로그 동시 해소

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/t3d/resolver.py` | 수정 (`resolve_function_reference` API 추가) |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (resolver 주입, FunctionReferenceNode → subgraph 연결, π-A2 키 통일, π-A3 폴백 제거) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (resolver를 인터프리터에 전달하는 와이어링) |
| `tests/repro/test_f20_node_preservation.py` | 수정 (π-A1 xfail 제거) |
| `tests/repro/test_f20_function_reference_subgraph.py` | 신규 (실원인 회귀 가드) |
| `tests/base/test_interpreter_diagnostics.py` | 수정 (π-A2 키 통일 단위 테스트 추가) |

---

## Task 1: π-A2 키 통일 — dropped도 suffix

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Modify: `tests/base/test_interpreter_diagnostics.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/base/test_interpreter_diagnostics.py`에 추가:

```python
def test_dropped_cls_uses_suffix_for_consistency() -> None:
    """π-A2: DroppedObject.cls도 suffix만 — extracted_per_class와 cross-reference 가능."""
    obj = T3DObject(cls="/Script/X.Foo", name="N1", properties={}, children=[])
    doc = T3DDocument(objects=[obj])
    g = RigVMGraphInterpreter().interpret(doc)
    assert g.diagnostics is not None
    dropped = g.diagnostics.objects_dropped[0]
    assert dropped.cls == "Foo", f"기대=Foo, 실제={dropped.cls}"
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_interpreter_diagnostics.py::test_dropped_cls_uses_suffix_for_consistency -v`
Expected: FAIL — 현재 `dropped.cls`가 풀 경로.

- [ ] **Step 3: 인터프리터 `_interpret_objects` 내 `DroppedObject` 생성 부분 suffix로**

`src/t3dgraph/plugins/rigvm/interpreter.py`의 `_interpret_objects`에서 `DroppedObject(..., cls=obj.cls, ...)` 3곳(unknown class, depth cap, graph at top)을 모두 다음 패턴으로:

```python
cls_suffix = (obj.cls or "").rsplit(".", 1)[-1] or None
diagnostics.objects_dropped.append(DroppedObject(
    name=obj.name or "?", cls=cls_suffix,
    reason="unknown class", parent_obj=parent_node))
```

(reason 문자열은 케이스에 맞춰 유지.)

- [ ] **Step 4: 기존 테스트 보강**

`test_unknown_class_recorded_as_dropped`가 풀 경로를 검사하면 suffix로 변경:

```python
def test_unknown_class_recorded_as_dropped() -> None:
    obj = T3DObject(cls="/Script/X.Foo", name="N1", properties={}, children=[])
    ...
    dropped_classes = [d.cls for d in g.diagnostics.objects_dropped]
    assert "Foo" in dropped_classes
    reasons = [d.reason for d in g.diagnostics.objects_dropped]
    assert "unknown class" in reasons
```

- [ ] **Step 5: 실행 — 통과 확인**

Run: `pytest tests/base/test_interpreter_diagnostics.py -v`
Expected: 전 통과.

- [ ] **Step 6: 커밋**

```bash
git add tests/base/test_interpreter_diagnostics.py src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "fix(rigvm): DroppedObject.cls uses suffix for consistency (π-A2)"
```

---

## Task 2: π-A3 — `_interpret_objects` 시그니처 강제

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`

- [ ] **Step 1: defensive 폴백 제거**

`_interpret_objects` 본문 시작에 `if diagnostics is None: diagnostics = InterpreterDiagnostics()` 줄 있으면 삭제. 시그니처는 그대로 `diagnostics: InterpreterDiagnostics`(키워드 전용, 디폴트 없음).

`_add_node`도 동일.

`interpret()` 진입점이 항상 `InterpreterDiagnostics()`를 생성하므로 호출 누락 위험 차단.

- [ ] **Step 2: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "fix(rigvm): _interpret_objects diagnostics required, no defensive fallback (π-A3)"
```

---

## Task 3: F20 xfail 제거 (π-A1)

**Files:**
- Modify: `tests/repro/test_f20_node_preservation.py`

- [ ] **Step 1: `@pytest.mark.xfail` 제거**

`tests/repro/test_f20_node_preservation.py`의 두 xfail 마커를 제거:

```python
# 변경 후
def test_no_unknown_classes_after_fix(orion_doc):
    ...

def test_no_unresolved_external_refs_after_fix(orion_doc):
    ...
```

- [ ] **Step 2: 실행 — 통과 확인**

Run: `T3DGRAPH_ORION_SAMPLE=Orion_WorkStation_Rig_Analysis/<sample>.t3d.txt pytest tests/repro/test_f20_node_preservation.py -v`
Expected: 4 passed.

- [ ] **Step 3: 커밋**

```bash
git add tests/repro/test_f20_node_preservation.py
git commit -m "test(repro): drop F20 xfail markers — π data confirms 0 unknown/unresolved (π-A1)"
```

---

## Task 4: AssetResolver 인터프리터 주입 + FunctionReferenceNode → subgraph

**Files:**
- Create: `tests/repro/test_f20_function_reference_subgraph.py`
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`
- Modify: `src/t3dgraph/core/t3d/resolver.py`
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: AssetResolver 기존 코드 확인**

`src/t3dgraph/core/t3d/resolver.py`를 읽어 현재 API와 데이터 구조 파악. `load_folder`가 `_docs_by_pkg: dict[str, T3DDocument]` 또는 비슷한 매핑을 가지는지 확인. 없으면 추가.

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/repro/test_f20_function_reference_subgraph.py`:

```python
"""F20 실원인 — FunctionReferenceNode가 외부 함수 라이브러리의 ContainedGraph를 subgraph로 보유."""
from __future__ import annotations
from pathlib import Path

import pytest

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.resolver import AssetResolver
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter


@pytest.fixture
def orion_folder() -> Path:
    p = Path("Orion_WorkStation_Rig_Analysis")
    if not p.exists():
        pytest.skip("Orion 폴더 미발견")
    return p


def test_function_reference_node_has_subgraph_with_resolver(orion_folder: Path) -> None:
    """폴더 단위 로드 시 RigVMFunctionReferenceNode가 외부 함수의 subgraph 보유."""
    resolver = AssetResolver()
    resolver.load_folder(orion_folder)
    model_path = next(orion_folder.glob("*RigVMModel.t3d.txt"))
    doc = parse_document(model_path.read_text(encoding="utf-8", errors="replace"))
    interp = RigVMGraphInterpreter(resolver=resolver)
    graph = interp.interpret(doc)

    func_refs = [n for n in graph.nodes
                 if (n.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"]
    assert func_refs, "Orion 샘플에 FunctionReferenceNode가 있어야 함"
    for fr in func_refs:
        assert fr.subgraph is not None, (
            f"FunctionReferenceNode '{fr.name}' subgraph 미연결 — F20 회귀"
        )
        assert len(fr.subgraph.nodes) > 0, (
            f"FunctionReferenceNode '{fr.name}' subgraph 비어있음"
        )


def test_function_reference_node_no_subgraph_without_resolver(orion_folder: Path) -> None:
    """resolver 미주입 시 subgraph=None — 기존 동작 보존(폴더 안 열림)."""
    model_path = next(orion_folder.glob("*RigVMModel.t3d.txt"))
    doc = parse_document(model_path.read_text(encoding="utf-8", errors="replace"))
    interp = RigVMGraphInterpreter()
    graph = interp.interpret(doc)
    func_refs = [n for n in graph.nodes
                 if (n.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"]
    for fr in func_refs:
        assert fr.subgraph is None or len(fr.subgraph.nodes) == 0
```

- [ ] **Step 3: 실행 — 실패 확인**

Run: `pytest tests/repro/test_f20_function_reference_subgraph.py -v`
Expected: `test_function_reference_node_has_subgraph_with_resolver` FAIL.

- [ ] **Step 4: 인터프리터 변경 — resolver 주입**

`src/t3dgraph/plugins/rigvm/interpreter.py`:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...core.t3d.resolver import AssetResolver


class RigVMGraphInterpreter(AbstractGraphInterpreter):
    def __init__(self, resolver: "AssetResolver | None" = None) -> None:
        self._resolver = resolver
```

`_add_node` 끝부분에 FunctionReferenceNode 처리 추가 (graph_children 처리 직후, variable ref 처리 전):

```python
# F20: FunctionReferenceNode에 자체 ContainedGraph가 없으면 resolver로 외부 함수 룩업
if (
    self._resolver is not None
    and node.subgraph is None
    and (obj.cls or "").rsplit(".", 1)[-1] == "RigVMFunctionReferenceNode"
):
    ref_path = _text(obj.properties.get("ReferencedNode"))
    if ref_path:
        ext_obj = self._resolver.resolve_function_reference(ref_path)
        if ext_obj is not None:
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
            diagnostics.external_refs_unresolved.append(ref_path)
```

- [ ] **Step 5: resolver에 `resolve_function_reference` 추가**

`src/t3dgraph/core/t3d/resolver.py`에 메서드 추가 (기존 구조 보존, 신규 메서드만):

```python
import re
from .objects import T3DObject

def resolve_function_reference(self, ref_path: str) -> T3DObject | None:
    """ReferencedNode 경로에서 외부 함수의 노드(보통 RigVMCollapseNode)를 찾는다.

    ref_path 예: "Class'/Game/.../Lib.Lib:RigVMModel.MyFunc'"
    """
    m = re.search(r"'([^']+)'", ref_path)
    inner = m.group(1) if m else ref_path
    if ":" not in inner:
        return None
    pkg_part, sub_path = inner.split(":", 1)
    # 폴더 안에서 pkg_part에 해당하는 doc 찾기 (load_folder가 _docs_by_pkg 보유 가정)
    target_doc = self._docs_by_pkg.get(pkg_part)
    if target_doc is None:
        asset_name = pkg_part.rsplit(".", 1)[-1]
        for k, d in self._docs_by_pkg.items():
            if k.endswith(asset_name) or k.endswith(f".{asset_name}"):
                target_doc = d
                break
    if target_doc is None:
        return None
    func_name = sub_path.rsplit(".", 1)[-1]
    def find_named(objects):
        for o in objects:
            if o.name == func_name:
                return o
            found = find_named(o.children)
            if found is not None:
                return found
        return None
    return find_named(target_doc.objects)
```

`load_folder`가 `_docs_by_pkg: dict[str, T3DDocument]`를 채우는지 확인. 없으면 추가:

```python
def load_folder(self, folder: Path) -> None:
    if not hasattr(self, "_docs_by_pkg"):
        self._docs_by_pkg: dict[str, T3DDocument] = {}
    # ... 기존 로직 ...
    # 파일 한 개 파싱 후
    doc = parse_document(text)
    pkg_key = derive_pkg_key(path)   # 파일명 → 패키지 키
    self._docs_by_pkg[pkg_key] = doc
```

`derive_pkg_key`는 파일명에서 UE 자산 경로(`/Game/.../Lib.Lib` 형식)를 도출. 단순화: 파일명 그대로 또는 stem.

- [ ] **Step 6: MainWindow 와이어링**

`src/t3dgraph/core/app/main_window.py`의 인터프리터 생성을 다음으로 변경:

```python
# 기존
interp = RigVMGraphInterpreter()
# 변경
interp = RigVMGraphInterpreter(resolver=self._resolver)
```

resolver가 None이어도 안전(인터프리터 디폴트).

- [ ] **Step 7: 실행 — 통과 확인**

Run: `pytest tests/repro/test_f20_function_reference_subgraph.py -v`
Expected: 2 passed.

- [ ] **Step 8: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 9: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

Orion 폴더 "에셋 폴더 열기" → FunctionReferenceNode 더블클릭 → 함수 본문 그래프 표시.

- [ ] **Step 10: 커밋**

```bash
git add tests/repro/test_f20_function_reference_subgraph.py src/t3dgraph/core/t3d/resolver.py src/t3dgraph/plugins/rigvm/interpreter.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(rigvm): FunctionReferenceNode → resolver-backed subgraph (F20, κ-A2)"
```

---

## Self-Review 체크리스트

- π-A1 xfail 마커 제거 — Task 3 ✅
- π-A2 dropped vs extracted 키 통일 — Task 1 ✅
- π-A3 defensive 폴백 제거 — Task 2 ✅
- F20 실원인 fix — Task 4 ✅
- backlog κ-A2 동시 해소 — Task 4 ✅
- PRESERVE-ALL — 노드 복원(불변식 강화) ✅
- resolver 미주입 시 기존 동작 유지 — Task 4 Step 2 ✅

---

## 완료 후

- improver 자동 리뷰 → backlog
- backlog κ-A2 해소 표시
- σ 머지 후 batch ⑨ 마감
