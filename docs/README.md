# Circumstances documentation

Circumstances tests complete agent systems—model, harness, tools, memory, and
environment—inside versioned, multi-step situations. These pages explain how to
install it, write packs, connect your own agent, and read the evidence a run
leaves behind.

The same pages are published at
[circumstances.aenimalabs.com](https://circumstances.aenimalabs.com/docs/),
with search and navigation.

## Start here

| If you want to… | Read |
|---|---|
| Install the command line | [Installation](getting-started/installation.md) |
| See a run end to end in five minutes | [Quickstart](getting-started/quickstart.md) |
| Learn the vocabulary: pack, rule, case, trajectory, grade | [Core concepts](getting-started/concepts.md) |

## Guides

Task-oriented walkthroughs.

- [Write a pack](guides/writing-a-pack.md) — from `pack init` to a linted,
  self-tested pack.
- [Connect your agent](guides/connecting-your-agent.md) — test an
  OpenAI-compatible endpoint, or write a subject plugin for any system.
- [Run packs and read results](guides/running-packs.md) — repetitions, case
  selection, retention, the local viewer, and bundle verification.
- [Compare and regrade runs](guides/comparing-and-regrading.md) — regressions,
  run locks, and grading stored trajectories again.
- [Share and install packs](guides/installing-packs.md) — the pinned index,
  project sources, remote refs, trust, and digests.
- [Write an evaluator](guides/custom-evaluators.md) — evaluator plugins and
  calibrated semantic judges.

## Reference

Exact fields, commands, and formats.

- [Command line](reference/cli.md)
- [Pack format v4](reference/pack-format.md)
- [Actions and events](reference/actions-and-events.md)
- [Built-in evaluators](reference/evaluators.md)
- [Run bundles](reference/run-bundles.md)
- [Configuration](reference/configuration.md)
- [Provider API v1](reference/provider-api.md)
- [Public packs](../packs/README.md)

## Background

Why Circumstances is shaped the way it is.

- [Evaluation methodology](background/methodology.md) — evidence tiers and what
  a result may claim.
- [Security and trust model](background/security.md) — why packs are data and
  what the resolver refuses.
- [Architecture](background/architecture.md) — principles, plugin boundary, and
  run lifecycle.
- [Evaluation landscape](background/landscape.md) — how Circumstances relates to
  Inspect, Harbor, Promptfoo, Garak, PyRIT, and trace platforms.
- [AI Risk coverage programme](background/ai-risk-coverage.md) — the mapping to
  the MIT AI Risk Repository taxonomy.

## Project

- [Contributing](../CONTRIBUTING.md)
- [Governance](../GOVERNANCE.md)
- [Security policy](../SECURITY.md)
- [Code of conduct](../CODE_OF_CONDUCT.md)
- [Roadmap](project/roadmap.md)
- [RFC 1: Adaptive campaigns](project/rfcs/0001-adaptive-campaigns.md)
- [History](project/history.md)

## Conventions in these pages

- Commands are shown with `uv run circumstances …` when they run from a clone
  of this repository, and as plain `circumstances …` when the package is
  installed in your environment. Both forms are equivalent.
- Every command that prints structured output prints JSON, so you can pipe it
  into `jq`.
- "Pack format v4" is the only public format. Fields marked *required* are
  rejected by the loader when missing; every other field has the default shown.
