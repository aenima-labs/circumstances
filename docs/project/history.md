# History

Circumstances grew out of Gears, a private evaluation harness that Ænima Labs
built to test one product. Gears worked, but its pack format named that
product's data, its graders mixed text matching with meaning, and its results
lived only as long as the sessions behind them.

Circumstances is the public, product-neutral rewrite. Nothing private was
imported: the public packs were written from scratch with fictional fixtures,
and no Gears history is in this repository.

## What changed

| Gears schema v3 | Circumstances pack format v4 |
|---|---|
| Product data fields on every case | A namespaced `fixture` that only the matching subject plugin reads |
| `Turn.user` messages | Typed actions: a literal or generated message, a wait, an environment action, or a plugin extension |
| An `Outcome` | An ordered event trajectory |
| `match` graders | `smoke.text` and `smoke.event` evaluators, labelled as smoke |
| `judge` graders | `semantic.rubric` evaluators that may return `unknown` |
| A fixed `subject` in the pack | Required capabilities in the pack, and a subject plugin chosen at run time |
| Result files | A sealed run bundle |

## Converting an old pack

`circumstances migrate-pack` converts a Gears schema-v3 pack into format v4
data. It is best-effort and exists for teams moving their own private packs.
Product-specific fields move into a namespaced fixture, so a converted pack
still needs that product's subject plugin to run. Review the result with
`circumstances pack lint` before using it. See
[`migrate-pack`](../reference/cli.md#migrate-pack).
