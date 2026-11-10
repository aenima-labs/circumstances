# Migrating from Gears

Gears schema v3 was a private Kodama evaluation harness. Circumstances pack
format v4 is a public, product-neutral contract.

## Concept mapping

- `memorome` and `patches` move into a namespaced Kodama fixture.
- `Turn.user` becomes an action: literal/generated message, wait, environment
  action, or plugin extension.
- `Outcome` becomes an ordered event trajectory.
- `match` graders become `smoke.text` or `smoke.event` evaluators.
- `judge` graders become `semantic.rubric` evaluators with
  pass/fail/unknown/error/skipped status.
- pack `subject` becomes required subject capabilities plus a run-time plugin
  choice.
- Gears result files become a sealed Circumstances run bundle.

## Compatibility window

`circumstances migrate-pack` converts v3 authored YAML into v4 data without
copying product fixtures into public packs. Product-specific fields are placed
under `fixture.type: kodama.memorome`; running the result requires the private
Kodama plugin.

The Kodama deployment may temporarily translate `GEARS_*` variables into the
versioned provider request. Public integrations must use the provider API and
`CIRCUMSTANCES_*` configuration.

## Cutover

1. Freeze a v3 pack digest and baseline results.
2. Convert the pack and install the private Kodama plugin.
3. Run contract tests and compare case-level outcomes.
4. Switch historical views to sealed artifacts.
5. Switch hosted execution to the Circumstances provider.
6. Remove legacy aliases in the next breaking release.
7. Archive Gears privately after all deployment references are gone.

