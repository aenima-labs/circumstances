# Release cutover checklist

Date: 2026-11-10

## Circumstances public repository

- Organization: `aenima-labs`
- Repository: https://github.com/aenima-labs/circumstances
- Package: `circumstances` `0.1.0`
- Pack format: v4
- Public packs: grounding, action-integrity, privacy-security, transparency,
  human-agency, reliability, ai-risk
- AI Risk coverage matrix: `docs/ai-risk-coverage.md`

## Kodama consumer boundary

- Private plugin and packs: `kodama/evals`
- Provider API: `circumstances.provider.v1`
- Least-privilege runner/catalog service accounts in Terraform
- Artifact-backed historical readout in the platform UI

## Gears retirement

- Private repository: `chernov-consulting/gears`
- Notice files: `README.md` deprecation banner and `ARCHIVED.md`
- New work uses Circumstances; Gears remains for audit history

## Verification performed

- Public packs lint and toy-subject runs pass
- Public pack evaluator self-tests pass
- Gears v3 migration moves product fixtures into namespaced Kodama fixtures
- Provider request/event contract tests pass in Kodama
- Terraform validate succeeds for Circumstances runner/catalog resources
