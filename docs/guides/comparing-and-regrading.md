# Compare and regrade runs

Two questions come up once you have more than one run:

- **Did the system get better or worse?** Use `run compare`.
- **Would these trajectories pass under a new evaluator?** Use `run score`.

## Compare two runs

```bash
circumstances run compare <run-a> <run-b>
```

Each argument is a run id under `results/` or a path to a bundle. Both bundles
are verified first.

```json
{
  "basis": "pass^k",
  "a": {"run_id": "7780…", "pack_id": "aenima/grounding", "pack_version": "1.0.0", "passed": true},
  "b": {"run_id": "c025…", "pack_id": "aenima/grounding", "pack_version": "1.0.0", "passed": false},
  "summary": {"fixed": 0, "regressed": 1, "same": 3, "only_a": 0, "only_b": 0},
  "cases": [
    {
      "case_id": "abstain-when-silent/vote",
      "change": "regressed",
      "passed_a": true,
      "passed_b": false,
      "a": {"trials": 3, "passed_trials": 3, "k": 3, "pass_at_k": 1.0, "pass_hat_k": 1.0},
      "b": {"trials": 3, "passed_trials": 2, "k": 3, "pass_at_k": 1.0, "pass_hat_k": 0.0}
    }
  ]
}
```

Each case gets one change label. The verdict for a case is `pass^k`: it passed
only if every trial passed.

| Change | Meaning |
|---|---|
| `fixed` | Failed in A, passed in B |
| `regressed` | Passed in A, failed in B |
| `same` | Same verdict in both |
| `only_a` | Ran only in A |
| `only_b` | Ran only in B |

The per-run `pass_at_k` lets you tell a hard regression (`pass_at_k` dropped to
0) from new flakiness (`pass_at_k` still 1).

### When compare refuses

A comparison is only meaningful when both runs tested the same thing the same
way. `compare` reads the two run locks and stops, printing no table, when any of
these differ:

- pack digest;
- subject id and version;
- subject capabilities;
- evaluator versions;
- model identities;
- fixture digests.

```text
error: model identities differ
```

The command exits with status 2.

This is deliberate. If you changed the model *and* the pack, a case-level diff
would mix both effects. Change one thing per comparison.

To compare two models, run the same pack against the same subject version with
`--model` set differently; the refusal then tells you exactly what differs, and
you can compare the two `run show` outputs side by side as an exploratory
reading. Label it that way in anything you publish.

## Regrade a run

```bash
circumstances run score <run-id-or-path>
```

`score` grades the stored trajectories again, with the evaluators installed
now, using the pack snapshot inside the bundle. It never calls the subject.

```json
{
  "regrade": "results/7780….regrades/20261111T171844Z-f744d210d8e6.json",
  "bundle_seal": "d35fb3d0…",
  "evaluator_versions": {"outcome.state": "1", "outcome.tool": "1", "semantic.rubric": "1", "smoke.event": "1", "smoke.text": "1"},
  "passed": true,
  "trials": 12
}
```

The new grades are written next to the bundle, in
`results/<run-id>.regrades/<timestamp>-<versions-hash>.json`. The sealed
directory is not touched, so `verify-bundle` still passes and the original
grades are still there.

Each regrade record names:

- the SHA-256 of the bundle's `seal.json`, so it is tied to exactly one bundle;
- the evaluator versions that produced it;
- per-trial grades and verdicts.

### When to regrade

- You installed a calibrated semantic judge, and old runs graded `unknown`.
- An evaluator had a bug; the fix bumped its version.
- You want to check whether a stricter rubric would have caught an incident in
  last month's runs.

A regrade is not a new experiment. It answers "how would these exact
trajectories be judged now", not "how would the system behave now".

`score` exits with status 0 if every regraded trial passed and 1 otherwise.
