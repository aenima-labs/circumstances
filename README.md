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

## Documentation

Full documentation lives in [`docs/`](docs/README.md) and is published, with
search, at **[circumstances.aenimalabs.com](https://circumstances.aenimalabs.com/)**.

- Getting started: [Installation](docs/getting-started/installation.md) ·
  [Quickstart](docs/getting-started/quickstart.md) ·
  [Core concepts](docs/getting-started/concepts.md)
- Guides: [Write a pack](docs/guides/writing-a-pack.md) ·
  [Connect your agent](docs/guides/connecting-your-agent.md) ·
  [Run packs and read results](docs/guides/running-packs.md) ·
  [Compare and regrade runs](docs/guides/comparing-and-regrading.md) ·
  [Share and install packs](docs/guides/installing-packs.md) ·
  [Write an evaluator](docs/guides/custom-evaluators.md)
- Reference: [Command line](docs/reference/cli.md) ·
  [Pack format v4](docs/reference/pack-format.md) ·
  [Actions and events](docs/reference/actions-and-events.md) ·
  [Built-in evaluators](docs/reference/evaluators.md) ·
  [Run bundles](docs/reference/run-bundles.md) ·
  [Configuration](docs/reference/configuration.md) ·
  [Provider API](docs/reference/provider-api.md) ·
  [Public packs](packs/README.md)
- Background: [Evaluation methodology](docs/background/methodology.md) ·
  [Security model](docs/background/security.md) ·
  [Architecture](docs/background/architecture.md) ·
  [Evaluation landscape](docs/background/landscape.md) ·
  [AI Risk coverage programme](docs/background/ai-risk-coverage.md)
- Project: [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) ·
  [History](docs/project/history.md)

The website itself is built from this repository; see [`site/`](site/README.md).

Products that use Circumstances, including Ænima Labs' own, keep their subject
plugins, fixtures, and cases in their own repositories and use Circumstances
only through its public contracts.

## Status

Circumstances is pre-1.0. Pack format v4 is the initial public format. APIs may
change while adapter contract suites and public pack governance mature.

## License

Apache License 2.0. Individual packs declare their own SPDX license and
provenance in `pack.yaml`.

