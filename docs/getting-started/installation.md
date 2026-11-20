# Installation

Circumstances is a Python package with one command line, which installs under
two names: `circumstances` and the short alias `circs`. It needs Python 3.12 or
newer. CI tests it on Linux with Python 3.12, 3.13, and 3.14.

## Install the command line

Install it from [PyPI](https://pypi.org/project/circumstances/) with
[uv](https://docs.astral.sh/uv/) or pip:

```bash
uv tool install "circumstances[http]"
```

```bash
pip install "circumstances[http]"
```

The `http` extra adds `httpx`, which the OpenAI-compatible subject needs. Leave
it out if you only use the deterministic `toy` subject or your own plugins.

Check the install:

```bash
circumstances --version
circumstances subjects
```

`subjects` lists the subject plugins Python can find. A fresh install shows
`toy` and `openai-compatible`.

To try it without installing anything, let uv fetch it for one run:

```bash
uvx circs --version
```

## The short name: `circs`

`circs` runs the same command line as `circumstances`, so every example in
these docs works with either name:

```bash
circs run packs/grounding --subject toy
```

`circs` is also a package on PyPI. It holds no code and installs
`circumstances` at the same version, so `pip install "circs[http]"` and
`pip install "circumstances[http]"` give you the same thing. With
`uv tool install`, install `circumstances` to get both commands on your `PATH`.
`uv tool install circs` adds only `circs`.

The alias covers the commands and the PyPI name. Python code and plugins still
import `circumstances` and register under the `circumstances.subjects` entry
point, and environment variables keep the `CIRCUMSTANCES_` prefix.

## Pin a version

```bash
uv tool install "circumstances[http]==0.2.0"
```

Each [GitHub release](https://github.com/aenima-labs/circumstances/releases)
also attaches the wheels, the sdists, `SHA256SUMS`, an SPDX stub, and the JSON
Schemas. `v0.1.0` predates the PyPI packages, the pack workflow (`pack init`,
`pack add`, `pack list`), the run inspections (`run list`, `show`, `compare`,
`score`), and `circumstances view`.

To run the unreleased default branch:

```bash
uv tool install "circumstances[http] @ git+https://github.com/aenima-labs/circumstances"
```

## Work from a clone

To run the public packs, contribute, or read the code, clone the repository and
let uv create the environment:

```bash
git clone https://github.com/aenima-labs/circumstances.git
cd circumstances
uv sync --extra dev
uv run circumstances --version
```

From a clone, prefix every command with `uv run`.

## Optional extras

| Extra | Adds | Use it for |
|---|---|---|
| `http` | `httpx` | The `openai-compatible` subject |
| `server` | `fastapi`, `uvicorn` | Hosting a provider service |
| `dev` | test, lint, type-check, and build tools | Working on Circumstances itself |

`circs` offers the `http` and `server` extras too.

## Next

Run your first pack in the [Quickstart](quickstart.md).
