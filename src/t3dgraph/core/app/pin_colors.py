"""핀 색 팔레트 룩업 — TOML 기반 3계층 (special -> bucket -> palette)."""
from __future__ import annotations
import os
import sys
import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from PySide6.QtGui import QColor

_FALLBACK_COLOR = QColor("#C8C878")  # palette.default 키 누락 시 하드코딩 안전망


@dataclass(frozen=True)
class ResolvedColor:
    """핀 색 룩업 결과. 배열 핀은 외곽선 변형 신호."""
    color: QColor
    is_array: bool


class PinColorTable:
    """TOML 팔레트에서 cpp_type -> 색을 룩업한다.

    런타임은 사용자 파일(`_user_dir() / pin_colors.toml`)만 읽는다.
    첫 호출 시 사용자 파일이 없으면 번들에서 풀 카피한다.
    """

    def __init__(
        self,
        *,
        palette: dict[str, QColor],
        bucket: dict[str, str],
        exec_marker: str,
        array_marker: str,
    ) -> None:
        self._palette = palette
        self._bucket = bucket
        self._exec_marker = exec_marker
        self._array_marker = array_marker

    @classmethod
    def load(cls) -> "PinColorTable":
        user_file = cls._user_dir() / "pin_colors.toml"
        if not user_file.exists():
            user_file.parent.mkdir(parents=True, exist_ok=True)
            bundle_bytes = resources.files(
                "t3dgraph.core.app.resources"
            ).joinpath("pin_colors.toml").read_bytes()
            user_file.write_bytes(bundle_bytes)
        with user_file.open("rb") as f:
            data = tomllib.load(f)
        palette = {k: QColor(v) for k, v in data.get("palette", {}).items()}
        if "default" not in palette:
            palette["default"] = _FALLBACK_COLOR
        bucket = dict(data.get("bucket", {}))
        special = data.get("special", {})
        return cls(
            palette=palette,
            bucket=bucket,
            exec_marker=special.get("exec_marker", "ExecuteContext"),
            array_marker=special.get("array_marker", "TArray<"),
        )

    @classmethod
    def reset_user_file(cls) -> Path:
        """사용자 파일을 번들로 덮어쓰고 경로를 반환한다."""
        user_file = cls._user_dir() / "pin_colors.toml"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        bundle_bytes = resources.files(
            "t3dgraph.core.app.resources"
        ).joinpath("pin_colors.toml").read_bytes()
        user_file.write_bytes(bundle_bytes)
        return user_file

    def resolve(self, cpp_type: str | None) -> ResolvedColor:
        default = self._palette.get("default", _FALLBACK_COLOR)
        if cpp_type is None:
            return ResolvedColor(color=default, is_array=False)
        # special — array: 한 레벨만 벗김 (단일 레벨 TArray<T> 전용)
        if cpp_type.startswith(self._array_marker):
            inner = cpp_type[len(self._array_marker):-1]
            inner_resolved = self.resolve(inner)
            return ResolvedColor(color=inner_resolved.color, is_array=True)
        # special — exec
        if self._exec_marker in cpp_type:
            return ResolvedColor(color=self._palette.get("exec", default),
                                 is_array=False)
        # bucket -> palette
        key = self._bucket.get(cpp_type)
        if key is not None and key in self._palette:
            return ResolvedColor(color=self._palette[key], is_array=False)
        return ResolvedColor(color=default, is_array=False)

    @classmethod
    def _user_dir(cls) -> Path:
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            return Path(base) / "t3dgraph"
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        return base / "t3dgraph"
