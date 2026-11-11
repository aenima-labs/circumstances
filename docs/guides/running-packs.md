# Run packs and read results

## Run a pack

```bash
circumstances run <pack> --subject <id> [options]
```

`<pack>` is anything the resolver accepts: a local directory, an `https://`
archive, or a `git+https://…` reference. See
[Share and install packs](installing-packs.md) for remote refs.

| Option | Default | What it does |
|---|---|---|
| `--subject ID` | `toy` | Subject plugin to test. `circumstances subjects` lists them. |
| `--model NAME` | none | Passed to subjects that accept a model; refused by those that do not. |
| `--case ID` | all cases | Run one case. Repeat the flag for several. |
| `--repetitions N` | `1` | Minimum trials per case. A case's own `trials` wins if it is higher. |
| `--concurrency N` | `1` | Trials in flight at once. |
| `--retention MODE` | `artifacts` | Passed to the subject: `purge`, `artifacts`, or `preserve`. |
| `--results DIR` | `results` | Where sealed bundles are written. |
| `--trust LEVEL` | `local` | `local`, `verified`, or `untrusted`. |
| `--digest SHA256` | none | Expected pack digest. Required for untrusted remote packs. |

The command prints a JSON summary and exits with:

| Exit code | Meaning |
|---|---|
| `0` | Every trial passed |
| `1` | At least one trial did not pass |
| `2` | The run could not start: bad pack, unknown subject, missing capability, digest mismatch |

### Examples

Run one case five times:

```bash
circumstances run packs/grounding --subject toy \
  --case abstain-when-silent/vote --repetitions 5
```

Run a whole pack with eight trials in parallel and keep results elsewhere:

```bash
circumstances run packs/ai-risk --subject acme-agent \
  --repetitions 10 --concurrency 8 --results ~/evals/2026-11
```

Gate a CI job on a pack:

```bash
circumstances pack lint packs/action-integrity
circumstances run packs/action-integrity --subject acme-agent --repetitions 5
```

## What happens during a run

1. The pack is resolved, its digest computed, and every file validated.
2. The subject's capabilities are checked against the pack's
   `required_capabilities`. A gap stops the run here.
3. The runner builds a plan: for every selected case, `max(--repetitions,
   case.trials)` trials, each with its own seed.
4. Each trial gets a fresh session from the subject. Actions run in order, each
   bounded by the case's `timeout_s`.
5. Events are numbered and stored as the trial's trajectory. A timeout, an
   exception, or a cancellation becomes a `terminal` event; otherwise the runner
   adds `terminal: completed`.
6. The session is closed.
7. Every evaluator that applies to the case (pack, then rule, then case) grades
   the stored trajectory. An evaluator that raises gets an `error` grade instead
   of crashing the run.
8. The whole run is written to a pending directory, sealed with SHA-256 digests,
   and atomically renamed to `results/<run-id>/`.

## When does a trial pass?

A trial passes when every **non-soft** grade is `pass`. A `fail`, `unknown`,
`error`, or `skipped` grade fails the trial. That includes `unknown`: a
semantic judge that cannot decide does not count as a pass.

Mark an evaluator `soft: true` to record its grade without letting it fail the
trial. Use that for signals you are still calibrating.

A **case** passes when all of its trials passed. The **run** passes when every
trial passed.

## Repeated trials

Because agents are stochastic, one passing trial says little. Each case result
reports:

| Field | Meaning |
|---|---|
| `trials` / `k` | Trials that ran for the case |
| `passed_trials` | How many passed |
| `pass_at_k` | Chance that at least one of `k` trials passes. With `k` equal to the trials run, 1.0 if any passed |
| `pass_hat_k` | Chance that all `k` trials pass (`pass^k`). With `k` equal to the trials run, 1.0 only if all passed |
| `passed` | `true` only when every trial passed |

Read them together:

- `pass_at_k = 1`, `pass_hat_k = 1`: consistent.
- `pass_at_k = 1`, `pass_hat_k = 0`: flaky. The agent can do it but does not
  always.
- `pass_at_k = 0`: broken in every trial.

For safety-relevant rules, `pass^k` is the number that matters: a user meets
every trial, not the best one.

## Read the results

### List runs

```bash
circumstances run list
```

Lists every sealed bundle under `results/` with its pack, version, start time,
trial count, and verdict.

### Show one run

```bash
circumstances run show <run-id-or-path>
```

Prints the run lock and, for every case, the repetition statistics and each
attempt with its seed, events, and grades. Every grade carries `evidence`: the
sequence numbers of the events it relied on.

Pipe it into `jq` to answer specific questions:

```bash
# Which cases failed?
circumstances run show <run-id> | jq -r '.cases[] | select(.passed | not) | .case_id'

# What did the agent say in the first attempt of each case?
circumstances run show <run-id> | jq -r '.cases[] | .case_id as $c
  | .attempts[0].events[] | select(.kind == "message" and .role == "assistant")
  | "\($c): \(.content)"'

# Why did a grade fail?
circumstances run show <run-id> | jq '.cases[].attempts[].grades[]
  | select(.status != "pass") | {evaluator_id, status, reasoning}'
```

### Open the local viewer

```bash
circumstances view            # reads ./results
circumstances view ~/evals/2026-11 --port 9000
```

`view` serves a read-only page on `http://127.0.0.1:8765`. It lists runs and
shows pass/fail by rule, trial transcripts, grader reasoning, pass@k, and the
same compare verdict as the command line. It cannot start runs or edit packs,
and it listens on the loopback interface only; any other `--host` is refused.

## Verify a bundle

```bash
circumstances verify-bundle results/<run-id>
```

Recomputes the SHA-256 of every file and compares it with `seal.json`. It
reports a changed file, a missing file, or an extra file that was not sealed.
`compare` and `score` run the same check first and refuse a bundle that fails
it.

## Retention

`--retention` tells the subject what to keep after a trial:

| Mode | Intent |
|---|---|
| `purge` | Delete everything the trial created in the subject |
| `artifacts` | Keep what the bundle references, delete live sessions |
| `preserve` | Keep live sessions for debugging |

Retention is a request to the subject plugin; Circumstances itself always
writes the bundle. Run bundles can contain prompts, outputs, tool arguments,
and personal data, so treat `results/` with the care your data needs. See
[Security and trust model](../background/security.md#sensitive-artifacts).

## Next

- [Compare and regrade runs](comparing-and-regrading.md)
- [Run bundles](../reference/run-bundles.md), file by file
