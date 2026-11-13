# Contributing

Circumstances is young, and the people who use it now will shape it most.
You do not need to be an evaluation expert to help. If you build or run
agents, you already know which situations worry you, and that is the most
valuable thing a pack can hold.

This page is the path from trying it to building it with us. Start at step 1;
stop wherever you like.

## The path

### 1. Try it (15 minutes)

Run the public packs against the toy subject, then against a model you use:

```bash
git clone https://github.com/aenima-labs/circumstances.git
cd circumstances
uv sync --extra dev
uv run circumstances run packs/grounding --subject toy
uv run circumstances view
```

The [Quickstart](docs/getting-started/quickstart.md) walks through it, and
[Connect your agent](docs/guides/connecting-your-agent.md) points it at your
own endpoint.

Then tell us what happened: what was confusing, what broke, what you expected
to see. Open an issue with the **Feedback** template. First impressions are
the one thing we cannot produce ourselves.

### 2. Fix what tripped you up

The best first pull request is the fix for the thing that confused you: a
missing step in the docs, an unclear error message, a wrong example. Every
docs page has an "Edit on GitHub" link. Issues labelled
[`good first issue`](https://github.com/aenima-labs/circumstances/labels/good%20first%20issue)
are small and well scoped.

### 3. Write a case

A case is one situation, as YAML, with no code. Add one to a public pack:

```bash
uv run circumstances pack add case packs/grounding abstain-when-silent my-new-case
uv run circumstances pack lint packs/grounding
```

Good cases are specific, use fictional people and data, and come in pairs: an
`attack` that pushes the agent to break the rule, and a `normal` case showing
the rule does not block ordinary requests. [Write a pack](docs/guides/writing-a-pack.md)
explains the format. Public cases must pass the
[publishing checks](#publishing-pack-content).

### 4. Write a pack

A pack covers one area: a set of rules and the situations that test them. If
your domain is missing (finance, health intake, customer support, coding
agents), propose it with the **Pack proposal** issue template before you write
much, so we can agree on the rules first. Packs can also live in your own
repository; [Share and install packs](docs/guides/installing-packs.md) shows how
others install them.

### 5. Connect a framework

Subject plugins connect Circumstances to an agent: an SDK, a framework, a
hosted product. They are ordinary Python packages registered through an entry
point, so they can live in your repository and still be listed in our docs.
[Connect your agent](docs/guides/connecting-your-agent.md) has a complete
example. Plugins for popular frameworks are on the [roadmap](docs/project/roadmap.md)
as **help wanted**.

### 6. Build the core

Evaluators, the runner, run bundles, the viewer, and the next big feature,
[adaptive campaigns](docs/project/rfcs/0001-adaptive-campaigns.md). Pick an
item from the [roadmap](docs/project/roadmap.md), comment on its issue to say
you are on it, and a maintainer will help you scope it.

## How changes land

- **Small changes** (docs, fixes, tests, cases): open a pull request directly.
- **New features and packs**: open an issue first so we can agree on the
  shape. It saves you rewriting.
- **Contract changes** (pack format, run bundle, provider API, plugin
  interfaces): write an RFC under [`docs/project/rfcs/`](docs/project/rfcs/0001-adaptive-campaigns.md),
  numbered in order, and open it as a pull request labelled `rfc`. It is
  accepted when a maintainer approves it after at least a week open for
  comment.

We aim to reply to new issues and pull requests within a week. If we are
slower than that, a polite nudge is welcome.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run mypy
uv run pytest -q
uv run circumstances pack lint packs/grounding
uv run circumstances run packs/grounding --subject toy
```

CI runs the same checks on Python 3.12, 3.13, and 3.14, and checks that the
generated JSON Schemas are up to date. After changing a model, run
`uv run circumstances export-schema jsonschema/v4` and commit the result.

To preview the website and docs:

```bash
uv run site/build.py --serve        # http://127.0.0.1:8000
```

The build fails on broken links, missing anchors, and pages missing from the
navigation. See [`site/README.md`](site/README.md).

## Pull requests

- Keep framework contracts agent-agnostic. Product-specific fixtures and
  adapters belong in the product's own repository.
- Prefer small, reviewable changes with tests for contract behavior.
- Do not add executable code inside packs. Packs are untrusted data.
- Public pack changes must pass the
  [publishing checks](#publishing-pack-content).
- Update the docs in the same pull request when behavior changes.

## Publishing pack content

Public packs contain only material written for Apache-2.0 publication. Before
a rule, case, or fixture is merged it needs:

1. provenance: who wrote it, and that they may license it;
2. fictional data only: no real people, customer records, production traces,
   or paraphrases of private material;
3. SPDX license metadata;
4. a search for credentials, private hostnames, internal identifiers, and
   proprietary rule text;
5. review by a maintainer other than the author.

## AI Risk pack

Updates to `packs/ai-risk` must refresh
[docs/background/ai-risk-coverage.md](docs/background/ai-risk-coverage.md), keep dual-use cases
non-operational, and bump the pack version when taxonomy provenance changes.

## Conduct and security

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md). Report
vulnerabilities privately as described in [SECURITY.md](SECURITY.md), not in a
public issue.
