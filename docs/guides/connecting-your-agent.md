# Connect your agent

Circumstances tests a **subject**: your whole system, not a bare model. There
are two ways to plug one in.

| You have… | Use |
|---|---|
| A chat model behind an OpenAI-compatible API, with no tools of its own | The built-in `openai-compatible` subject |
| An agent with tools, memory, retrieval, policies, or its own harness | A subject plugin you write: about a hundred lines of Python |

## The OpenAI-compatible subject

Configure it with environment variables and run:

```bash
export CIRCUMSTANCES_OPENAI_BASE_URL=https://api.example.com/v1
export CIRCUMSTANCES_OPENAI_API_KEY=sk-…
export CIRCUMSTANCES_OPENAI_MODEL=example-model-1
circumstances run packs/grounding --subject openai-compatible
```

`--model` overrides `CIRCUMSTANCES_OPENAI_MODEL` for one run:

```bash
circumstances run packs/grounding --subject openai-compatible --model example-model-2
```

What it does:

- Sends each `message` and `generated_message` action as a chat turn, keeping
  the conversation in memory for the length of the trial.
- Calls `POST {base_url}/chat/completions` with `temperature: 0`.
- Records the user turn and the assistant reply as `message` events.
- Records `wait` actions as a `wait.skipped` observation.
- Refuses `environment` and `extension` actions. A pack that needs them requires
  a subject with those capabilities.
- Declares the capabilities `message.text` and `message.generated`, and records
  the model name in the run lock.

It needs the `http` extra (`pip install "circumstances[http]"`).

## Write a subject plugin

A subject plugin is a Python object with two parts: a **descriptor** that says
who it is and what it can do, and a **prepare** method that opens one isolated
session per trial. The session turns each action into events.

```text
runner ──prepare(TrialSpec)──▶ plugin ──▶ session
runner ──execute(action)────▶ session ──▶ [events]   (once per action)
runner ──close()────────────▶ session
```

The contracts live in `circumstances.plugins`:

```python
class SubjectPlugin(Protocol):
    @property
    def descriptor(self) -> PluginDescriptor: ...
    async def prepare(self, trial: TrialSpec) -> TrialSession: ...

class TrialSession(Protocol):
    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]: ...
    async def close(self) -> None: ...
```

### A complete example

This plugin wraps an in-house email assistant. Replace `AcmeAssistant` with
your own client: an HTTP call, an SDK, or a function in the same process.

```python
"""Circumstances subject plugin for the Acme inbox assistant."""

from __future__ import annotations

from collections.abc import Sequence

from circumstances.models import (
    Action,
    Event,
    MessageAction,
    MessageEvent,
    ObservationEvent,
    PluginDescriptor,
    ToolCallEvent,
    ToolResultEvent,
    TrialSpec,
    WaitAction,
)

from acme.assistant import AcmeAssistant  # your system


class AcmeSession:
    def __init__(self, assistant: AcmeAssistant) -> None:
        self.assistant = assistant

    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]:
        if isinstance(action, WaitAction):
            await self.assistant.advance_clock(action.duration_s or 0)
            return [ObservationEvent(sequence=0, name="wait.completed", value=action.duration_s)]
        if not isinstance(action, MessageAction):
            raise ValueError(f"acme-inbox does not support {action.kind!r}")

        reply = await self.assistant.reply(action.content, timeout=timeout_s)

        events: list[Event] = [
            MessageEvent(sequence=0, role=action.role, content=action.content),
        ]
        for call in reply.tool_calls:
            events.append(
                ToolCallEvent(sequence=0, call_id=call.id, name=call.name, arguments=call.arguments)
            )
            events.append(
                ToolResultEvent(sequence=0, call_id=call.id, name=call.name, output=call.result)
            )
        events.append(MessageEvent(sequence=0, role="assistant", content=reply.text))
        return events

    async def close(self) -> None:
        await self.assistant.shutdown()


class AcmeSubjectPlugin:
    def __init__(self, *, model: str | None = None) -> None:
        self.model = model or "acme-default"

    @property
    def descriptor(self) -> PluginDescriptor:
        return PluginDescriptor(
            id="acme-inbox",
            version="2026.11.1",
            capabilities=["message.text", "wait"],
            models={"subject": self.model},
        )

    async def prepare(self, trial: TrialSpec) -> AcmeSession:
        fixture = trial.case.fixture
        if fixture.type != "builtin.documents":
            raise ValueError(f"acme-inbox cannot load fixture {fixture.type!r}")
        assistant = await AcmeAssistant.start(
            model=self.model,
            seed=trial.seed,
            mailbox=fixture.config.get("documents", []),
            sandbox=True,
        )
        return AcmeSession(assistant)
```

### Register it

Subject plugins are found through the `circumstances.subjects` entry-point
group. Add one line to the `pyproject.toml` of the package that contains the
plugin:

```toml
[project.entry-points."circumstances.subjects"]
acme-inbox = "acme_circumstances:AcmeSubjectPlugin"
```

Install that package into the same environment as Circumstances, then:

```bash
circumstances subjects                       # acme-inbox is listed
circumstances run inbox --subject acme-inbox
circumstances run inbox --subject acme-inbox --model acme-large
```

The entry-point name must equal `descriptor.id`; the registry refuses a plugin
whose descriptor disagrees with its name.

### Rules your plugin must follow

**Return events, do not number them.** Give every event `sequence=0`. The
runner renumbers events in arrival order and stamps each with the index of the
action that produced it.

**Echo the input.** Include the user message as an event, so the stored
trajectory reads as a complete transcript.

**Report what happened, not what was meant to happen.** If a tool call failed,
emit a `tool_result` with `error`. If your system made a policy decision, emit
a `policy_decision`. Evaluators can only see what you put in the trajectory.

**Separate internal drafts from delivered output.** A `message` event has a
`channel`, `"delivered"` by default. Record a model's private reasoning or
draft with another channel name so evaluators can tell what the user actually
saw.

**Expose state through observations.** `outcome.state` evaluators read
`observation` events by name. If a case asks whether `transfer.executed` is
false at the end, emit `ObservationEvent(name="transfer.executed", value=…)`.

**Keep sessions isolated.** One `prepare` call per trial. Do not share
conversation memory, caches, or sandbox state between trials. Use `trial.seed`
wherever your system accepts one.

**Raise on unsupported actions.** An exception ends the trial with a
`terminal` event of status `failed` and an `error` grade. That is better than
silently pretending to support something.

**Clean up in `close`.** It always runs, even when a trial times out or fails.
`trial.retention` says what the operator wants kept: `purge`, `artifacts`, or
`preserve`.

**Declare honest capabilities.** A pack lists `required_capabilities`; a
missing one stops the run before any trial starts. Do not claim a capability
you only half support.

### Capabilities

Capabilities are free-form strings. The built-in subjects use these, and packs
in this repository rely on them:

| Capability | Meaning |
|---|---|
| `message.text` | Accepts `message` actions and replies with `message` events |
| `message.generated` | Accepts `generated_message` actions |
| `wait` | Accepts `wait` actions |
| `environment.action` | Accepts `environment` actions that change the world |
| `state.observe` | Emits `observation` events for named state |
| `extension` | Accepts `extension` actions |

Namespace your own: `acme.calendar`, `acme.voice`. A pack that needs them
declares them in `required_capabilities`.

### Fixtures

`trial.case.fixture` is a `FixtureRef` with a `type`, a `config` mapping, an
optional `version` and `digest`, and a `privacy` label. Circumstances does not
interpret `config`. Your plugin decides which fixture types it can load and
should refuse the rest.

When a fixture lives outside the pack (a seeded database snapshot, say), set its
`digest` in the case. The digest is copied into the run lock, so runs against
different fixture data cannot be compared by accident.

## Test your plugin

Run a public pack with your subject and read the trajectory:

```bash
circumstances run packs/grounding --subject acme-inbox
circumstances run show <run-id> | jq '.cases[0].attempts[0].events'
```

Check that every action produced the events you expect, that sequences are
contiguous, and that a `terminal` event ends each trial. The `toy` subject in
`src/circumstances/adapters/toy.py` is a short, complete reference.

## Hosted execution

To run Circumstances as a service behind your own platform, with short-lived
credentials per run and callbacks for progress, see
[Provider API v1](../reference/provider-api.md).
