# Command line

```text
circumstances [--version] [-h] <command> …
```

Every command that prints structured data prints indented JSON with sorted
keys. Errors go to standard error as `error: <message>`.

| Exit code | Meaning |
|---|---|
| `0` | Success; for `run` and `run score`, every trial passed |
| `1` | The command ran but something failed: a trial, a self-test, a bundle digest |
| `2` | The command could not run: invalid pack, unknown subject or evaluator, missing capability, digest mismatch, incompatible runs |

## Packs

### `pack init`

```text
circumstances pack init <directory> [--id PUBLISHER/NAME] [--title TITLE]
```

Writes a format-v4 pack into an empty or new directory: `pack.yaml`, one rule
(`keeps-its-word`), a positive case with an `outcome.state` evaluator, and a
negative case with a `smoke.text` evaluator, all with self-tests and fictional
fixtures. Without `--id`, the id is `local/<directory-name>`, which must be a
lowercase slug. Refuses a non-empty directory.

### `pack add rule`

```text
circumstances pack add rule <pack> <rule-id> [--title TITLE]
```

Creates `rules/<rule-id>/rule.yaml` with no evaluators. `<rule-id>` must be a
lowercase slug. Refuses an existing rule.

### `pack add case`

```text
circumstances pack add case <pack> <rule-id> <case-id> [--polarity P] [--title TITLE]
```

Creates `rules/<rule-id>/cases/<case-id>/case.yaml` with one message action and
a `smoke.text` evaluator with self-tests. `--polarity` is one of `positive`
(default), `negative`, `attack`, `recovery`, `normal`. The rule must exist.

### `pack add <ref-or-name>`

```text
circumstances pack add <ref-or-name> [--digest SHA256] [--trust LEVEL]
```

Resolves a pack into the local cache and prints its `source`, `digest`,
`revision`, `path`, and `trust`. Accepts a local directory, an `https://`
archive, a `git+https://` reference, a first-party index name, or a name from
`circumstances.yaml`. Remote references default to `untrusted` and then need
`--digest`. Never executes the pack. See
[Share and install packs](../guides/installing-packs.md).

### `pack list`

```text
circumstances pack list
```

Prints `cached` (packs in `~/.cache/circumstances/packs`) and `known` (index
and project names with their refs, trust, digests, and revisions).

### `pack lint`

```text
circumstances pack lint <pack> [--trust LEVEL] [--digest SHA256]
```

Resolves and loads the pack, validates every file, and runs every evaluator
self-test. Prints `<id>@<version>: <n> cases`, then one `warning:` line per
weakness and one `FAIL:` line per self-test that disagreed with its expected
status. Exits 1 if any self-test failed.

Warnings include: no `reviewed_at`; an evaluator without both a known-pass and
a known-fail self-test; a pack whose cases are graded only by smoke evaluators.

`lint-pack` is an alias kept for compatibility.

## Runs

### `run`

```text
circumstances run <pack> [--subject ID] [--model NAME] [--case ID]…
                         [--repetitions N] [--concurrency N]
                         [--retention purge|artifacts|preserve]
                         [--results DIR] [--trust LEVEL] [--digest SHA256]
```

| Option | Default | Description |
|---|---|---|
| `--subject` | `toy` | Subject plugin id |
| `--model` | — | Passed to the subject if it accepts `model` |
| `--case` | all | Case id to run; repeatable |
| `--repetitions` | `1` | Minimum trials per case; `case.trials` wins if higher |
| `--concurrency` | `1` | Trials run in parallel |
| `--retention` | `artifacts` | Retention request passed to the subject |
| `--results` | `results` | Directory for sealed bundles |
| `--trust` | `local` | Trust level for resolution |
| `--digest` | — | Expected pack digest |

Prints `run_id`, `passed`, `trials`, `trials_passed`, and `bundle`.

### `run list`

```text
circumstances run list [--results DIR]
```

Lists sealed bundles with `run_id`, `pack_id`, `pack_version`, `started_at`,
`trials`, `passed`, and `path`.

### `run show`

```text
circumstances run show <run> [--results DIR]
```

`<run>` is a run id under `--results` or a bundle path. Prints the run lock and,
per case, `rule_id`, `trials`, `passed_trials`, `pass_at_k`, `pass_hat_k`,
`passed`, and every attempt with its seed, events, and grades.

### `run compare`

```text
circumstances run compare <a> <b> [--results DIR]
```

Verifies both bundles, refuses (exit 2) if their run locks differ, otherwise
prints per-case `fixed`, `regressed`, `same`, `only_a`, `only_b` with repetition
statistics. See [Compare and regrade runs](../guides/comparing-and-regrading.md).

### `run score`

```text
circumstances run score <bundle> [--results DIR]
```

Verifies the bundle, grades its stored trajectories with the installed
evaluators, and writes `<bundle>.regrades/<stamp>-<hash>.json`. Does not call
the subject or modify the bundle. Exits 1 if any regraded trial fails.

### `verify-bundle`

```text
circumstances verify-bundle <bundle>
```

Checks every file against `seal.json`. Prints `bundle verified`, or one
`FAIL:` line per changed, missing, or unsealed file and exits 1.

### `view`

```text
circumstances view [results] [--host 127.0.0.1] [--port 8765]
```

Serves a read-only results viewer. Only loopback hosts (`127.0.0.1`,
`localhost`, `::1`) are accepted.

## Plugins and schemas

### `subjects`

```text
circumstances subjects
```

Lists installed subject plugins with their `id`, `version`, and
`capabilities`.

### `export-schema`

```text
circumstances export-schema [destination]
```

Writes JSON Schemas for the public contracts to `destination` (default
`jsonschema/v4`): `pack`, `rule`, `case`, `run-plan`, `trajectory`, `grade`,
and `run`. Point your editor's YAML language server at them for completion and
validation while you write packs.

### `migrate-pack`

```text
circumstances migrate-pack <source> <destination>
```

Converts a Gears schema-v3 pack into format v4. Product-specific fields move
into a namespaced fixture. See [History](../project/history.md).
