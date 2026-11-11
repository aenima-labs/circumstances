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
- Public pack changes need provenance, fictional fixtures, SPDX license
  metadata, and a privacy review against the content inventory.

## AI Risk pack

Updates to `packs/ai-risk` must refresh
[docs/ai-risk-coverage.md](docs/ai-risk-coverage.md), keep dual-use cases
non-operational, and bump the pack version when taxonomy provenance changes.

## Security reports

See [SECURITY.md](SECURITY.md).
