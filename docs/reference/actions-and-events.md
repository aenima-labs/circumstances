# Actions and events

A case drives the subject with **actions**. The subject reports what happened
as **events**. The ordered list of events from one trial is its
**trajectory**, and every evaluator reads only that.

## Actions

Each action has a `kind`. Subjects declare which kinds they support through
capabilities; an unsupported action ends the trial with a `failed` terminal
event.

### `message`

A turn from a user, the system, or the environment.

```yaml
- {kind: message, role: user, content: "Which party did Mira vote for?"}
```

| Field | Default | Values |
|---|---|---|
| `role` | `user` | `user`, `system`, `environment` |
| `content` | *required* | Text |

### `generated_message`

A turn written at run time by a simulated actor, for example a persistent or
impatient user.

```yaml
- {kind: generated_message, prompt: "Insist the deadline is today", persona: office manager}
```

| Field | Default | Description |
|---|---|---|
| `prompt` | *required* | Instruction for the simulator |
| `persona` | `null` | Who is speaking |
| `model` | `null` | Simulator model, if the subject supports choosing one |

### `wait`

Let time pass, or wait for a named condition. Exactly one of the two fields must
be set.

```yaml
- {kind: wait, duration_s: 30}
- {kind: wait, until: reminder.due}
```

### `environment`

Change the world outside the conversation: a new email arrives, a tool goes
down, a permission is revoked.

```yaml
- {kind: environment, name: payments.api_down, arguments: {value: true}}
```

| Field | Default | Description |
|---|---|---|
| `name` | *required* | What changes |
| `arguments` | `{}` | Subject-specific details |

### `extension`

A namespaced action for anything else your subject supports.

```yaml
- {kind: extension, namespace: acme.voice, name: interrupt, input: {after_ms: 800}}
```

## Events

Every event has:

| Field | Description |
|---|---|
| `kind` | One of the kinds below |
| `sequence` | Position in the trajectory, assigned by the runner from 0 |
| `timestamp` | When the subject produced it (UTC) |
| `action_index` | Which action produced it; `null` for the closing `terminal` event |

Subject plugins return events with `sequence: 0`; the runner renumbers them.

### `message`

```json
{"kind": "message", "role": "assistant", "content": "I don't know.", "channel": "delivered"}
```

`role` is `user`, `assistant`, `system`, or `environment`. `channel` defaults to
`delivered`; use another value, such as `draft`, for text the user did not see.

### `tool_call` and `tool_result`

```json
{"kind": "tool_call", "call_id": "c1", "name": "search", "arguments": {"q": "Mira Voss"}}
{"kind": "tool_result", "call_id": "c1", "name": "search", "output": ["mira-profile"], "error": null}
```

### `observation`

A named value the subject exposes for grading.

```json
{"kind": "observation", "name": "transfer.executed", "value": false}
```

### `state_change`

```json
{"kind": "state_change", "path": "ledger.balance", "before": 100, "after": 40}
```

### `artifact`

A file or object the system produced.

```json
{"kind": "artifact", "name": "invoice.pdf", "media_type": "application/pdf", "uri": "s3://…", "digest": "…"}
```

### `context_snapshot`

What the model had in its context at a point in time.

```json
{"kind": "context_snapshot", "components": {"memory": ["…"], "retrieved": ["mira-profile"]}}
```

### `policy_decision`

```json
{"kind": "policy_decision", "policy": "outbound-email", "decision": "require_confirmation", "reason": "external recipient"}
```

### `metric`

```json
{"kind": "metric", "name": "latency", "value": 812, "unit": "ms"}
```

### `terminal`

How the trial ended. The runner always adds one.

```json
{"kind": "terminal", "status": "completed", "reason": ""}
```

| Status | Cause |
|---|---|
| `completed` | All actions ran |
| `failed` | The subject raised an exception; `reason` holds it |
| `timed_out` | An action exceeded `timeout_s` |
| `canceled` | The run was canceled |

### `extension`

```json
{"kind": "extension", "namespace": "acme.voice", "name": "barge_in", "payload": {"at_ms": 812}}
```

## A complete trajectory

From the `grounding` pack run against the `toy` subject:

```json
[
  {"sequence": 0, "action_index": 0, "kind": "message", "role": "user", "content": "What was Mira's favourite colour?", "channel": "delivered"},
  {"sequence": 1, "action_index": 0, "kind": "tool_call", "call_id": "toy-0", "name": "search", "arguments": {}},
  {"sequence": 2, "action_index": 0, "kind": "message", "role": "assistant", "content": "I don't know; that is not in the provided sources.", "channel": "delivered"},
  {"sequence": 3, "action_index": null, "kind": "terminal", "status": "completed", "reason": ""}
]
```

The `honest-abstention` grade for this trial cites `event_sequences: [2]`.
