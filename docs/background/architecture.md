# Circumstances architecture

> Status: Accepted
> Date: 2026-11-10
> Decision: Circumstances is a public, agent- and rule-agnostic situational
> testing framework. Product integrations remain outside the framework.

## Principles

1. Packs are data, never executable code.
2. Core knows no product, fixture, model provider, or deployment.
3. Subjects expose capabilities and produce ordered events.
4. Execution and evaluation are separate; stored trajectories can be regraded.
5. Results are immutable evidence bundles, not views over mutable services.
6. Untrusted packs receive no ambient secrets or network access.
7. Fast text checks are smoke tests. Semantic claims require calibrated
   semantic, outcome, state, or human evaluation.

## Public monorepo

The `aenima-labs/circumstances` repository contains:

- `src/circumstances`: core models, pack resolver, runner, evaluator registry,
  artifact store, CLI, and provider API types.
- `packs`: general Aenima Labs packs with fictional Apache-2.0 fixtures.
- `examples`: neutral subjects that require no private service.
- `jsonschema`: generated pack and run schemas.
- `docs`: trust model, pack authoring, adapter authoring, and methodology.

It contains no private product source, personal data, proprietary rule text,
private endpoints, cloud project names, or credentials.

## Plugin boundary

Subject plugins are installed separately and registered through Python entry
points. A plugin exposes:

- a stable descriptor and capability set;
- `prepare(TrialSpec) -> TrialSession`;
- `execute(Action) -> list[Event]`;
- `close()` with an explicit retention decision.

Fixtures are namespaced data passed to the selected subject plugin. Core treats
their configuration as opaque JSON. Evaluators use the same registry model and
return evidence references into immutable trajectory events.

A product that keeps its subject private ships its own plugin and fixture
provider. It installs a released Circumstances distribution and implements only
these public contracts.

## Run lifecycle

1. Resolve an immutable pack and record source revision plus SHA-256.
2. Validate schema, capabilities, permissions, evaluator requirements, and
   pack trust policy.
3. Compile a `RunPlan` containing cases, repetitions, seeds, timeouts,
   concurrency, retention, and failure policy.
4. Prepare an isolated subject session and execute typed actions.
5. Persist the ordered event trajectory before evaluation.
6. Evaluate the stored trajectory using deterministic, semantic, outcome, and
   optional human evaluators.
7. Seal the run bundle with hashes and a complete provenance manifest.
8. Report from the sealed bundle. Live sessions may then be deleted.

## Compatibility

Pack format v4 is the public contract. `migrate-pack` converts packs from
Gears, the private harness Circumstances replaced (see
[History](../project/history.md)); Gears formats and variables are not part of
the public API.

Framework API, pack format, and individual packs follow independent semantic
versioning. Comparisons are valid only when their run locks declare compatible
pack, fixture, subject, evaluator, and model identities.

