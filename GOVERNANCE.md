# Governance

Circumstances is maintained by Aenima Labs.

## Compatibility

- Pack format `v4` is the initial public format.
- Breaking contract changes require a major package version bump and a
  migration note under `docs/`.
- Public packs version independently of the framework package.

## Reviewers

- Framework contracts and security-sensitive fetch/artifact code require
  maintainer review.
- Public pack publication requires provenance, privacy, and license checks
  described in `docs/content-inventory.md`.
- Dual-use or mass-harm situations remain non-operational in public packs.

## Releases

Maintainers publish GitHub releases with wheel, sdist, checksums, and schema
artifacts. PyPI publication follows the same tag once package ownership is
confirmed.
