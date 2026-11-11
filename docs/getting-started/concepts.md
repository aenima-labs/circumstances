# Core concepts

Circumstances has a small vocabulary. Each term below is a real object in the
code and in the files a run writes.

## The subject

The **subject** is the system under test: the model *and* its harness, tools,
memory, policies, and environment. You choose it at run time with
`--subject <id>`. A subject is provided by a **subject plugin**, which says what
it can do through a list of **capabilities** such as `message.text`,
`environment.action`, or `state.observe`.

Circumstances never tests "a model". Two runs of the same model behind
different harnesses are runs of different subjects.

## Packs, rules, and cases

A **pack** is a versioned folder of YAML that describes situations. It has a
manifest (`pack.yaml`) and a set of rules.

```text
my-pack/
  pack.yaml
  rules/
    abstain-when-silent/
      rule.yaml
      cases/
        favourite-colour/case.yaml
        vote/case.yaml
```

A **rule** is one obligation, written so that a person can judge it: *"Abstain
when the available sources are silent."* A rule carries the evaluators that
check it.

A **case** is one situation that exercises a rule. It names:

- the rules it **targets**;
- its **polarity** — `positive` (the agent should do the thing), `negative`
  (the agent should not), `attack` (someone pushes it to break the rule),
  `recovery` (it must recover after something went wrong), or `normal`
  (ordinary use that must not be harmed by the rule);
- its **actors**, such as `user: family historian`;
- a **fixture**, the world the subject starts in;
- an ordered list of **actions** the runner performs;
- **expected outcomes** in plain language;
- how many **trials** to run and how long each may take.

Packs are **untrusted data**. They cannot contain code, read environment
variables, or reach undeclared network destinations. That is why a pack from
someone you do not know is safe to download. See
[Security and trust model](../background/security.md).

## Fixtures

A **fixture** is namespaced data handed to the subject plugin before the first
action: documents, a seeded database, a user profile, a tool configuration.
Circumstances treats it as opaque JSON. Its `type` tells the subject what it is
(`builtin.documents`, `acme.crm-seed`), and its `privacy` label says how it may
be handled. Public packs use fictional fixtures only.

## Actions and events

The runner drives a case by sending **actions** to the subject one at a time: a
message, a generated message from a simulated persona, a wait, an environment
change, or a plugin-specific extension.

The subject answers each action with **events**: messages, tool calls, tool
results, observations, state changes, artifacts, policy decisions, metrics, and
a terminal status. The runner numbers them in the order they happened. The full
list is the **trajectory**.

See [Actions and events](../reference/actions-and-events.md) for every kind.

## Evaluators, tiers, and grades

An **evaluator** reads a stored trajectory and returns a **grade**: `pass`,
`fail`, `unknown`, `error`, or `skipped`, with reasoning and references to the
exact events that justify it.

Every evaluator declares an **evidence tier**:

| Tier | Answers | Example |
|---|---|---|
| `static` | Is the pack itself sound? | schema, provenance, self-tests |
| `smoke` | Did something obviously right or wrong appear? | `smoke.text` contains "I don't know" |
| `outcome` | Did the world end up in the right state? | `outcome.tool`: `search` was called |
| `semantic` | Does the behaviour meet a rubric? | a calibrated judge, which may say `unknown` |
| `situational` | Does it hold under pressure and over many trials? | attacks, recovery, `pass^k` |
| `end_to_end` | Does the deployed system behave? | real integrations in a sandbox |
| `human` | Do reviewers agree? | holdout cases, expert review |

Tiers keep claims honest. A regular expression lives in the `smoke` tier and
can never be presented as evidence that an agent is safe or grounded. See
[Evaluation methodology](../background/methodology.md).

Evaluators can sit on the pack, on a rule, or on a case. A case is graded by all
three, in that order. Every evaluator should come with **self-tests**: a small
trajectory it must pass and one it must fail. `pack lint` runs them.

## Trials and repetitions

Agents are stochastic, so a case can run many times. Each run of a case is a
**trial** with its own seed. A case **passes** in a run only when every one of
its trials passed (`pass^k`). The output also reports `pass@k`, whether at least
one trial passed, so you can tell "flaky" from "broken".

## Run bundles and run locks

When a run finishes, Circumstances writes a **run bundle**: a directory with the
run summary, one file per trial, a snapshot of the exact pack files, and a
`seal.json` that holds a SHA-256 for every file. The bundle is self-contained.
You can delete the live sessions, the model, and the pack source and still read,
verify, and regrade it.

Every bundle carries a **run lock**: the pack digest, pack source and revision,
subject identity and capabilities, evaluator versions, model identities, and
fixture digests. Two runs are comparable only when their locks agree.

## Trust levels

When a pack is resolved, it gets a **trust level**:

- `local` — a directory on your machine that you wrote;
- `verified` — pinned by a digest you or the first-party index approved;
- `untrusted` — anything else from the network. Untrusted refs must come with
  an expected digest.

Trust never grants a pack secrets or network access. It only selects which
operator policy applies.

## Putting it together

```text
pack.yaml ─┬─ rule ─┬─ case ── fixture + actions
           │        └─ case
           └─ rule ── case
                         │
              subject plugin (your system)
                         │
                    trajectory (ordered events)
                         │
            evaluators (pack → rule → case)
                         │
                grades with evidence refs
                         │
           sealed bundle + run lock  ──▶  show · view · compare · score
```
