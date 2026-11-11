# Security

## Reporting

Report security issues privately to `security@aenimalabs.com`. Please include
reproduction steps, impact, and whether the issue affects pack resolution,
artifact sealing, subject adapters, or hosted provider integrations.

## Trust model

- Packs are untrusted data. They must not execute code in the Circumstances
  process.
- Remote pack fetch requires HTTPS, rejects private/link-local destinations,
  and blocks archive path escape, symlinks, and oversized payloads.
- Hosted consumers should run evaluation workers with least-privilege
  credentials and short-lived run-scoped capabilities.
- Smoke/regex checks are not safety certification.

More detail: [docs/background/security.md](docs/background/security.md).
