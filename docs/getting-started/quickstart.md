# Quickstart

In five minutes you will lint a public pack, run it against a deterministic
subject, look at the evidence, and point the same pack at a real model. Nothing
here needs an API key.

This page assumes a clone of the repository. See
[Installation](installation.md) if you do not have one.

```bash
git clone https://github.com/aenima-labs/circumstances.git
cd circumstances
uv sync --extra dev
```

## 1. Lint a pack

A pack is a folder of YAML. Linting validates every file against pack format v4
and runs each evaluator's self-tests, without touching any agent.

```bash
uv run circumstances pack lint packs/grounding
```

```text
aenima/grounding@1.0.0: 4 cases
```

A warning line means the pack loads but is weaker than it should be, for
example an evaluator without a known-pass and a known-fail self-test. A `FAIL`
line means an evaluator disagreed with its own self-test, and the command exits
with status 1.

## 2. Run it

```bash
uv run circumstances run packs/grounding --subject toy
```

```json
{
  "bundle": "/…/circumstances/results/c025c1ace7c742859d937b080b246892",
  "passed": true,
  "run_id": "c025c1ace7c742859d937b080b246892",
  "trials": 12,
  "trials_passed": 12
}
```

The `toy` subject answers from responses written into each case's fixture, so it
always behaves the same. It exists to prove that the pack, the runner, and the
evaluators work before you spend money on a model.

Twelve trials ran for four cases because each case asks for three trials. The
command exits with status 0 when every trial passed and 1 otherwise, so it can
gate a CI job.

## 3. Look at the evidence

Every run writes a sealed bundle under `results/<run-id>/`. Three ways in:

```bash
uv run circumstances run list
uv run circumstances run show c025c1ace7c742859d937b080b246892   # run id or bundle path
uv run circumstances view                # http://127.0.0.1:8765
```

`run show` prints every case, every trial, the ordered events of each
trajectory, and every grade with the evidence it points at. `view` serves the
same data as a read-only page on your machine.

Check that nothing in the bundle changed since it was written:

```bash
uv run circumstances verify-bundle results/c025c1ace7c742859d937b080b246892
```

## 4. Point it at a model

Any server that speaks the OpenAI chat-completions API works: Ollama, vLLM,
llama.cpp, LM Studio, or a hosted provider.

```bash
export CIRCUMSTANCES_OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export CIRCUMSTANCES_OPENAI_MODEL=llama3.2
uv run circumstances run packs/grounding --subject openai-compatible
```

Some grounding cases need a subject that can call `search` and `cite` tools. A
bare chat endpoint cannot, so those cases fail. That is the point: the pack
describes what the system must do, and a model without tools is not that system.
[Connect your agent](../guides/connecting-your-agent.md) shows how to test the
whole system instead.

## 5. Write your own

```bash
uv run circumstances pack init my-pack --id me/first --title "My first pack"
uv run circumstances pack lint my-pack
uv run circumstances run my-pack --subject toy
```

The template contains one rule, a positive case, and a negative case, each with
an evaluator and its self-tests. Continue with [Write a pack](../guides/writing-a-pack.md).

## What just happened

```text
pack ──▶ rules ──▶ cases ──▶ actions ──▶ subject ──▶ trajectory ──▶ evaluators ──▶ grades
                                                        │
                                                        └──▶ sealed bundle (run.json, trials/, pack/, seal.json)
```

[Core concepts](concepts.md) names each of these parts.
