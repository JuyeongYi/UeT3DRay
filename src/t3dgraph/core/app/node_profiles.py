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
