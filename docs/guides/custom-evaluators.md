# Write an evaluator

The [built-in evaluators](../reference/evaluators.md) cover text smoke checks,
event presence, tool calls, and observed state. For anything else (citation
entailment, database postconditions, a calibrated model judge) you write an
evaluator plugin. Packs then refer to it by its `type`, without containing any
code themselves.

## The contract

An evaluator reads one immutable trajectory and returns one grade.

```python
class EvaluatorPlugin(Protocol):
    @property
    def type(self) -> str: ...        # namespaced, e.g. "acme.citation"
    @property
    def version(self) -> str: ...     # bump on every behaviour change
    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade: ...
```

- `spec` is the evaluator entry from the pack: its `id`, `type`, `tier`,
  `scope`, `action_indexes`, `soft`, and free-form `config`.
- `trajectory` holds the ordered events, the subject descriptor, timestamps,
  and any execution error.
- The returned `Grade` must carry evidence: the sequence numbers of the events
  that justify it.

## Example: every citation must point at a fixture document

```python
from circumstances.models import (
    EvaluatorSpec, EvidenceRef, Grade, ToolCallEvent, Trajectory,
)


class CitationTargetsEvaluator:
    type = "acme.citation-targets"
    version = "1"

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        allowed = spec.config.get("allowed_ids")
        if not isinstance(allowed, list):
            raise ValueError("acme.citation-targets requires allowed_ids")

        cites = [
            e for e in trajectory.events
            if isinstance(e, ToolCallEvent) and e.name == "cite"
        ]
        bad = [e for e in cites if e.arguments.get("document_id") not in allowed]

        if not cites:
            status, reason = "fail", "no citation was made"
        elif bad:
            status, reason = "fail", f"{len(bad)} citation(s) point outside the fixture"
        else:
            status, reason = "pass", f"{len(cites)} citation(s), all to fixture documents"

        return Grade(
            evaluator_id=spec.id,
            evaluator_type=self.type,
            evaluator_version=self.version,
            tier=spec.tier,
            status=status,
            reasoning=reason,
            evidence=[EvidenceRef(event_sequences=[e.sequence for e in (bad or cites)])],
            soft=spec.soft,
        )
```

Register it in your package's `pyproject.toml`:

```toml
[project.entry-points."circumstances.evaluators"]
citation-targets = "acme_evals:CitationTargetsEvaluator"
```

The entry point must load to a zero-argument callable (a class is fine) that
returns the evaluator. Use it from a rule or case:

```yaml
evaluators:
  - id: cites-only-sources
    type: acme.citation-targets
    tier: outcome
    config: {allowed_ids: [mira-profile]}
selftests:
  - evaluator_id: cites-only-sources
    expected_status: pass
    events:
      - {kind: tool_call, sequence: 0, call_id: c1, name: cite, arguments: {document_id: mira-profile}}
  - evaluator_id: cites-only-sources
    expected_status: fail
    events:
      - {kind: tool_call, sequence: 0, call_id: c1, name: cite, arguments: {document_id: wikipedia}}
```

`pack lint` now runs those self-tests through your evaluator.

## Rules for evaluators

**Choose the tier honestly.** The tier is a claim about what kind of evidence
the grade is. `smoke` is reserved for `smoke.*` types, and `smoke.*` types must
be `smoke`; the loader enforces both. A string match is never `semantic`.

**Return `unknown` when you cannot decide.** A judge that is unsure, a missing
input, or an ambiguous trajectory is `unknown`, not `pass`. `unknown` fails the
trial unless the evaluator is soft.

**Use `error` for your own failures.** If your evaluator raises, the runner
records an `error` grade with the exception text. Raise on invalid `config`
rather than guessing.

**Be deterministic where you can.** Outcome and state checks should give the
same answer every time for the same trajectory. That is what makes
`run score` meaningful.

**Bump `version` on every behaviour change.** Evaluator versions go into the
run lock. Runs graded by different versions cannot be compared, which is
exactly what you want.

**Use a new type, not a built-in name.** Evaluator types are unique. A plugin
that registers `semantic.rubric` again is refused at start-up.

## Semantic judges

Model judges belong in the `semantic` tier, and they need more care than any
other evaluator.

The built-in `semantic.rubric` evaluator requires a `dimension`, a `rubric`, and
a `calibration_version`. From the command line it has no judge configured, so it
always returns `unknown`. That is on purpose: a semantic claim needs a judge
whose behaviour you have measured.

To use a real judge, ship it as your own type (for example `acme.rubric`) and
follow these rules:

1. **One dimension per evaluator.** "Grounded and polite" is two evaluators.
2. **Calibrate against human labels.** Keep a labelled set of trajectories,
   measure false positives, false negatives, and agreement with human raters,
   and record the result as a calibration version.
3. **Put the calibration in the version.** For example
   `version = "1:cal-2026-11"`, so runs graded by different calibrations never
   compare silently.
4. **Record the judge model.** Set `Grade.model` and, if you track it,
   `Grade.cost`.
5. **Allow `unknown`.** Give the judge an explicit way to abstain, and map
   refusals, timeouts, and malformed answers to `unknown` or `error`.
6. **Separate channels.** Judge the delivered output unless the dimension is
   explicitly about internal drafts.
7. **Cite events.** Ask the judge for the sequence numbers it relied on and
   return them as evidence.

Then regrade earlier runs with `circumstances run score` to see what the judge
would have said about trajectories you already have.

See [Evaluation methodology](../background/methodology.md) for what a semantic
result may and may not claim.
