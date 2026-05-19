"""플러그인 등록·그래프 타입 디스패치."""
from __future__ import annotations
import importlib
import pkgutil
from .base.plugin import GraphTypePlugin
from .t3d.document import T3DDocument


class Registry:
    def __init__(self) -> None:
        self._plugins: dict[str, GraphTypePlugin] = {}

    def register(self, plugin: GraphTypePlugin) -> None:
        if plugin.id in self._plugins:
            raise ValueError(f"플러그인 id 중복: {plugin.id}")
        self._plugins[plugin.id] = plugin

    def plugins(self) -> list[GraphTypePlugin]:
        return list(self._plugins.values())

    def detect(self, doc: T3DDocument) -> GraphTypePlugin:
        classes = [o.cls for o in doc.objects if o.cls]
        for plugin in self._plugins.values():
            if any(plugin.matches(c) for c in classes):
                return plugin
        raise LookupError(
            f"매칭되는 그래프 타입 플러그인 없음. 최상위 클래스: {classes[:5]} "
            f"— config/graph_types.toml 확인"
        )


_DEFAULT: Registry | None = None


def default_registry() -> Registry:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Registry()
        import t3dgraph.plugins as plugins_pkg
        for mod in pkgutil.iter_modules(plugins_pkg.__path__):
            importlib.import_module(f"t3dgraph.plugins.{mod.name}")
    return _DEFAULT
