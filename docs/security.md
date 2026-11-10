# Security and trust model

Circumstances runs third-party descriptions of tests against systems that may
hold sensitive data or powerful tools. Packs are untrusted data by default.

## Trust levels

- `local`: authored by the operator and loaded from a local directory.
- `verified`: digest-pinned and approved by an operator policy.
- `untrusted`: remote or otherwise unapproved content.

Trust never grants ambient credentials. It only selects an operator-defined
capability policy.

## Pack restrictions

- Pack-relative paths are resolved and confined beneath the resolved pack.
- Archives reject traversal, links, special files, excessive size, and
  excessive file counts.
- Git sources resolve to an immutable commit; moving branches and tags are
  recorded by commit.
- Digests cover every material file while excluding transport metadata.
- Templates receive declared variables only. They never receive `os.environ`.
- Secret references are symbolic. The operator maps them to values and allowed
  destinations outside the pack.
- Network access is default-deny and limited by scheme, host, port, redirect,
  and resolved-address policy.
- Packs cannot embed Python, shell, JavaScript, or evaluator code.

## Execution isolation

Subject plugins declare their capabilities and required permissions. Hosted
workers use dedicated identities with no platform administration, product
database, application bucket, or broad secret-manager access. Every run gets
short-lived credentials bound to its run, target, audience, and allowed event
types.

## Sensitive artifacts

Run bundles may contain prompts, model drafts, delivered output, tool
arguments/results, environment observations, judge requests, and personal
data. A run plan therefore declares classification, provider allowlist,
redaction, retention, export, and deletion policy before execution.

Public packs and CI fixtures contain fictional data only. Real-person or
private-presence evaluation is an explicit operator-approved mode.

## Reporting vulnerabilities

Report security issues privately to `security@aenimalabs.com`. Do not include
real credentials, private fixture content, or personal data in a public issue.

