# Slice κ: 에셋 단위 교차 파일 resolver (FEAT-3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 같은 에셋의 여러 `.t3d.txt` 파일(예: RigVMModel + RigVMFunctionLibrary)을 함께 로드해 `external_refs`를 실제 노드로 resolve.

**Architecture:** `core/t3d/resolver.py`(신규) — `AssetResolver`. `register(path, doc)` + `resolve_external_refs(graph)`. MainWindow에 "에셋 폴더 열기..." 메뉴.

**Spec ref:** `2026-05-22-t3dgraph-batch-8-heavy-features-design.md` §κ.

---

### Task 1: AssetResolver 모델

**Files:**
- Create: `src/t3dgraph/core/t3d/resolver.py`
- Create: `tests/core/t3d/test_resolver.py`

- [ ] **Step 1: Tests**

```python
from pathlib import Path
from t3dgraph.core.t3d.resolver import AssetResolver
from t3dgraph.core.t3d.document import parse_document


def test_resolve_external_ref_by_name(tmp_path):
    a_src = (
        'Begin Object Class=/Script/Foo.Func Name="MyFunc"\n'
        'End Object\n'
    )
    pa = tmp_path / "a.t3d.txt"
    pa.write_text(a_src, encoding="utf-8")
    pb = tmp_path / "b.t3d.txt"
    pb.write_text('Begin Object Class=/Script/Foo.Caller Name="C"\nEnd Object\n', encoding="utf-8")

    r = AssetResolver()
    r.register(pa, parse_document(a_src))
    found = r.resolve_node_name("MyFunc")
    assert found is not None
    assert found[0] == pa
    assert found[1].name == "MyFunc"


def test_load_folder_registers_all_t3d_files(tmp_path):
    for name in ("a.t3d.txt", "b.t3d.txt"):
        (tmp_path / name).write_text(
            f'Begin Object Class=/Script/Foo.Bar Name="X_{name[0]}"\nEnd Object\n',
            encoding="utf-8"
        )
    r = AssetResolver()
    r.load_folder(tmp_path)
    assert r.resolve_node_name("X_a") is not None
    assert r.resolve_node_name("X_b") is not None


def test_resolve_external_refs_returns_resolved_map():
    """graph.external_refs 처리 — external_refs path → (file, node) 매핑."""
    from t3dgraph.core.base.graph_model import GraphModel
    g = GraphModel(external_refs=["MyFunc.OutPin", "Unknown.Ref"])
    r = AssetResolver()
    r._index["MyFunc"] = ("fake_path", "fake_obj")  # 직접 주입
    resolved = r.resolve_external_refs(g)
    assert "MyFunc.OutPin" in resolved
    assert "Unknown.Ref" not in resolved
```

- [ ] **Step 2: Implement**

```python
"""에셋 단위 교차 파일 resolver — 같은 폴더의 t3d 파일들을 인덱싱."""
from __future__ import annotations
from pathlib import Path
from .document import T3DDocument, parse_document
from .objects import T3DObject
from .encoding import read_t3d_text


class AssetResolver:
    def __init__(self) -> None:
        # 노드 이름 → (file_path, T3DObject)
        self._index: dict[str, tuple[Path, T3DObject]] = {}

    def register(self, path: Path, doc: T3DDocument) -> None:
        for obj in self._iter_objects(doc.objects):
            if obj.name:
                self._index.setdefault(obj.name, (path, obj))

    def _iter_objects(self, objs):
        for o in objs:
            yield o
            yield from self._iter_objects(o.children)

    def load_folder(self, folder: Path, pattern: str = "*.t3d.txt") -> None:
        for p in sorted(folder.glob(pattern)):
            try:
                doc = parse_document(read_t3d_text(p))
                self.register(p, doc)
            except Exception:
                continue   # lenient

    def resolve_node_name(self, name: str):
        return self._index.get(name)

    def resolve_external_refs(self, graph) -> dict[str, tuple[Path, T3DObject]]:
        """graph.external_refs의 각 경로의 node 부분을 인덱스에서 찾아 매핑 반환."""
        out: dict[str, tuple[Path, T3DObject]] = {}
        for ref in graph.external_refs:
            node_name = ref.split(".", 1)[0]
            hit = self._index.get(node_name)
            if hit is not None:
                out[ref] = hit
        return out
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/t3d/resolver.py tests/core/t3d/test_resolver.py
git commit -m "feat(t3d): AssetResolver folder-level cross-file lookup (FEAT-3)"
```

---

### Task 2: MainWindow 통합 — "에셋 폴더 열기" 메뉴

**Files:**
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/core/app/test_asset_folder_open.py`

- [ ] **Step 1: 변경**

```python
# _build_menu 안
file_menu.addAction("에셋 폴더 열기…").triggered.connect(self._on_open_folder)

self._resolver = None    # __init__에 추가


def _on_open_folder(self) -> None:
    folder = QFileDialog.getExistingDirectory(self, "에셋 폴더 선택")
    if not folder:
        return
    from ..t3d.resolver import AssetResolver
    self._resolver = AssetResolver()
    self._resolver.load_folder(Path(folder))
    # 폴더의 모든 t3d를 멀티탭으로 열기
    for path in sorted(Path(folder).glob("*.t3d.txt")):
        if self._open_handler:
            self._open_handler(str(path))
```

(헬퍼 메서드 — 폴더 일괄 등록 + 탭 추가)

- [ ] **Step 2: Test (headless 폴더 등록만)**

```python
def test_main_window_load_resolver(qapp, tmp_path):
    for n in ("a.t3d.txt", "b.t3d.txt"):
        (tmp_path / n).write_text(
            f'Begin Object Class=/Script/Foo.Bar Name="X_{n[0]}"\nEnd Object\n',
            encoding="utf-8")
    win = MainWindow()
    # 메뉴 클릭 우회 — load_folder 직접 호출 (UI 없는 환경)
    from t3dgraph.core.t3d.resolver import AssetResolver
    win._resolver = AssetResolver()
    win._resolver.load_folder(tmp_path)
    assert win._resolver.resolve_node_name("X_a") is not None
```

- [ ] **Step 3: Run·Commit**

```
git add src/t3dgraph/core/app/main_window.py tests/core/app/test_asset_folder_open.py
git commit -m "feat(main_window): asset folder menu + AssetResolver wiring (FEAT-3)"
```

---

### Task 3: external_refs UI 표시

**Files:**
- Modify: `src/t3dgraph/core/app/inspector_panel.py` (옵션 — 변경 안 해도 됨)

선택: 인스펙터 헤더에 resolved external_ref 카운트 표시. 이 task는 시간 여유 시.

- [ ] **Step 1**: skip (시간 우선).

---

### Task 4: 회귀

```
pytest tests/ -v
```

---

## 완료 정의

- [ ] Task 1-2 PASS
- [ ] `AssetResolver.load_folder` + `resolve_external_refs`
- [ ] "에셋 폴더 열기" 메뉴 (UI 동작은 헤드리스 테스트 한계 — 실행만)
