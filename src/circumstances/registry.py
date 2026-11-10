"""Explicit subject and evaluator registries."""

from __future__ import annotations

from importlib.metadata import entry_points

from circumstances.plugins import EvaluatorPlugin, SubjectPlugin


class RegistryError(ValueError):
    pass


class SubjectRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, SubjectPlugin] = {}

    def register(self, plugin: SubjectPlugin) -> None:
        plugin_id = plugin.descriptor.id
        if plugin_id in self._plugins:
            raise RegistryError(f"subject plugin already registered: {plugin_id}")
        self._plugins[plugin_id] = plugin

    def load_entry_points(self) -> None:
        for point in entry_points(group="circumstances.subjects"):
            factory = point.load()
            self.register(factory())

    def get(self, plugin_id: str) -> SubjectPlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            known = ", ".join(sorted(self._plugins)) or "none"
            raise RegistryError(
                f"unknown subject plugin {plugin_id!r}; registered: {known}"
            ) from exc

    def capabilities(self, plugin_id: str) -> set[str]:
        return set(self.get(plugin_id).descriptor.capabilities)


class EvaluatorRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, EvaluatorPlugin] = {}

    def register(self, plugin: EvaluatorPlugin) -> None:
        if plugin.type in self._plugins:
            raise RegistryError(f"evaluator plugin already registered: {plugin.type}")
        self._plugins[plugin.type] = plugin

    def load_entry_points(self) -> None:
        for point in entry_points(group="circumstances.evaluators"):
            factory = point.load()
            self.register(factory())

    def get(self, evaluator_type: str) -> EvaluatorPlugin:
        try:
            return self._plugins[evaluator_type]
        except KeyError as exc:
            known = ", ".join(sorted(self._plugins)) or "none"
            raise RegistryError(
                f"unknown evaluator type {evaluator_type!r}; registered: {known}"
            ) from exc

    def versions(self) -> dict[str, str]:
        return {name: plugin.version for name, plugin in sorted(self._plugins.items())}

