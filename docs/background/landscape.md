# Evaluation landscape

> Survey date: 2026-11-11
> Decision: Circumstances stays a data-only situational runner. It borrows the
> command-line shape of Inspect and Harbor, and it does not become a benchmark
> hub, an attack generator, or a hosted trace product.

This note records what the 2026 agent-evaluation field actually does, where
Circumstances is different on purpose, and the two adoption surfaces that were
missing: a pack-and-run command line, and a local results viewer.

## Four jobs, not one market

Peers split into four jobs. Circumstances belongs in the fourth.

### Run someone else's benchmark

[Inspect](https://inspect.aisi.org.uk/) (UK AI Security Institute) is the
reference runner. The [command reference](https://inspect.aisi.org.uk/reference/)
includes `inspect eval`, `eval-set`, `eval-retry`, `list`, `log`, `score`,
`trace`, `sandbox`, and `view`. The library holds 200+ tasks. Tasks are Python.
The [log viewer](https://inspect.aisi.org.uk/log-viewer.html) reads local logs.
Inspect also runs external agents such as Claude Code, Codex CLI, and Gemini CLI,
and it can sandbox untrusted model code.

[Harbor](https://github.com/harbor-framework/harbor) is the container harness
behind Terminal-Bench. Operators install datasets from Harbor Hub and run them
with `harbor run -d org/name@version`, then open `harbor view jobs`. As of
November 2026 the hub carries public datasets such as Terminal-Bench,
SWE-bench, and τ-bench variants. [Inspect Harbor](https://meridianlabs-ai.github.io/inspect_harbor/registry.html)
already loads those datasets as Inspect tasks. Both tools measure task success
for an agent in an environment. They do not ship versioned obligation packs.

### Red-team a model or an endpoint

[Promptfoo](https://www.promptfoo.dev/docs/usage/command-line/) is the command
line people copy: `init`, `eval`, `view`, `share`, and a `redteam` group
(`init`, `generate`, `run`, `plugins`, `report`). Its
[plugin catalogue](https://www.promptfoo.dev/docs/red-team/plugins/) is a set of
generative attackers, on the order of 150 plugins across brand, compliance,
security, and trust-and-safety, not a reviewed case corpus. A 4 November 2026
comparison of the three scanners reported Promptfoo 0.125.1 (MIT, and described
there as part of OpenAI), NVIDIA Garak 0.17.1, and Microsoft PyRIT 1.1.0.

[Garak](https://github.com/NVIDIA/garak) is a probe scanner, including an
agent-breaker probe aimed at tool-using applications. [PyRIT](https://microsoft.github.io/PyRIT/latest/)
is a campaign toolkit: `pyrit_scan`, the CoPyRIT web UI, and multi-turn attacks
such as Crescendo and TAP. Their cases are generated attacks. A Circumstances
case is a versioned obligation with a polarity: positive, negative, attack,
recovery, or normal.

### Watch production and score datasets

LangSmith's CLI manages traces, datasets, evaluators, and experiments.
Braintrust's `bt` CLI runs evals and can query logs with SQL. DeepEval is a
pytest-style metric library; `deepeval view` opens the Confident AI cloud, and
`deepeval inspect` is a terminal trace. Langfuse, Arize Phoenix, and MLflow
remain trace and experiment warehouses. In these products the hosted dashboard
is the product, and the tests are code or rows in that vendor's account.

### Circumstances

A portable situation: rules, cases, fixtures, actions, and evidence
requirements, graded on a sealed trajectory of a named subject. The subject is
the whole system under test (model, harness, tools, memory, environment), not a
bare model name. Packs are untrusted data.

## Feature matrix

Read on 11 November 2026 from the docs linked above.

| | Circumstances | Inspect | Harbor | Promptfoo | Garak / PyRIT | LangSmith, Braintrust, DeepEval |
|---|---|---|---|---|---|---|
| Unit | named subject plugin for a whole system | model, built-in agent, or external CLI | agent in a container | provider or target | model or HTTP/browser target | traced application |
| Test form | pack format v4 YAML; no executable code | Python tasks | container tasks and datasets | YAML plus generative plugins | probe modules and scenarios | datasets and code scorers |
| Multi-step | authored trajectories, repetitions, seeds | agent and tool loops | task episodes | strategies and multi-turn plugins | PyRIT campaigns; Garak probes | traces and experiments |
| Evidence | sealed bundle, then `run score` | `inspect score` on logs | job logs and hub upload | eval cache and shared URL | scanner memory and export | hosted experiment |
| Smoke vs meaning | smoke is a labelled tier; judges may return `unknown` | task scorers | task reward | assertion or grader result | detector hit | metric score |
| Pack / dataset CLI | `pack init`, `add`, `list`, `lint` | `list`, task imports | `datasets list`, `run -d` | `init`, `redteam plugins` | probes shipped in the install | dataset upload / list |
| Run CLI | `run`, `run list`, `show`, `compare`, `score` | `eval`, `eval-retry`, `log` | `run`, `view`, `upload` | `eval`, `view` | `garak`, `pyrit_scan` | `experiment list`, `bt eval` |
| Local viewer | `circumstances view` over sealed bundles | `inspect view` | `harbor view jobs` | `promptfoo view` | CoPyRIT for PyRIT | `deepeval inspect`; `view` opens the cloud |
| Hosted dashboard | none; `view` is local | not required | Harbor Hub | Promptfoo cloud / share | not the product | the product |
| Third-party install | pinned index, `git+https` or HTTPS archive; untrusted refs need a digest | tasks in the library, plus Harbor datasets | `org/name@version` from the hub | plugins in the package | probes in the package | upload into the vendor account |

## Advantages worth keeping

These are the reasons not to switch frameworks and not to clone one.

- **Packs cannot execute.** Inspect tasks, Harbor tasks, Promptfoo plugins,
  DeepEval metrics, and PyRIT scenarios are code. A third-party Circumstances
  pack receives no process environment, no undeclared network, and no evaluator
  code. That is what makes "download a pack" safe enough to ship. See
  [Security](security.md).
- **The subject is the system, not the model.** A comparison is valid only when
  the run locks agree on pack digest, fixture digests, subject id and version,
  evaluator versions, and model identities. See
  [Evaluation methodology](methodology.md). Harbor and Inspect
  disclose a harness and then score task success. Circumstances is for rules
  whose violation is a path through memory, tools, and policy.
- **Smoke is not a safety claim.** Exact strings and regular expressions stay
  in the smoke tier. A semantic judge must be able to return `unknown`.
- **The bundle outlives the session.** `run score` regrades stored trajectories
  and writes a new grade record beside the bundle. It does not call the subject
  and it does not rewrite sealed trial events. Inspect's `inspect score` is the
  command this copies.
- **No hosted service in the framework.** A product's own dashboard is the
  right place for its settings and hosted runs. Building one into Circumstances
  would drag accounts, OAuth, and a catalog service into the open-source
  contract.

## Will not match

On purpose, and not as a later surprise inside this cut:

- Inspect's benchmark catalogue and sandbox fleet.
- Harbor Hub as a hosted marketplace, and `harbor upload`.
- Promptfoo's attack-plugin generator, and Garak or PyRIT campaign search as
  open-ended attack libraries. The planned
  [adaptive campaigns](../project/rfcs/0001-adaptive-campaigns.md) are
  narrower: one declared rule, one declared situation, an operator budget, and
  sealed episodes.
- A LangSmith-style trace warehouse, seats, or production monitor.
- Heatmaps, SARIF, OpenTelemetry export, and shareable cloud URLs.

Threat-database adapters stay a later candidate import. Nothing in an adapter
writes into a pack automatically. Imported cases would be candidates a pack
owner promotes.

## What we match, in this order

### 1. Pack workflow

```bash
circumstances pack init <dir>
circumstances pack add rule <pack> <rule-id>
circumstances pack add case <pack> <rule-id> <case-id>
circumstances pack lint <pack>          # lint-pack remains
circumstances pack add <ref-or-name>
circumstances pack list
```

`pack init` writes a format-v4 pack: one rule, one positive case, one negative
case, fictional fixture notes, and SPDX fields. The template is data the
current linter accepts. It tracks format version 4; when the format changes,
the template changes with it.

`pack add` resolves a local directory, an `https://` archive, a
`git+https://…#ref=…&path=…` checkout, a name in the checked-in index, or a
name in a project `circumstances.yaml`. It prints the digest and revision. It
does not execute the pack. Download limits, public-host checks, and digest
pins stay in the existing resolver.

The checked-in index names the seven first-party packs at one git revision and
the digest of each pack directory. There is no phone-home registry. A project
file adds further sources:

```yaml
sources:
  - name: partner/example
    ref: git+https://example.com/example.git#ref=v1.0.0
    trust: untrusted
    digest: "<sha256>"
```

A raw remote ref is `untrusted`. Untrusted refs require `--digest`. First-party
index entries are `verified` because the digest is already pinned.

`pack list` shows the download cache (`~/.cache/circumstances/packs`) and the
known index and project names.

### 2. Run workflow

```bash
circumstances run <pack> --subject <id>
circumstances run list
circumstances run show <id>
circumstances run compare <a> <b>
circumstances run score <bundle>
circumstances subjects
```

`run list`, `show`, and `compare` read sealed bundles under `results/`.
`compare` reports per-case `fixed`, `regressed`, `same`, `only_a`, and
`only_b`, using pass^k (every trial passed) as the case verdict, and it prints
pass@k for the trials that were actually run. It exits with an error, and does
not print a case table, when the run locks disagree.

`run score` grades the stored trajectories with the installed evaluators and
writes `results/<id>.regrades/<stamp>.json`. The sealed directory is unchanged.
`verify-bundle` still applies to that directory.

`subjects` lists plugins from the `circumstances.subjects` entry-point group.
`run --subject` uses that group instead of a hardcoded pair. `--model` is
passed only to a plugin that accepts it.

### 3. Local viewer

```bash
circumstances view [results/]
```

`view` serves a read-only page on `127.0.0.1`. It lists runs, shows pass/fail
by rule, trial transcripts, grader reasoning, pass@k, and the same compare
verdict as the command line. It has no login, no pack editor, and no catalog
service. It reads `run.json` and the trial records in the bundle.

## Limits of this cut

- The template will look finished before pack format v4 is stable. It is
  generated to satisfy the current linter, and it says which format version it
  tracks.
- A named index is a supply chain. First-party entries are pinned by revision
  and digest. Every other remote source stays untrusted until the operator
  passes a digest. Circumstances does not phone home for a pack list.
- The local viewer will drift if it grows its own copy of the grading logic. It
  reads the public bundle fields only.
- A regrade can be mistaken for a new experiment. The new file names the
  evaluator versions and the seal of the bundle it graded. The original trial
  events stay in the sealed directory.
