# Circumstances

Test agents under the circumstances.

Circumstances is an open-source framework for exercising complete agent
systems—model, harness, tools, memory, and environment—inside versioned,
multi-step situations. Packs declare rules, cases, fixtures, actions, and
evidence requirements. Subject plugins connect any agent without putting
product concepts into the framework.

## What it provides

- Strict, data-only pack format v4.
- Agent-agnostic subject and fixture plugins.
- Ordered trajectories of messages, tools, observations, state, artifacts,
  policy decisions, and terminal outcomes.
- Fast smoke checks clearly separated from outcome and semantic evidence.
- Repeated trials, seeds, `pass@k`/`pass^k`-ready results, and immutable run
  locks.
- Self-contained, hash-sealed artifacts that can be regraded after live trial
  cleanup.
- General Aenima Labs packs built on fictional, independently licensed data.
- A pack-and-run command line, including templates, a digest-pinned pack index,
  and a read-only local viewer. See the
  [evaluation landscape](docs/landscape.md).

## Five-minute quickstart

```bash
uv sync --extra dev
uv run circumstances pack lint packs/grounding
uv run circumstances run packs/grounding --subject toy
uv run circumstances view
```

The toy subject is deterministic and requires no model key or private service.
Results are written beneath `results/<run-id>/`.

To test an OpenAI-compatible endpoint:

```bash
export CIRCUMSTANCES_OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export CIRCUMSTANCES_OPENAI_MODEL=your-model
uv run circumstances run packs/grounding --subject openai-compatible
```

## Pack layout

```text
pack.yaml
rules/
  rule-id/
    rule.yaml
    cases/
      case-id/
        case.yaml
```

Packs are untrusted data. They cannot contain executable evaluators, access the
process environment, or declare unrestricted network destinations.

## Evaluation tiers

1. Static schema, provenance, permissions, and evaluator self-tests.
2. Fast smoke/protocol checks, including exact strings and regular expressions.
3. Deterministic outcome and state checks.
4. Calibrated semantic rubrics with an explicit `unknown` result.
5. Repeated situational trajectories.
6. End-to-end observable-action evaluation.
7. Holdout and human review.

Smoke checks are useful for fast feedback. They do not establish that an agent
is safe, grounded, private, fair, or compliant.

## Architecture and trust

- [Architecture](docs/architecture.md)
- [Evaluation landscape](docs/landscape.md)
- [Security model](docs/security.md)
- [Evaluation methodology](docs/evaluation-methodology.md)
- [AI Risk coverage programme](docs/ai-risk-coverage.md)
- [Migration from Gears](docs/migration-from-gears.md)
- [Public/private content inventory](docs/content-inventory.md)
- [Public packs](packs/README.md)

Kodama is a private first-party consumer. Its adapter, KDL, fixtures, and cases
remain in the Kodama repository and use Circumstances solely through public
contracts.

## Status

Circumstances is pre-1.0. Pack format v4 is the initial public format. APIs may
change while adapter contract suites and public pack governance mature.

## License

Apache License 2.0. Individual packs declare their own SPDX license and
provenance in `pack.yaml`.

