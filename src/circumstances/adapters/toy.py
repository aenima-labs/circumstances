"""Deterministic subject used by examples and contract tests."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from circumstances.models import (
    Action,
    EnvironmentAction,
    Event,
    ExtensionAction,
    GeneratedMessageAction,
    JSONValue,
    MessageAction,
    MessageEvent,
    ObservationEvent,
    PluginDescriptor,
    StateChangeEvent,
    ToolCallEvent,
    TrialSpec,
    WaitAction,
)


class ToyTrialSession:
    def __init__(self, trial: TrialSpec) -> None:
        self.trial = trial
        self.state: dict[str, JSONValue] = {}
        self.closed = False

    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]:
        del timeout_s
        if self.closed:
            raise RuntimeError("trial session is closed")
        if isinstance(action, MessageAction):
            configured = self._configured_response(action.content)
            if configured is not None:
                return [
                    MessageEvent(sequence=0, role=action.role, content=action.content),
                    *configured,
                ]
            return [
                MessageEvent(sequence=0, role=action.role, content=action.content),
                MessageEvent(
                    sequence=0,
                    role="assistant",
                    content=f"Observed: {action.content}",
                ),
            ]
        if isinstance(action, GeneratedMessageAction):
            generated = f"[{action.persona or 'user'}] {action.prompt}"
            return [
                MessageEvent(sequence=0, role="user", content=generated),
                MessageEvent(sequence=0, role="assistant", content=f"Observed: {generated}"),
            ]
        if isinstance(action, WaitAction):
            if action.duration_s:
                await asyncio.sleep(min(action.duration_s, 0.01))
            return [
                ObservationEvent(
                    sequence=0,
                    name="wait.completed",
                    value=action.until or action.duration_s,
                )
            ]
        if isinstance(action, EnvironmentAction):
            before = self.state.get(action.name)
            value = action.arguments.get("value", True)
            self.state[action.name] = value
            return [
                StateChangeEvent(
                    sequence=0,
                    path=action.name,
                    before=before,
                    after=value,
                ),
                ObservationEvent(sequence=0, name=action.name, value=value),
            ]
        if isinstance(action, ExtensionAction):
            return [
                ObservationEvent(
                    sequence=0,
                    name=f"{action.namespace}.{action.name}",
                    value=action.input,
                )
            ]
        raise TypeError(f"unsupported action: {type(action)!r}")

    def _configured_response(self, message: str) -> list[Event] | None:
        responses = self.trial.case.fixture.config.get("responses")
        if not isinstance(responses, dict):
            return None
        configured = responses.get(message)
        if not isinstance(configured, dict):
            return None
        events: list[Event] = []
        tools = configured.get("tools", [])
        if isinstance(tools, list):
            for index, name in enumerate(tools):
                if isinstance(name, str):
                    events.append(
                        ToolCallEvent(
                            sequence=0,
                            call_id=f"toy-{index}",
                            name=name,
                        )
                    )
        content = configured.get("text")
        if isinstance(content, str):
            events.append(
                MessageEvent(sequence=0, role="assistant", content=content)
            )
        observations = configured.get("observations", {})
        if isinstance(observations, dict):
            for name, value in observations.items():
                events.append(
                    ObservationEvent(sequence=0, name=name, value=value)
                )
        return events

    async def close(self) -> None:
        self.closed = True


class ToySubjectPlugin:
    descriptor = PluginDescriptor(
        id="toy",
        version="1",
        capabilities=[
            "message.text",
            "message.generated",
            "wait",
            "environment.action",
            "extension",
            "state.observe",
        ],
    )

    async def prepare(self, trial: TrialSpec) -> ToyTrialSession:
        return ToyTrialSession(trial)

