# Contributing

Circumstances welcomes framework, adapter, evaluator, documentation, and
public-pack contributions.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run mypy
uv run pytest -q
uv run circumstances pack lint packs/grounding
uv run circumstances run packs/grounding --subject toy
```

## Pull requests

- Keep framework contracts agent-agnostic. Product-specific fixtures and
  adapters belong in consumer repositories.
- Prefer small, reviewable changes with tests for contract behavior.
- Do not add executable code inside packs. Packs are untrusted data.
- Public pack changes must pass the checks in
  [Publishing pack content](#publishing-pack-content).

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

Product-specific fixtures and adapters belong in the product's own repository.

## AI Risk pack

Updates to `packs/ai-risk` must refresh
[docs/background/ai-risk-coverage.md](docs/background/ai-risk-coverage.md), keep dual-use cases
non-operational, and bump the pack version when taxonomy provenance changes.

## Security reports

See [SECURITY.md](SECURITY.md).
