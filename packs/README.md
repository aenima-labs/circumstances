# Public packs

All packs in this directory are independently licensed Apache-2.0 data and use
fictional fixtures. They are not Kodama presence tests and contain no private
donor data, KDL text, or production traces.

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
uv run circumstances lint-pack packs/grounding
uv run circumstances run packs/grounding --subject toy
```

Treat packs as untrusted data. See [Security](../docs/security.md) and
[Evaluation methodology](../docs/evaluation-methodology.md).

## AI Risk programme

`ai-risk` cites a specific MIT AI Risk Repository taxonomy version and publishes
an explicit coverage matrix with gaps for non-operationalizable and dual-use
subdomains. Details live in [docs/ai-risk-coverage.md](../docs/ai-risk-coverage.md).
The matrix describes intended coverage. It does not imply MIT endorsement or
risk certification.
