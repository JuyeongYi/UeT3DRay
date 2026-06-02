# batch ⑬ g6 — Parser 재귀 머지 (F21 핀 중복 + F29 링크 누락 근본 원인) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `parse_document`가 모든 nesting level에서 sibling 중복 머지. T3D 2-패스 직렬화(선언 + 정의)가 단일 부모 내부에서 나타나는 경우 — 현재 머지 안 됨 → 핀이 2배수로 보이고 Direction이 None (선언) + 정의 분기로 분리됨.

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-13-visual-fixes-design.md` §11(추가 예정)

**Pre-condition:** master `f8fa09d` 이상. **이 패치가 F21/F22/F23/F29 다수에 영향** — 다른 g1~g5 슬라이스보다 우선 검토.

**Why critical:**
- 사용자가 본 "출력 핀이 입출력에 모두" = 같은 이름 두 Pin 객체(선언 Direction=None + 정의 Direction=Output) → 첫 개는 LEFT, 둘째 개는 RIGHT
- F29 서브그래프 실행 링크 누락 = 같은 패턴이 RigVMLink에도 발생, 선언 단계 link는 SourcePinPath/TargetPinPath 미설정 → `_add_link` skip

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/t3d/document.py` | 수정 (`_recursive_dedupe` 추가, `parse_document` 호출) |
| `tests/core/t3d/test_document_merge.py` | 신규 (재귀 머지 검증 + 회귀 가드) |

---

## Task 1: 재귀 sibling 머지 — TDD

**Files:**
- Create: `tests/core/t3d/test_document_merge.py`
- Modify: `src/t3dgraph/core/t3d/document.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/t3d/test_document_merge.py`:

```python
"""g6 — parse_document 재귀 머지 (T3D 2-패스 직렬화 단일 부모 내부)."""
from __future__ import annotations

from t3dgraph.core.t3d.document import parse_document
from t3dgraph.core.t3d.values import Scalar


def test_nested_dedupe_same_parent() -> None:
    """단일 부모 안에 같은 name이 두 번 나타나면 머지."""
    src = (
        'Begin Object Class=/Script/X.Node Name="N"\n'
        '   Begin Object Class=/Script/X.Pin Name="P"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="Q"\n'
        '   End Object\n'
        '   Begin Object Name="P"\n'
        '      Direction=Output\n'
        '   End Object\n'
        '   Begin Object Name="Q"\n'
        '      Direction=Input\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    assert len(doc.objects) == 1
    n = doc.objects[0]
    # 중복 머지 — 자식 2개, 각각 cls + Direction 모두 설정됨
    assert len(n.children) == 2
    p = next(c for c in n.children if c.name == "P")
    assert p.cls == "/Script/X.Pin"
    assert isinstance(p.properties.get("Direction"), Scalar)
    assert p.properties["Direction"].text == "Output"
    q = next(c for c in n.children if c.name == "Q")
    assert q.cls == "/Script/X.Pin"
    assert q.properties["Direction"].text == "Input"


def test_deeply_nested_dedupe() -> None:
    """다중 깊이 nesting에서도 머지."""
    src = (
        'Begin Object Name="A"\n'
        '   Begin Object Name="B"\n'
        '      Begin Object Class=/Script/X.Pin Name="P"\n'
        '      End Object\n'
        '      Begin Object Name="P"\n'
        '         Direction=Hidden\n'
        '      End Object\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    a = doc.objects[0]
    b = a.children[0]
    assert len(b.children) == 1
    p = b.children[0]
    assert p.cls == "/Script/X.Pin"
    assert p.properties["Direction"].text == "Hidden"


def test_no_duplicate_no_change() -> None:
    """중복 없는 경우 변화 없음."""
    src = (
        'Begin Object Name="N"\n'
        '   Begin Object Class=/Script/X.Pin Name="A"\n'
        '      Direction=Input\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="B"\n'
        '      Direction=Output\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    n = doc.objects[0]
    assert len(n.children) == 2


def test_top_level_dedupe_unchanged() -> None:
    """최상위 머지(기존 동작) 회귀 없음."""
    src = (
        'Begin Object Class=/Script/X.Node Name="N"\n'
        'End Object\n'
        'Begin Object Name="N"\n'
        '   Direction=Output\n'
        'End Object\n'
    )
    doc = parse_document(src)
    assert len(doc.objects) == 1
    n = doc.objects[0]
    assert n.cls == "/Script/X.Node"
    assert n.properties["Direction"].text == "Output"


def test_link_with_paths_merged() -> None:
    """RigVMLink 선언 + 정의 머지 — SourcePinPath/TargetPinPath 보존."""
    src = (
        'Begin Object Name="N"\n'
        '   Begin Object Class=/Script/RigVMDeveloper.RigVMLink Name="L_1"\n'
        '   End Object\n'
        '   Begin Object Name="L_1"\n'
        '      SourcePinPath="X.Out"\n'
        '      TargetPinPath="Y.In"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    n = doc.objects[0]
    assert len(n.children) == 1
    link = n.children[0]
    assert link.cls == "/Script/RigVMDeveloper.RigVMLink"
    assert link.properties["SourcePinPath"].text == "X.Out"
    assert link.properties["TargetPinPath"].text == "Y.In"


def test_three_siblings_with_two_duplicates() -> None:
    """A·B·A·C → A 머지 후 3 children (A·B·C)."""
    src = (
        'Begin Object Name="P"\n'
        '   Begin Object Class=/Script/X.Pin Name="A"\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="B"\n'
        '   End Object\n'
        '   Begin Object Name="A"\n'
        '      Direction=Input\n'
        '   End Object\n'
        '   Begin Object Class=/Script/X.Pin Name="C"\n'
        '   End Object\n'
        'End Object\n'
    )
    doc = parse_document(src)
    p = doc.objects[0]
    assert len(p.children) == 3
    assert {c.name for c in p.children} == {"A", "B", "C"}
    a = next(c for c in p.children if c.name == "A")
    assert a.cls == "/Script/X.Pin"
    assert a.properties["Direction"].text == "Input"
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/core/t3d/test_document_merge.py -v`
Expected: 일부 FAIL (특히 `test_nested_dedupe_same_parent` — 32개 child 그대로).

- [ ] **Step 3: `_recursive_dedupe` 구현**

`src/t3dgraph/core/t3d/document.py`:

```python
"""무손실 T3DDocument — 2단계(선언/정의) 블록 병합."""
from __future__ import annotations
from dataclasses import dataclass, field
from .objects import T3DObject, parse_objects


@dataclass
class T3DDocument:
    objects: list[T3DObject] = field(default_factory=list)


def _merge_into(target: T3DObject, other: T3DObject) -> None:
    if target.cls is None and other.cls is not None:
        target.cls = other.cls
    if other.export_path:
        target.export_path = other.export_path
    target.properties.update(other.properties)
    _merge_sibling_list(target.children, other.children)


def _merge_sibling_list(dst: list[T3DObject], src: list[T3DObject]) -> None:
    by_name: dict[str, T3DObject] = {o.name: o for o in dst if o.name}
    for o in src:
        existing = by_name.get(o.name) if o.name else None
        if existing is not None:
            _merge_into(existing, o)
        else:
            dst.append(o)
            if o.name:
                by_name[o.name] = o


def _dedupe_within(objects: list[T3DObject]) -> list[T3DObject]:
    """단일 sibling list 안에서 같은 name 항목 머지.

    선언(`Begin Object Class=... Name="X"`) + 정의(`Begin Object Name="X"`)가
    같은 부모의 children에 연속 또는 비연속으로 나타나면 하나로 합친다.
    """
    result: list[T3DObject] = []
    by_name: dict[str, T3DObject] = {}
    for o in objects:
        if o.name and o.name in by_name:
            _merge_into(by_name[o.name], o)
        else:
            result.append(o)
            if o.name:
                by_name[o.name] = o
    return result


def _recursive_dedupe(objects: list[T3DObject]) -> list[T3DObject]:
    """전 트리 깊이에서 sibling 중복 머지."""
    deduped = _dedupe_within(objects)
    for obj in deduped:
        obj.children = _recursive_dedupe(obj.children)
    return deduped


def parse_document(src: str) -> T3DDocument:
    raw = parse_objects(src)
    merged: list[T3DObject] = []
    _merge_sibling_list(merged, raw)
    return T3DDocument(objects=_recursive_dedupe(merged))
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/core/t3d/test_document_merge.py -v`
Expected: 6 passed

- [ ] **Step 5: 풀스위트 회귀**

Run: `pytest tests -v`
Expected: 전체 통과. **다수 통합 테스트가 핀 개수 가정**하면 갱신 필요 — 가능성 높음. 특히:
- Orion 샘플 노드 개수 어서션 (F20 reproducer)
- 핀 개수 단위 테스트
- 링크 개수 검증

회귀 발생 시 가정 갱신(머지 후 절반 개수).

- [ ] **Step 6: Orion 샘플 검증**

```bash
T3DGRAPH_ORION_SAMPLE=Orion_WorkStation_Rig_Analysis/<sample>.t3d.txt \
  uv run python -c "
from pathlib import Path
import os
from t3dgraph.core.t3d.document import parse_document
from t3dgraph.plugins.rigvm.interpreter import RigVMGraphInterpreter

doc = parse_document(Path(os.environ['T3DGRAPH_ORION_SAMPLE']).read_text(encoding='utf-8', errors='replace'))
def find(objects, name):
    for o in objects:
        if o.name == name:
            return o
        f = find(o.children, name)
        if f: return f
    return None
n = find(doc.objects, 'HierarchyInstantiateFromPhysicsAsset')
if n is None:
    print('node not found in this sample')
else:
    print(f'children count: {len(n.children)}')
    from collections import Counter
    dups = [(k,v) for k,v in Counter(c.name for c in n.children).items() if v > 1]
    print(f'duplicated names after fix: {dups}')
    for c in n.children[:6]:
        d = c.properties.get('Direction')
        from t3dgraph.core.t3d.values import Scalar
        d_text = d.text if isinstance(d, Scalar) else d
        print(f'  {c.name!r}: cls={(c.cls or \"\").rsplit(\".\", 1)[-1]} Direction={d_text}')
"
```

Expected output:
- `children count: 16` (32에서 절반)
- `duplicated names after fix: []`
- 각 핀이 cls=RigVMPin AND Direction=Input/Output/Hidden/IO 한 줄에

- [ ] **Step 7: 수동 GUI 확인**

```bash
uv run t3dgraph-gui
```

Orion 샘플 열고 HierarchyInstantiateFromPhysicsAsset 노드 보기 — 16 핀만 표시, 각 핀이 본인 direction에 맞는 측에 단일 표시.

- [ ] **Step 8: 커밋**

```bash
git add tests/core/t3d/test_document_merge.py src/t3dgraph/core/t3d/document.py
git commit -m "fix(t3d): parse_document recursively dedupes sibling pins/links — fixes F21 핀 중복, likely F29 링크 누락"
```

---

## Self-Review

- T3D 2-패스 직렬화의 모든 nesting level 머지 — Task 1 ✅
- F21 핀 중복 해소 — Step 6 검증 ✅
- F29 링크 누락(서브그래프 실행 핀) — `test_link_with_paths_merged` ✅
- 기존 머지 회귀 없음 — `test_top_level_dedupe_unchanged` ✅
- PRESERVE-ALL — 노드 추가 방향(중복 제거로 단일 정확 표현)  ✅

## 완료 후

- F21·F23·F29 다수 영향 해소
- batch ⑬ g1·g2의 테스트가 정확한 Direction 값 위에서 작동 — 회귀 없음
- 다음 사이클 user 검증: 핀 표시·서브그래프 실행 링크 정상화 확인
