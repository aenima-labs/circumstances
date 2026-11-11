# Run bundles

Every run is written as one self-contained, sealed directory. A bundle can be
read, verified, compared, and regraded after the subject, the model, and the
original pack source are gone.

## Layout

```text
results/
  <run-id>/
    run.json                 # the whole run: lock, results, trajectories, grades
    trials/
      <trial-id>.json        # one file per trial
    pack/                    # byte-for-byte snapshot of the pack that ran
      pack.yaml
      rules/…
    seal.json                # SHA-256 of every file above
  <run-id>.regrades/
    20261111T171844Z-f744d210d8e6.json   # one per `run score`
```

The bundle is first written to a hidden `.<run-id>.pending` directory and
renamed into place only after it is sealed, so a crashed run never leaves a
half-written bundle under its real name.

All JSON is written canonically: sorted keys, no extra whitespace, UTF-8.

## `run.json`

A `RunSummary`:

| Field | Description |
|---|---|
| `run_id` | 32-character hex id |
| `pack_id`, `pack_version` | From `pack.yaml` |
| `started_at`, `finished_at` | UTC timestamps |
| `lock` | The [run lock](#run-lock) |
| `results` | One `TrialResult` per trial |

Each `TrialResult` has `trial_id` (`<case-id>--<attempt>--<random>`),
`case_id`, `attempt`, `seed`, `trajectory`, and `grades`.

A `trajectory` has `trial_id`, `subject` (the plugin descriptor), `events`,
`started_at`, `finished_at`, and `error`.

A `grade` has `evaluator_id`, `evaluator_type`, `evaluator_version`, `tier`,
`status`, `score`, `reasoning`, `evidence` (a list of `{event_sequences,
artifact, note}`), `soft`, `model`, and `cost`.

The schema is `jsonschema/v4/run.schema.json`.

## Run lock

The lock records everything that must match for two runs to be comparable.

| Field | Description |
|---|---|
| `pack_digest` | SHA-256 of the pack directory |
| `pack_source` | The resolved source reference |
| `pack_revision` | Git commit, when the pack came from git |
| `subject` | Plugin `id`, `version`, `capabilities`, and `models` |
| `evaluator_versions` | Every registered evaluator type and its version |
| `models` | Model identities reported by the subject |
| `fixture_digests` | Case id → fixture digest, for fixtures that declare one |

`run compare` refuses runs whose locks differ in pack digest, subject identity,
capabilities, evaluator versions, models, or fixture digests.

## `seal.json`

```json
{
  "schema": "circumstances.run-bundle.v1",
  "run_id": "c025c1ace7c742859d937b080b246892",
  "files": {
    "pack/pack.yaml": "9f2c…",
    "run.json": "41ab…",
    "trials/abstain-when-silent_vote--1--1a2b3c4d5e.json": "77de…"
  }
}
```

`verify-bundle` recomputes every digest and also reports any file present in
the directory but missing from the seal.

## Regrade records

`run score` writes `<run-id>.regrades/<UTC-stamp>-<hash>.json` next to the
bundle, never inside it. The hash is derived from the evaluator versions used.

| Field | Description |
|---|---|
| `schema` | `circumstances.regrade.v1` |
| `run_id` | The bundle that was regraded |
| `bundle_seal` | SHA-256 of that bundle's `seal.json` |
| `graded_at` | UTC timestamp |
| `evaluator_versions` | Versions used for this regrade |
| `passed` | Whether every trial passed |
| `trials` | Per trial: `trial_id`, `case_id`, `attempt`, `passed`, `grades` |

## Handling bundles safely

Bundles can contain prompts, model output, internal drafts, tool arguments and
results, environment observations, judge requests, and personal data. Store
`results/` with the same controls as the data your subject touches, keep it out
of version control (this repository's `.gitignore` already does), and delete
bundles according to your retention policy.
