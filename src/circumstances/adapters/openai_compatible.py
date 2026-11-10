"""Neutral OpenAI-compatible chat subject adapter."""

from __future__ import annotations

import os
from collections.abc import Sequence

from circumstances.models import (
    Action,
    Event,
    GeneratedMessageAction,
    MessageAction,
    MessageEvent,
    ObservationEvent,
    PluginDescriptor,
    TrialSpec,
    WaitAction,
)


class OpenAICompatibleTrialSession:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str | None,
    ) -> None:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("install circumstances[http] for the OpenAI adapter") from exc
        self._httpx = httpx
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=120,
        )
        self.model = model
        self.messages: list[dict[str, str]] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]:
        if isinstance(action, WaitAction):
            return [
                ObservationEvent(
                    sequence=0,
                    name="wait.skipped",
                    value=action.until or action.duration_s,
                )
            ]
        if isinstance(action, GeneratedMessageAction):
            content = action.prompt
        elif isinstance(action, MessageAction):
            if action.role not in {"user", "system"}:
                raise ValueError(f"OpenAI adapter cannot send role {action.role!r}")
            content = action.content
        else:
            raise ValueError(
                f"OpenAI-compatible adapter does not support {action.kind!r}; "
                "use a subject plugin with the required capability"
            )
        role = action.role if isinstance(action, MessageAction) else "user"
        self.messages.append({"role": role, "content": content})
        response = await self.client.post(
            "/chat/completions",
            json={"model": self.model, "messages": self.messages, "temperature": 0},
            timeout=timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        try:
            reply = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("OpenAI-compatible response has no assistant content") from exc
        if not isinstance(reply, str):
            raise ValueError("OpenAI-compatible assistant content must be text")
        self.messages.append({"role": "assistant", "content": reply})
        return [
            MessageEvent(sequence=0, role=role, content=content),
            MessageEvent(sequence=0, role="assistant", content=reply),
        ]

    async def close(self) -> None:
        await self.client.aclose()


class OpenAICompatibleSubjectPlugin:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.base_url = base_url or os.environ.get(
            "CIRCUMSTANCES_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"
        )
        self.api_key = api_key if api_key is not None else os.environ.get(
            "CIRCUMSTANCES_OPENAI_API_KEY", ""
        )
        self.model = model or os.environ.get("CIRCUMSTANCES_OPENAI_MODEL", "")
        self.system_prompt = system_prompt

    @property
    def descriptor(self) -> PluginDescriptor:
        return PluginDescriptor(
            id="openai-compatible",
            version="1",
            capabilities=["message.text", "message.generated"],
            models={"subject": self.model} if self.model else {},
        )

    async def prepare(self, trial: TrialSpec) -> OpenAICompatibleTrialSession:
        del trial
        if not self.model:
            raise ValueError("CIRCUMSTANCES_OPENAI_MODEL is required")
        return OpenAICompatibleTrialSession(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            system_prompt=self.system_prompt,
        )

