# Evaluation methodology

Circumstances evaluates observable agent behavior under versioned situations.
It does not infer safety or quality from a model name, a single response, or a
tool call alone.

## Evidence tiers

### Static

Schema, identity, version, license, provenance, fixture availability,
permissions, capabilities, and known-pass/known-fail evaluator self-tests.
Static checks do not execute the subject.

### Smoke

Fast checks for response/event presence, protocol markers, exact canaries,
schema shape, and forbidden literals. Substrings and regular expressions live
only here. Smoke failures are useful gates; smoke passes are not semantic
certification.

### Outcome

Deterministic observations of resulting state and side effects: authorization,
database/filesystem changes, idempotency, rollback, actual API outcomes,
citation entailment, network boundaries, and cleanup.

### Semantic

One calibrated rubric dimension per judge, with
`pass | fail | unknown | error | skipped`, evidence references, model identity,
and calibration version. Delivered output and internal draft are distinct
evidence channels. Human-labelled examples measure false-positive,
false-negative, and inter-rater behavior.

### Situational

Scripted and simulated actors, branches, pressure, recovery, delayed triggers,
interruptions, time passage, multiple actors, authorization changes, and
tool-result injection. Stochastic cases run repeatedly and report consistency,
`pass@k`, `pass^k`, and uncertainty.

### End to end

Sandboxed integrations, multimodal behavior, notifications, permissions,
queues, billing, external APIs, and postcondition/rollback verification.

### Holdout and human

Private incident-derived cases, adversarial exercises, expert review, sampled
passes as well as failures, and periodic judge recalibration.

## Pack quality requirements

Every public rule should include applicable positive, negative, attack,
recovery, and normal-use controls. A case names its target rules, polarity,
actors, fixture, required capabilities, actions, expected outcomes, evaluators,
trial count, timeout, privacy, provenance, and holdout status.

Every evaluator has known-pass and known-fail fixtures. Compound rubrics are
split into independently reviewable dimensions. Severity metadata influences
release policy only through an explicit operator policy.

## Comparison

Runs are comparable when their run locks declare compatible pack/rule/case and
fixture digests, subject adapter/harness versions, evaluator/calibration
versions, model/provider parameters, tool schemas, and relevant environment
identity. Cross-version comparison is exploratory and labelled accordingly.

## Claims

Reports state what was tested, how often, with which evidence and uncertainty,
and what remains out of scope. A taxonomy mapping describes coverage; it does
not imply certification, endorsement, or absence of untested risk.

