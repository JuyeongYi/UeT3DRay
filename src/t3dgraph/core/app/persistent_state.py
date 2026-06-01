"""파일 단위 영속 상태 — layout overrides + view state.

저장 위치: `~/.t3dgraph/state/{sha256(absolute_path)}.json`
형식: JSON (schema_version=1)
atomic write: tmp + replace
폴백: 손상·미래 버전 → 빈 상태 (사용자 데이터 손실 차단)
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


_SCHEMA_VERSION = 2


@dataclass
class GraphState:
    """graph_key 단위 상태 — multi-subgraph 영속용."""
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_positions": [
                {"node": k, "x": v[0], "y": v[1]}
                for k, v in self.node_positions.items()
            ],
            "expanded_pin_paths": sorted(self.expanded_pin_paths),
            "connected_pins_only": self.connected_pins_only,
            "fan_in_highlight": self.fan_in_highlight,
            "hidden_node_types": sorted(self.hidden_node_types),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GraphState":
        return cls(
            node_positions={
                e["node"]: (float(e["x"]), float(e["y"]))
                for e in data.get("node_positions", [])
            },
            expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
            connected_pins_only=bool(data.get("connected_pins_only", False)),
            fan_in_highlight=bool(data.get("fan_in_highlight", False)),
            hidden_node_types=list(data.get("hidden_node_types", [])),
        )


@dataclass
class PersistentState:
    """파일 단위 영속 상태."""
    schema_version: int = _SCHEMA_VERSION
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    expanded_pin_paths: list[str] = field(default_factory=list)
    connected_pins_only: bool = False
    fan_in_highlight: bool = False
    hidden_node_types: list[str] = field(default_factory=list)
    per_graph: dict[str, GraphState] = field(default_factory=dict)
    migrated_from_v1: bool = field(default=False, compare=False)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "node_positions": [
                {"node": k, "x": v[0], "y": v[1]}
                for k, v in self.node_positions.items()
            ],
            "expanded_pin_paths": sorted(self.expanded_pin_paths),
            "connected_pins_only": self.connected_pins_only,
            "fan_in_highlight": self.fan_in_highlight,
            "hidden_node_types": sorted(self.hidden_node_types),
            "per_graph": {k: v.to_dict() for k, v in self.per_graph.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentState":
        version = data.get("schema_version", _SCHEMA_VERSION)
        if version == 1:
            gs = GraphState(
                node_positions={
                    e["node"]: (float(e["x"]), float(e["y"]))
                    for e in data.get("node_positions", [])
                },
                expanded_pin_paths=list(data.get("expanded_pin_paths", [])),
                connected_pins_only=bool(data.get("connected_pins_only", False)),
                fan_in_highlight=bool(data.get("fan_in_highlight", False)),
                hidden_node_types=list(data.get("hidden_node_types", [])),
            )
            inst = cls(schema_version=_SCHEMA_VERSION, per_graph={"": gs})
            inst.migrated_from_v1 = True
            return inst
        if version != _SCHEMA_VERSION:
            return cls()
        return cls(
            schema_version=version,
            per_graph={
                k: GraphState.from_dict(v)
                for k, v in data.get("per_graph", {}).items()
            },
        )


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "t3dgraph" / "state"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "t3dgraph" / "state"


def _state_path(file_path: str) -> Path:
    abs_path = str(Path(file_path).resolve())
    digest = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()
    return _state_dir() / f"{digest}.json"


def load_state(file_path: str) -> tuple[PersistentState, str | None]:
    """영속 상태 로드. 폴백 시 (빈 state, 사유) — 사유 None이면 정상."""
    p = _state_path(file_path)
    if not p.exists():
        return PersistentState(), None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        bak = p.with_suffix(p.suffix + ".bak")
        try:
            p.replace(bak)
        except OSError:
            pass
        return PersistentState(), f"JSON 해독 실패 — {bak.name}으로 백업: {exc}"
    version = data.get("schema_version", _SCHEMA_VERSION)
    if version not in (1, _SCHEMA_VERSION):
        return PersistentState(), f"미지원 schema_version={version} — 무시"
    try:
        return PersistentState.from_dict(data), None
    except (KeyError, TypeError, ValueError) as exc:
        return PersistentState(), f"구조 오류 — 무시: {exc}"


def save_state(file_path: str, state: PersistentState) -> None:
    p = _state_path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
    tmp.replace(p)
