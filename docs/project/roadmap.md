# Roadmap

Circumstances is pre-1.0. This page says what works today, what is missing,
and the order we intend to build the rest in. It is a plan, not a promise:
items move when users tell us something else matters more. Open an issue to
argue for a change.

Items marked **help wanted** are good places to start. Each one is
self-contained, and a maintainer will help you scope it. See
[Contributing](../../CONTRIBUTING.md) for how to pick one up.

## Where it stands

**Works today**

- Pack format v4: rules, cases, fixtures, typed actions, and evidence
  requirements, all as data.
- Two subjects: the deterministic `toy` subject and an `openai-compatible`
  chat endpoint, plus entry points for your own subject plugins.
- Evaluators for the automated tiers: `smoke.text`, `smoke.event`,
  `outcome.state`, `outcome.tool`, and the `semantic.rubric` contract with an
  `unknown` result.
- Repeated trials with pass@k and pass^k, sealed run bundles, run locks,
  `compare`, `score` (regrade without calling the subject), and a local
  read-only viewer.
- A pack workflow (`pack init`, `add`, `lint`, `list`), a digest-pinned
  first-party pack index, and seven public packs.

**Known gaps**

- **No judge from the command line.** `semantic.rubric` grades `unknown` unless
  a program passes in a judge, so command-line runs have no semantic evidence.
- **Not on PyPI.** The `v0.1.0` release predates the pack workflow and the run
  commands.
- **`generated_message` is not generated.** The built-in subjects send its
  `prompt` as a literal message. No user simulator plays the persona yet.
- **`wait` is skipped.** The built-in subjects record a skipped wait instead of
  advancing time.
- **Only chat endpoints.** No built-in subject drives a tool-using agent
  framework, a command-line agent, or an MCP environment.
- **No CI integration.** There is no GitHub Action, no JUnit output, and no
  pass/fail threshold to gate a merge.
- **Cost is not tracked per trial.** Judge cost is recorded on grades, but a
  run does not total tokens, dollars, or latency for the subject.
- **Judges are uncalibrated by default.** `semantic.rubric` records a
  calibration version, but Circumstances ships no tooling to measure judge
  agreement against human labels.
- **Human review is manual.** Tier 7 has no workflow in the viewer.

## Now: make it easy to adopt

Target: the next minor release.

| Item | What done looks like | |
|---|---|---|
| PyPI release | `pip install circumstances` installs the current command line; release notes list what changed since `v0.1.0` | |
| CI integration | A GitHub Action that runs packs, writes a JUnit report and a Markdown summary, and fails on a pass^k threshold | **help wanted** |
| Native subjects | `anthropic` and `openai-responses` subjects with tool calls mapped to `tool_call` and `tool_result` events | **help wanted** |
| Command-line judge | A judge model chosen with `--judge` (any OpenAI-compatible or native endpoint) grades `semantic.rubric`, and its identity goes into the run lock | |
| User simulator | `generated_message` drives a configurable simulator model that plays the persona, recorded in the trajectory and the run lock | |
| Cost and latency | Every trial records subject, judge, and simulator tokens, dollars, and wall time; `run show` and `compare` report them | |
| More public cases | Each public pack reaches at least three cases per rule, including a negative control | **help wanted** |

## Next: adaptive campaigns

Target: the release after.

Static packs answer "does the agent hold this rule in these situations?". They
cannot answer "how hard is it to make the agent break this rule?". An
**adaptive campaign** does: an attacker model, configured by the operator,
keeps inventing new multi-turn situations against one rule until the agent
breaks or a budget in dollars, tokens, or episodes runs out.

The full design is in
[RFC 1: Adaptive campaigns](rfcs/0001-adaptive-campaigns.md). In short:

- A pack declares a **campaign**: the rule under test, the situation and
  fixtures, the tactics the attacker may use, and what counts as a break. It
  stays data, with no code.
- The operator chooses the attacker and judge models and the **budget** at run
  time. A pack can never spend money or choose a model.
- Every episode is a normal trajectory, graded by normal evaluators, and sealed
  into the bundle. Nothing is lost when the live session ends.
- The headline result is **cost to break**: dollars, tokens, and episodes spent
  before the first confirmed break, and the break rate at a fixed budget. Two
  agents compared at the same budget answer "which one is harder to talk out of
  its rules?"
- A confirmed break can be **promoted** into an ordinary static case with
  `circumstances campaign promote`, so every failure the attacker finds becomes
  a regression test.

Milestones:

1. Budget accounting and price tables (builds on the command-line judge and on
   cost and latency above).
2. The campaign format in pack format v4.x, with lint support.
3. A single-strategy attacker: propose, run, grade, refine.
4. Search across tactics with novelty, so the budget is not spent on
   rephrasings of one attack.
5. `campaign promote`, and cost-to-break in `compare` and the viewer.

## Later: wider subjects and stronger evidence

| Item | Why |
|---|---|
| Framework subjects (LangGraph, OpenAI Agents SDK, and others) as separate packages | Test the whole agent where it already runs. **help wanted** |
| Command-line and container agents | Run coding and computer-use agents in an isolated sandbox with recorded file and process events |
| MCP tool environments | Fixtures that stand up mock MCP servers with state that `outcome.state` can check |
| Judge calibration | Label a sample, measure judge agreement, and record it as the calibration version |
| Human review in the viewer | Assign trials, record verdicts as tier-7 grades, and seal them beside the bundle |
| Signed packs and a community index | Sigstore signatures, and an index anyone can propose packs to with the same publication checks |
| Pack format v5 and 1.0 | Freeze the public contracts once adapters and campaigns have been used in practice |

## Not planned

These stay out on purpose. See the
[evaluation landscape](../background/landscape.md) for the reasoning.

- A hosted dashboard, accounts, or a trace warehouse.
- A benchmark leaderboard or a catalogue of model scores.
- Executable code inside packs.
- An open-ended jailbreak generator. Campaigns attack one declared rule in one
  declared situation, within a budget the operator sets.
