# Configuration

Circumstances has little configuration on purpose. Packs never read it.

## Environment variables

Read by the `openai-compatible` subject only:

| Variable | Default | Description |
|---|---|---|
| `CIRCUMSTANCES_OPENAI_BASE_URL` | `http://127.0.0.1:11434/v1` | API base URL; `/chat/completions` is appended |
| `CIRCUMSTANCES_OPENAI_API_KEY` | empty | Sent as `Authorization: Bearer …` when set |
| `CIRCUMSTANCES_OPENAI_MODEL` | empty, *required* | Model name; `--model` overrides it |

Packs and fixtures never see environment variables.

## Project file: `circumstances.yaml`

Optional. Gives remote packs short names. Circumstances looks in the working
directory and each parent up to the repository root.

```yaml
sources:
  - name: acme/inbox
    ref: git+https://github.com/acme/packs.git#ref=v0.3.0&path=packs/inbox
    trust: untrusted
    digest: "3b1f…e9"
    revision: v0.3.0
  - name: team/drafts
    ref: ./evals/drafts
    trust: local
```

| Field | Default | Description |
|---|---|---|
| `name` | *required* | Name to use with `pack add` |
| `ref` | *required* | Local path (relative to this file), `https://` archive, or `git+https://` ref |
| `trust` | `untrusted` | `local`, `verified`, or `untrusted` |
| `digest` | none | Expected SHA-256; required for `untrusted` |
| `revision` | none | Informational |

## Files and directories

| Path | Purpose |
|---|---|
| `results/` | Default location for sealed run bundles (`--results` changes it) |
| `~/.cache/circumstances/packs/` | Cache of resolved remote packs |
| `circumstances.yaml` | Project pack sources |
| `jsonschema/v4/` | Default output of `export-schema` |

## Resolver limits

Applied to every remote pack:

| Limit | Value |
|---|---|
| Scheme | HTTPS only (`git+https` for git) |
| Download size | 100 MiB |
| Unpacked size | 250 MiB |
| Files | 5,000 |
| Redirects | 3 |
| Private, loopback, link-local hosts | refused |

These limits are fixed in the command line. Code that embeds Circumstances can
pass its own `ResolverPolicy`.

## Plugin entry points

| Group | Registers | Example |
|---|---|---|
| `circumstances.subjects` | Subject plugins, keyed by id | `acme-inbox = "acme_circumstances:AcmeSubjectPlugin"` |
| `circumstances.evaluators` | Evaluator plugins | `citation-targets = "acme_evals:CitationTargetsEvaluator"` |

See [Connect your agent](../guides/connecting-your-agent.md) and
[Write an evaluator](../guides/custom-evaluators.md).
