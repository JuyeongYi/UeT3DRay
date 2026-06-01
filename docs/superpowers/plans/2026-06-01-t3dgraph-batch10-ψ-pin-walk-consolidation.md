# batch ⑩ ψ (psi) — Pin Walk Consolidation + Contracts Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 세 곳에서 변주된 pin walk (`_locate_pin`·`_collect_node_pin_paths`)을 `GraphModel.find_pin`/`iter_pin_paths`로 통합. `_cls_suffix` 헬퍼 추출. controller의 `inspect.signature` glue 제거 + view contract에 `resolver` property 노출.

**Architecture:** `GraphModel`에 `find_pin(path)`·`iter_pin_paths(node_name=None)` 메서드 추가. 호출부 3곳 치환. `InterpreterFactory` 프로토콜이 `resolver` 키워드 표준화. `AbstractGraphView` 프로토콜에 `resolver` property.

**Tech Stack:** Python 3.11 (`typing.Protocol`), pytest. 외부 의존성 0.

**Spec:** `docs/superpowers/specs/2026-06-01-t3dgraph-batch-10-hotfix-design.md` §7

**Pre-condition:** master에 **α/χ 머지 완료** — interpreter.py 공유 충돌 회피. ω 머지도 권장 (main_window.py 공유). 1차 슬라이스 5개 머지 후 2차로 진입.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/base/graph_model.py` | 수정 (`find_pin`/`iter_pin_paths` 메서드 + `_walk_pin_paths` 모듈 함수) |
| `src/t3dgraph/plugins/rigvm/interpreter.py` | 수정 (`_locate_pin` 제거 → `g.find_pin` 사용, `_cls_suffix` 모듈 헬퍼 + 3분기 사용) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (`_collect_node_pin_paths` 제거 → `g.iter_pin_paths(node_name=)` 사용) |
| `src/t3dgraph/core/app/contracts.py` | 수정 (`AbstractGraphView`에 `resolver` property + `InterpreterFactory` Protocol) |
| `src/t3dgraph/core/app/controller.py` | 수정 (`inspect.signature` glue 제거, `view.resolver`·`factory(resolver=...)` 직접 호출) |
| `tests/base/test_graph_model_find_pin.py` | 신규 |

---

## Task 1: `GraphModel.find_pin` + `iter_pin_paths` — TDD

**Files:**
- Create: `tests/base/test_graph_model_find_pin.py`
- Modify: `src/t3dgraph/core/base/graph_model.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/base/test_graph_model_find_pin.py`:

```python
"""ψ — GraphModel.find_pin + iter_pin_paths 단위."""
from __future__ import annotations

from t3dgraph.core.base.graph_model import GraphModel, Node, Pin


def _p(name: str, subs: list[Pin] | None = None) -> Pin:
    return Pin(name=name, cpp_type=None, direction=None,
               subpins=subs or [])


def test_find_pin_top_level() -> None:
    a = _p("A")
    n = Node(name="N1", cls="X", pins=[a])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.A") is a


def test_find_pin_subpin() -> None:
    sub = _p("X")
    parent = _p("P", subs=[sub])
    n = Node(name="N1", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.P.X") is sub


def test_find_pin_deeply_nested() -> None:
    leaf = _p("Leaf")
    mid = _p("Mid", subs=[leaf])
    parent = _p("Parent", subs=[mid])
    n = Node(name="N1", cls="X", pins=[parent])
    g = GraphModel(nodes=[n])
    assert g.find_pin("N1.Parent.Mid.Leaf") is leaf


def test_find_pin_missing_node() -> None:
    g = GraphModel(nodes=[Node(name="N1", cls="X", pins=[_p("A")])])
    assert g.find_pin("Missing.A") is None


def test_find_pin_missing_pin() -> None:
    g = GraphModel(nodes=[Node(name="N1", cls="X", pins=[_p("A")])])
    assert g.find_pin("N1.NotThere") is None


def test_find_pin_empty_path() -> None:
    g = GraphModel()
    assert g.find_pin("") is None


def test_iter_pin_paths_all() -> None:
    n = Node(name="N1", cls="X",
             pins=[_p("P", subs=[_p("X"), _p("Y")]), _p("Q")])
    g = GraphModel(nodes=[n])
    paths = list(g.iter_pin_paths())
    assert paths == ["N1.P", "N1.P.X", "N1.P.Y", "N1.Q"]


def test_iter_pin_paths_filtered_by_node() -> None:
    n1 = Node(name="N1", cls="X", pins=[_p("A")])
    n2 = Node(name="N2", cls="X", pins=[_p("B")])
    g = GraphModel(nodes=[n1, n2])
    paths = list(g.iter_pin_paths(node_name="N2"))
    assert paths == ["N2.B"]


def test_iter_pin_paths_filtered_missing_node_empty() -> None:
    g = GraphModel(nodes=[Node(name="N1", cls="X", pins=[_p("A")])])
    assert list(g.iter_pin_paths(node_name="MissingNode")) == []
```

- [ ] **Step 2: 실행 — 실패 확인**

Run: `pytest tests/base/test_graph_model_find_pin.py -v`
Expected: FAIL — 메서드 미존재.

- [ ] **Step 3: `GraphModel`에 메서드 추가**

`src/t3dgraph/core/base/graph_model.py` 상단 import 추가:

```python
from typing import Any, Iterator
```

(`Iterator` 추가 — `Any` 이미 있을 가능성.)

`GraphModel` 클래스 끝 (`node_by_name` 다음) 추가:

```python
def find_pin(self, path: str) -> "Pin | None":
    """'NodeName.PinName[.SubPin...]' → Pin. 없으면 None."""
    if not path:
        return None
    parts = path.split(".")
    node = self.node_by_name(parts[0])
    if node is None:
        return None
    cur_pins = node.pins
    last: Pin | None = None
    for name in parts[1:]:
        pin = next((p for p in cur_pins if p.name == name), None)
        if pin is None:
            return None
        last = pin
        cur_pins = pin.subpins
    return last

def iter_pin_paths(self, *, node_name: str | None = None) -> Iterator[str]:
    """모든 핀 경로(서브핀 포함) 순회. node_name 지정 시 그 노드만."""
    nodes = ([n for n in self.nodes if n.name == node_name]
             if node_name else self.nodes)
    for node in nodes:
        for pin in node.pins:
            yield from _walk_pin_paths(pin, node.name)
```

모듈 함수로 helper 추가 (`@dataclass` `GraphModel` 위 또는 아래):

```python
def _walk_pin_paths(pin: "Pin", prefix: str) -> Iterator[str]:
    path = f"{prefix}.{pin.name}"
    yield path
    for sp in pin.subpins:
        yield from _walk_pin_paths(sp, path)
```

- [ ] **Step 4: 실행 — 통과 확인**

Run: `pytest tests/base/test_graph_model_find_pin.py -v`
Expected: 9 passed

- [ ] **Step 5: 커밋**

```bash
git add tests/base/test_graph_model_find_pin.py src/t3dgraph/core/base/graph_model.py
git commit -m "feat(base): GraphModel.find_pin + iter_pin_paths (ψ prep)"
```

---

## Task 2: 인터프리터 `_locate_pin` 제거 → `find_pin` 사용 + `_cls_suffix` 헬퍼

**Files:**
- Modify: `src/t3dgraph/plugins/rigvm/interpreter.py`

- [ ] **Step 1: `_locate_pin` 호출 대체**

`src/t3dgraph/plugins/rigvm/interpreter.py`의 `_annotate_variable_consumers` 안:

```python
# 변경 전
target_pin = self._locate_pin(g, link.target_path)

# 변경 후
target_pin = g.find_pin(link.target_path)
```

`_locate_pin` 메서드 자체 제거.

- [ ] **Step 2: `_cls_suffix` 모듈 헬퍼 추가 + 3분기 사용**

`_interpret_objects` 함수 위(또는 `_text` 근처)에 추가:

```python
def _cls_suffix(obj: T3DObject) -> str | None:
    """T3DObject.cls의 suffix (마지막 '.' 이후) 반환. None이면 None."""
    return (obj.cls or "").rsplit(".", 1)[-1] or None
```

`_interpret_objects` 안의 `DroppedObject(..., cls=...)` 3분기에서 사용:

```python
# 변경 전
cls_suffix = (obj.cls or "").rsplit(".", 1)[-1] or None
diagnostics.objects_dropped.append(DroppedObject(
    name=obj.name or "?", cls=cls_suffix, reason="unknown class",
    parent_obj=parent_node))

# 변경 후
diagnostics.objects_dropped.append(DroppedObject(
    name=obj.name or "?", cls=_cls_suffix(obj), reason="unknown class",
    parent_obj=parent_node))
```

(3분기 모두 같은 패턴 — `depth cap`·`graph at top`·`unknown class`.)

`_add_node`의 `extracted_per_class` 카운트도 통일:

```python
# 변경 전
suffix = (obj.cls or "").rsplit(".", 1)[-1]
diagnostics.extracted_per_class[suffix] = ...

# 변경 후
suffix = _cls_suffix(obj) or ""
diagnostics.extracted_per_class[suffix] = ...
```

- [ ] **Step 3: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과. `find_pin`이 `_locate_pin`과 동일 동작 (서브핀까지 따라가는 walk).

- [ ] **Step 4: 커밋**

```bash
git add src/t3dgraph/plugins/rigvm/interpreter.py
git commit -m "refactor(rigvm): use GraphModel.find_pin + _cls_suffix helper (ψ)"
```

---

## Task 3: MainWindow `_collect_node_pin_paths` 제거 → `iter_pin_paths` 사용

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`

- [ ] **Step 1: 호출부 대체**

`src/t3dgraph/core/app/main_window.py`의 `_invoke_node_action` 안 (또는 `_collect_node_pin_paths` 호출 위치):

```python
# 변경 전
paths = self._collect_node_pin_paths(node)

# 변경 후
paths = list(self.graph.iter_pin_paths(node_name=node.name))
```

`_collect_node_pin_paths` 메서드 자체 제거.

- [ ] **Step 2: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과. F19 노드 컨텍스트 메뉴 expand_all 테스트가 같은 결과.

- [ ] **Step 3: 커밋**

```bash
git add src/t3dgraph/core/app/main_window.py
git commit -m "refactor(app): use GraphModel.iter_pin_paths in node menu (ψ)"
```

---

## Task 4: View contract에 `resolver` property + controller 정상화

**Files:**
- Modify: `src/t3dgraph/core/app/contracts.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Modify: `src/t3dgraph/core/app/controller.py`

- [ ] **Step 1: `contracts.py`에 property 정의**

`src/t3dgraph/core/app/contracts.py` 상단 import 추가:

```python
from typing import TYPE_CHECKING, Protocol
if TYPE_CHECKING:
    from ..t3d.resolver import AssetResolver
    from ..base.interpreter import AbstractGraphInterpreter
```

`AbstractGraphView` Protocol에 추가:

```python
class AbstractGraphView(Protocol):
    ...
    @property
    def resolver(self) -> "AssetResolver | None":
        ...
```

신규 `InterpreterFactory` Protocol 추가:

```python
class InterpreterFactory(Protocol):
    def __call__(
        self, *, resolver: "AssetResolver | None" = None,
    ) -> "AbstractGraphInterpreter":
        ...
```

- [ ] **Step 2: `MainWindow`에 `resolver` property 노출**

`src/t3dgraph/core/app/main_window.py`의 `MainWindow` 클래스에 추가:

```python
@property
def resolver(self) -> "AssetResolver | None":
    return self._resolver
```

- [ ] **Step 3: `controller.py`의 `inspect.signature` glue 제거**

`src/t3dgraph/core/app/controller.py`의 인터프리터 생성 부분:

```python
# 변경 전 (가정)
import inspect
sig = inspect.signature(self.interpreter_factory)
if "resolver" in sig.parameters:
    interp = self.interpreter_factory(resolver=getattr(self.view, "_resolver", None))
else:
    interp = self.interpreter_factory()

# 변경 후
interp = self.interpreter_factory(resolver=self.view.resolver)
```

`inspect` 모듈 import 제거 (다른 곳에서 안 쓰면).

- [ ] **Step 4: 회귀 확인**

Run: `pytest tests -v`
Expected: 전체 통과. 모든 인터프리터 팩토리가 `resolver` 키워드를 받아야 함 — `RigVMGraphInterpreter`는 이미 받음. 다른 플러그인이 있으면 시그니처 갱신 필요 (현재 RigVM 단일).

- [ ] **Step 5: 수동 검증 (선택)**

```bash
uv run t3dgraph-gui
```

Orion 폴더 로드 → FunctionReferenceNode 더블클릭 진입 → 함수 본문 표시 (resolver wiring 정상).

- [ ] **Step 6: 커밋**

```bash
git add src/t3dgraph/core/app/contracts.py src/t3dgraph/core/app/main_window.py src/t3dgraph/core/app/controller.py
git commit -m "refactor(app): view.resolver property + InterpreterFactory protocol (ρ-B1+B2)"
```

---

## Self-Review 체크리스트

- Spec §7.1.1 `GraphModel.find_pin`/`iter_pin_paths` — Task 1 ✅
- Spec §7.1.1 호출부 3곳 치환 (`_locate_pin`·`_collect_node_pin_paths`·`items.collect_pin_rows` 별도) — Task 2·3 ✅
- Spec §7.1.2 `_cls_suffix` 헬퍼 + 3분기 사용 — Task 2 ✅
- Spec §7.1.3 contracts 정상화 (`resolver` property + `InterpreterFactory`) — Task 4 ✅
- Spec §7.2 테스트 5건 + 회귀 — Task 1 + Task 2/3 회귀 ✅
- PRESERVE-ALL — 행동 무변경 리팩터 ✅

---

## 완료 후

- improver 자동 리뷰 → backlog
- ν-B1·φ-B2·ρ-B1/B2/B3 백로그 해소
- batch ⑩ 완전 마감
