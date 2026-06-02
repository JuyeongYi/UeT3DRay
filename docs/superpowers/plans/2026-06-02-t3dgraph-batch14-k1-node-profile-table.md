# batch ⑭ k1 — NodeStyleProfile + NodeProfileTable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** `NodeStyleProfile` dataclass + `NodeProfileTable` 로더 + 번들 TOML + 사용자 파일 마이그레이션 인프라.

**Spec:** `docs/superpowers/specs/2026-06-02-t3dgraph-batch-14-node-profiles-design.md` §3·4·5

**Pre-condition:** master 최신.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/node_profiles.py` | 신규 (`NodeStyleProfile`, `NodeProfileTable`) |
| `src/t3dgraph/core/app/resources/node_profiles.toml` | 신규 (번들 디폴트) |
| `pyproject.toml` | package-data에 `*.toml` 이미 등록돼 있는지 확인 — μ에서 추가됨 |
| `tests/app/test_node_profiles.py` | 신규 |

---

## Task 1: NodeStyleProfile + NodeProfileTable — TDD

**Files:**
- Create: `src/t3dgraph/core/app/node_profiles.py`
- Create: `src/t3dgraph/core/app/resources/node_profiles.toml`
- Create: `tests/app/test_node_profiles.py`

- [ ] **Step 1: 번들 TOML 작성**

`src/t3dgraph/core/app/resources/node_profiles.toml`:

```toml
# t3dgraph 노드 클래스별 시각/동작 프로필
# 사용자가 ~/.config/t3dgraph/node_profiles.toml 편집해 확장 가능.

[profile.RigVMVariableNode]
show_var_badge = true

[profile.RigVMCollapseNode]
always_show_chevron = true
chevron_state_aware = true

[profile.RigVMFunctionReferenceNode]
always_show_chevron = true
chevron_state_aware = true
tooltip_when_no_subgraph = "함수 참조 — 함수 본문이 외부 파일에 있음. 에셋 폴더 열기로 함수 라이브러리 등록 필요."

[profile.RigVMFunctionEntryNode]
layout_hint = "outputs_only"

[profile.RigVMFunctionReturnNode]
layout_hint = "inputs_only"

[profile.RigVMRerouteNode]
layout_hint = "passthrough"
```

- [ ] **Step 2: 실패하는 테스트**

`tests/app/test_node_profiles.py`:

```python
"""k1 (batch ⑭) — NodeStyleProfile + NodeProfileTable 단위."""
from pathlib import Path

import pytest

from t3dgraph.core.app.node_profiles import NodeStyleProfile, NodeProfileTable


def test_default_profile() -> None:
    p = NodeStyleProfile()
    assert p.show_var_badge is False
    assert p.always_show_chevron is False
    assert p.chevron_state_aware is False
    assert p.tooltip_when_no_subgraph is None
    assert p.layout_hint == "default"


@pytest.fixture
def bundled_table(tmp_path: Path, monkeypatch) -> NodeProfileTable:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    return NodeProfileTable.load()


def test_variable_node_has_var_badge(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMVariableNode")
    assert p.show_var_badge is True


def test_collapse_node_chevron_state_aware(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMCollapseNode")
    assert p.always_show_chevron is True
    assert p.chevron_state_aware is True


def test_function_reference_has_tooltip(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMFunctionReferenceNode")
    assert p.tooltip_when_no_subgraph is not None
    assert "함수" in p.tooltip_when_no_subgraph


def test_function_entry_outputs_only(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMFunctionEntryNode")
    assert p.layout_hint == "outputs_only"


def test_function_return_inputs_only(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMFunctionReturnNode")
    assert p.layout_hint == "inputs_only"


def test_reroute_passthrough(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("RigVMRerouteNode")
    assert p.layout_hint == "passthrough"


def test_unknown_class_returns_default(bundled_table: NodeProfileTable) -> None:
    p = bundled_table.resolve("UnknownCustomNodeClass")
    assert p == NodeStyleProfile()


def test_first_load_copies_bundle_to_user_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "node_profiles.toml"
    assert not user_file.exists()
    NodeProfileTable.load()
    assert user_file.exists()
    bundle = NodeProfileTable._bundle_path()
    assert user_file.read_bytes() == bundle.read_bytes()


def test_user_file_overrides_bundle(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "node_profiles.toml"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text(
        '[profile.MyCustomNode]\nshow_var_badge = true\n',
        encoding="utf-8",
    )
    table = NodeProfileTable.load()
    custom = table.resolve("MyCustomNode")
    assert custom.show_var_badge is True


def test_user_file_partial_uses_default_for_unset(tmp_path, monkeypatch) -> None:
    """사용자 TOML에 일부 필드만 있으면 나머지는 디폴트."""
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    user_file = tmp_path / "node_profiles.toml"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text(
        '[profile.Minimal]\nshow_var_badge = true\n',
        encoding="utf-8",
    )
    table = NodeProfileTable.load()
    p = table.resolve("Minimal")
    assert p.show_var_badge is True
    assert p.always_show_chevron is False   # 디폴트
    assert p.layout_hint == "default"        # 디폴트
```

- [ ] **Step 3: 실행 — 실패 확인**

Run: `pytest tests/app/test_node_profiles.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: 구현**

`src/t3dgraph/core/app/node_profiles.py`:

```python
"""노드 클래스별 시각/동작 프로필 — TOML 기반.

데이터 주도: 사용자가 ~/.config/t3dgraph/node_profiles.toml 편집해
신규 클래스 추가 가능. 코드 변경 불필요.
"""
from __future__ import annotations
import os
import shutil
import sys
import tomllib
from dataclasses import dataclass, fields as _fields
from importlib import resources
from pathlib import Path


@dataclass(frozen=True)
class NodeStyleProfile:
    """단일 노드 클래스의 시각/동작 설정."""
    show_var_badge: bool = False
    always_show_chevron: bool = False
    chevron_state_aware: bool = False
    tooltip_when_no_subgraph: str | None = None
    layout_hint: str = "default"   # default | outputs_only | inputs_only | passthrough


_DEFAULT_PROFILE = NodeStyleProfile()
_ALLOWED_FIELDS = {f.name for f in _fields(NodeStyleProfile)}


class NodeProfileTable:
    """클래스 suffix → NodeStyleProfile 룩업."""

    def __init__(self, profiles: dict[str, NodeStyleProfile]) -> None:
        self._by_suffix = profiles

    def resolve(self, cls_suffix: str) -> NodeStyleProfile:
        return self._by_suffix.get(cls_suffix, _DEFAULT_PROFILE)

    @classmethod
    def load(cls) -> "NodeProfileTable":
        user_file = cls._user_dir() / "node_profiles.toml"
        if not user_file.exists():
            user_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(cls._bundle_path(), user_file)
        with user_file.open("rb") as f:
            data = tomllib.load(f)
        return cls(cls._parse(data))

    @classmethod
    def reset_user_file(cls) -> Path:
        user_file = cls._user_dir() / "node_profiles.toml"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cls._bundle_path(), user_file)
        return user_file

    @staticmethod
    def _parse(data: dict) -> dict[str, NodeStyleProfile]:
        profiles: dict[str, NodeStyleProfile] = {}
        for suffix, fields in data.get("profile", {}).items():
            # 알려진 필드만 사용 (사용자 오타 무시)
            filtered = {k: v for k, v in fields.items() if k in _ALLOWED_FIELDS}
            profiles[suffix] = NodeStyleProfile(**filtered)
        return profiles

    @classmethod
    def _user_dir(cls) -> Path:
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            return Path(base) / "t3dgraph"
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        return base / "t3dgraph"

    @classmethod
    def _bundle_path(cls) -> Path:
        with resources.as_file(
            resources.files("t3dgraph.core.app.resources") / "node_profiles.toml"
        ) as p:
            return Path(p)
```

- [ ] **Step 5: 실행 — 통과**

Run: `pytest tests/app/test_node_profiles.py -v`
Expected: 11 passed.

Run: `pytest tests -v`
Expected: 전체 통과 (신규 모듈이라 기존 영향 없음).

- [ ] **Step 6: 커밋**

```bash
git add src/t3dgraph/core/app/node_profiles.py src/t3dgraph/core/app/resources/node_profiles.toml tests/app/test_node_profiles.py
git commit -m "feat(app): NodeStyleProfile + NodeProfileTable — data-driven node behavior (k1)"
```

## 완료 후

인프라 준비 완료. k2가 NodeItem에 profile 주입해 기존 if-분기 제거.
