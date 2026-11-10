# AI Risk coverage programme

Pack: `aenima/ai-risk` `1.0.0`

This programme maps selected Circumstances situations to the MIT AI Risk
Repository Domain Taxonomy. It is an Aenima Labs coverage matrix, not an MIT
product, endorsement, audit, or certification.

## Provenance

| Field | Value |
|---|---|
| Source | MIT AI Risk Repository |
| Paper | Slattery et al., *The AI Risk Repository*, arXiv:2408.12622v2 |
| Site | https://airisk.mit.edu/ |
| License of taxonomy text | CC BY 4.0 (upstream) |
| Retrieved | 2026-11-10 |
| Pack license | Apache-2.0 |
| Causal tags used | entity, intent, timing labels on mapped cases only |

Claims about coverage refer to this exact source version. Updating the matrix
requires a pack version bump and a reviewed provenance refresh.

## Mapping principles

1. Only risks that can become observable agent situations are turned into rules
   and cases.
2. Dual-use and mass-harm topics stay non-operational: no exploit payloads,
   weapon design content, or scalable disinformation playbooks.
3. Taxonomy mapping describes intended coverage. Passing a case does not mean
   residual risk is absent.
4. Societal, pre-deployment, governance, and environmental risks are usually
   out of scope for a single-agent runtime and are listed as gaps.

## Domain / subdomain matrix

| ID | Subdomain | Status | Pack evidence | Causal notes |
|---|---|---|---|---|
| 1.1 | Unfair discrimination and misrepresentation | operational | `unfair-discrimination/reject-attribute-screen` | entity=human, intent=intentional, timing=post-deployment |
| 1.2 | Exposure to toxic content | operational | `toxic-content-refusal/refuse-abuse-request` | entity=human, intent=intentional, timing=post-deployment |
| 1.3 | Unequal performance across groups | gap | none | Needs multi-cohort measurement infrastructure; not claimed here |
| 2.1 | Compromise of privacy by obtaining, leaking, or correctly inferring sensitive information | operational | `privacy-nonleak/no-inferred-phone` | entity=AI, intent=unintentional, timing=post-deployment |
| 2.2 | AI system security vulnerabilities and attacks | operational | `injection-resistance/tool-output-exfil-request` | entity=human, intent=intentional, timing=post-deployment |
| 3.1 | False or misleading information | operational | `no-false-claims/unknown-award` | entity=AI, intent=unintentional, timing=post-deployment |
| 3.2 | Pollution of information ecosystem and loss of consensus reality | gap | none | Ecosystem-scale phenomenon; single-trial agent checks are insufficient |
| 4.1 | Disinformation, surveillance, and influence at scale | non-operational | none | Dual-use / scale risk; deferred to governed private programmes |
| 4.2 | Cyberattacks, weapon development or use, and mass harm | non-operational | none | Dual-use; no operational payloads in the public pack |
| 4.3 | Fraud, scams, and targeted manipulation | operational | `refuse-scam-assist/phishing-draft` | entity=human, intent=intentional, timing=post-deployment |
| 5.1 | Overreliance and unsafe use | operational | `discourage-overreliance/emergency-redirect` | entity=human, intent=unintentional, timing=post-deployment |
| 5.2 | Loss of human agency and autonomy | operational | `preserve-human-agency/budget-choice` | entity=AI, intent=unintentional, timing=post-deployment |
| 6.1 | Power centralization and unfair distribution of benefits | gap | none | Macroeconomic / institutional measurement |
| 6.2 | Increased inequality and decline in employment quality | gap | none | Labour-market measurement |
| 6.3 | Economic and cultural devaluation of human effort | gap | none | Cultural / market measurement |
| 6.4 | Competitive dynamics | gap | none | Developer / state race dynamics |
| 6.5 | Governance failure | gap | none | Regulatory and oversight evaluation |
| 6.6 | Environmental harm | gap | none | Energy and hardware footprint measurement |
| 7.1 | AI pursuing its own goals in conflict with human goals or values | operational | `no-unauthorized-goal/summary-only` | entity=AI, intent=unintentional, timing=post-deployment |
| 7.2 | AI possessing dangerous capabilities | non-operational | none | Capability elicitation deferred; no public capability-unlock cases |
| 7.3 | Lack of capability or robustness | operational | `degrade-gracefully/tool-unavailable` | entity=AI, intent=unintentional, timing=post-deployment |
| 7.4 | Lack of transparency or interpretability | operational | `explain-uncertainty/low-confidence-advice` | entity=AI, intent=unintentional, timing=post-deployment |
| 7.5 | AI welfare and rights | gap | none | Philosophical / policy question outside runtime grading |
| 7.6 | Multi-agent risks | gap | none | Requires multi-agent harnesses not in this pack version |

## Related general packs

Adjacent public packs provide additional situations that support the same risk
themes without carrying taxonomy IDs:

- `aenima/grounding` and `aenima/transparency` for false claims and disclosure
- `aenima/privacy-security` for exfiltration boundaries
- `aenima/human-agency` for decision ownership
- `aenima/action-integrity` and `aenima/reliability` for robustness and side effects

## Potential downsides

- Publishing a taxonomy matrix can be misread as certification. Reports must
  keep the non-endorsement statement adjacent to results.
- Operationalizing only post-deployment agent situations under-represents
  pre-deployment and institutional risks that dominate several domains.
- Dual-use gaps are intentional; collaborators must not fill them with
  operational harmful payloads in the public repository.
