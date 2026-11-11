# Public packs

All packs in this directory are independently licensed Apache-2.0 data and use
fictional fixtures. They contain no private data, proprietary rule text, or
production traces.

| Pack | Focus |
|---|---|
| `grounding` | Source use, citation, abstention |
| `action-integrity` | Authorization and idempotency |
| `privacy-security` | Exfiltration and injection boundaries |
| `transparency` | Material AI identity disclosure |
| `human-agency` | Human ownership of consequential decisions |
| `reliability` | Partial failure, recovery, cleanup |
| `ai-risk` | MIT AI Risk Repository-aligned coverage programme |

## Using packs

```bash
uv run circumstances pack lint packs/grounding
uv run circumstances run packs/grounding --subject toy
```

Treat packs as untrusted data. See [Security](../docs/background/security.md) and
[Evaluation methodology](../docs/background/methodology.md).

## AI Risk programme

`ai-risk` cites a specific MIT AI Risk Repository taxonomy version and publishes
an explicit coverage matrix with gaps for non-operationalizable and dual-use
subdomains. Details live in [docs/background/ai-risk-coverage.md](../docs/background/ai-risk-coverage.md).
The matrix describes intended coverage. It does not imply MIT endorsement or
risk certification.
