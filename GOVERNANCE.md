# Governance

Circumstances is maintained by Ænima Labs.

## Decisions

- Maintainers keep the [roadmap](docs/project/roadmap.md) and revise it in the
  open, through pull requests.
- Changes to public contracts (pack format, run bundles, provider API, plugin
  interfaces) need an RFC under `docs/project/rfcs/`. An RFC is accepted when a
  maintainer approves it after at least a week open for comment.
- Contributors with a record of sustained, careful work may be invited to
  become maintainers.

## Compatibility

- Pack format `v4` is the initial public format.
- Breaking contract changes require a major package version bump and a
  migration note under `docs/`.
- Public packs version independently of the framework package.

## Reviewers

- Framework contracts and security-sensitive fetch/artifact code require
  maintainer review.
- Public pack publication requires the provenance, privacy, and license checks
  in [`CONTRIBUTING.md`](CONTRIBUTING.md#publishing-pack-content).
- Dual-use or mass-harm situations remain non-operational in public packs.

## Releases

`circumstances` and its alias `circs` always share one version. To release,
a maintainer sets it in `src/circumstances/__init__.py` and everywhere in
`packaging/circs/pyproject.toml`, merges, and pushes a `vX.Y.Z` tag. The
release workflow publishes `circumstances` and then `circs` to PyPI through
trusted publishing, then a GitHub release with the wheels, sdists, checksums,
and schema artifacts.
