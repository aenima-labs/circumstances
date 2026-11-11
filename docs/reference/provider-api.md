# Provider API v1

`circumstances.provider.v1` is the contract between a hosting platform (the
system that owns users, targets, and dashboards) and a Circumstances provider
(the worker that resolves packs, runs trials, and seals bundles). The models
live in `circumstances.provider`.

Use it when you run evaluations as a service. For local runs, the command line
is all you need.

## Flow

```text
platform                                   provider
   │  GET capabilities ───────────────────────▶ │
   │ ◀──────────────── ProviderCapabilities ─── │
   │  POST ProviderRunRequest ────────────────▶ │
   │                                            │  resolve pack (digest-checked)
   │ ◀── run.started ─────────── callback ───── │
   │ ◀── case.completed (per attempt) ───────── │  call target with TargetCapability
   │ ◀── run.completed + artifact URI/digest ── │  seal bundle, upload
```

Every message carries `api_version: "circumstances.provider.v1"`.

## `ProviderCapabilities`

What a provider can do.

| Field | Description |
|---|---|
| `provider`, `provider_version` | Provider identity |
| `subjects` | Subject id → capabilities |
| `evaluator_types` | Installed evaluator types |
| `supports_cancel` | Default `true` |
| `supports_artifacts` | Default `true` |

`PackCatalogueEntry` describes a pack a provider can run: `id`, `version`,
`digest`, `title`, `case_ids`, `required_capabilities`.

## `ProviderRunRequest`

| Field | Description |
|---|---|
| `platform_run_id` | The platform's id for this run |
| `pack_id`, `pack_version`, `pack_digest` | Exactly which pack to run |
| `plan` | A `RunPlan`: `pack_ref`, `case_ids`, `subject`, `repetitions`, `seeds`, `concurrency`, `timeout_s`, `retention`, `trust` |
| `target` | A `TargetCapability` |
| `callback` | A `CallbackCapability` |
| `artifact_destination` | Where to upload the sealed bundle, if anywhere |

### `TargetCapability`

A short-lived grant to call the system under test.

| Field | Description |
|---|---|
| `adapter` | Subject plugin id |
| `endpoint` | Where the target listens |
| `token`, `audience`, `expires_at` | Credential bound to this run and target |
| `fixture` | Fixture data for the subject |

### `CallbackCapability`

A short-lived grant to report progress.

| Field | Description |
|---|---|
| `url` | Callback endpoint |
| `token`, `audience`, `expires_at` | Credential bound to this run |
| `allowed_events` | Which event types this token may send |

## Run events

Every event has `event_id`, `sequence`, `platform_run_id`, `provider_run_id`,
`pack_id`, `pack_version`, `pack_digest`, `occurred_at`, and a `type`:

| Type | Extra fields |
|---|---|
| `run.started` | `runner_version` |
| `case.completed` | `case_id`, `attempt`, `passed`, `result` |
| `run.completed` | `summary` (a full `RunSummary`), `artifact_uri`, `artifact_digest` |
| `run.failed` | `error` |
| `run.canceled` | `reason` |

## Security expectations

- Run provider workers under a dedicated identity with no platform
  administration, product database, application bucket, or broad secret access.
- Mint target and callback credentials per run, scoped to one audience and the
  event types the run needs, and expire them quickly.
- Resolve packs by digest. The request names `pack_digest`; a provider must
  refuse a pack that hashes differently.

See [Security and trust model](../background/security.md).
