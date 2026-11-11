"""Explicit subject and evaluator registries."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from importlib.metadata import entry_points

from circumstances.plugins import EvaluatorPlugin, SubjectPlugin


class RegistryError(ValueError):
    pass


SubjectFactory = Callable[..., SubjectPlugin]


class SubjectRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, SubjectPlugin] = {}
        self._factories: dict[str, SubjectFactory] = {}

    def register(self, plugin: SubjectPlugin) -> None:
        plugin_id = plugin.descriptor.id

        def factory(plugin: SubjectPlugin = plugin) -> SubjectPlugin:
            return plugin

        self._add(plugin_id, factory)
        self._plugins[plugin_id] = plugin

    def load_entry_points(self) -> None:
        points = list(entry_points(group="circumstances.subjects"))
        if not points:
            from circumstances.adapters.openai_compatible import OpenAICompatibleSubjectPlugin
            from circumstances.adapters.toy import ToySubjectPlugin

            self._add("toy", ToySubjectPlugin)
            self._add("openai-compatible", OpenAICompatibleSubjectPlugin)
            return
        for point in points:
            self._add(point.name, point.load())

    def names(self) -> list[str]:
        return sorted(self._factories)

    def create(self, plugin_id: str, **kwargs: object) -> SubjectPlugin:
        try:
            factory = self._factories[plugin_id]
        except KeyError as exc:
            known = ", ".join(self.names()) or "none"
            raise RegistryError(
                f"unknown subject plugin {plugin_id!r}; registered: {known}"
            ) from exc
        signature = inspect.signature(factory)
        accepted = {
            key: value
            for key, value in kwargs.items()
            if value is not None and key in signature.parameters
        }
        rejected = [
            key
            for key, value in kwargs.items()
            if value is not None and key not in signature.parameters
        ]
        if rejected:
            raise RegistryError(f"subject {plugin_id} does not accept {', '.join(rejected)}")
        plugin = factory(**accepted)
        if plugin.descriptor.id != plugin_id:
            raise RegistryError(
                f"subject entry point {plugin_id!r} created descriptor {plugin.descriptor.id!r}"
            )
        return plugin

    def get(self, plugin_id: str) -> SubjectPlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError:
            plugin = self.create(plugin_id)
            self._plugins[plugin_id] = plugin
            return plugin

    def capabilities(self, plugin_id: str) -> set[str]:
        return set(self.get(plugin_id).descriptor.capabilities)

    def _add(self, plugin_id: str, factory: SubjectFactory) -> None:
        if plugin_id in self._factories:
            raise RegistryError(f"subject plugin already registered: {plugin_id}")
        self._factories[plugin_id] = factory


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
