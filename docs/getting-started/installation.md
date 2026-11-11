# Installation

Circumstances is a Python package with one command, `circumstances`. It needs
Python 3.12 or newer. CI tests it on Linux with Python 3.12, 3.13, and 3.14.

## Install the command line

Circumstances is not on PyPI yet. Install it from GitHub with
[uv](https://docs.astral.sh/uv/) or pip.

```bash
uv tool install "circumstances[http] @ git+https://github.com/aenima-labs/circumstances"
```

```bash
pip install "circumstances[http] @ git+https://github.com/aenima-labs/circumstances"
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

## Install a tagged release

Each GitHub release attaches a wheel, an sdist, `SHA256SUMS`, an SPDX stub, and
the JSON Schemas. To pin a release:

```bash
uv tool install "circumstances[http] @ https://github.com/aenima-labs/circumstances/releases/download/v0.1.0/circumstances-0.1.0-py3-none-any.whl"
```

Release `v0.1.0` predates the pack workflow (`pack init`, `pack add`,
`pack list`), the run inspections (`run list`, `show`, `compare`, `score`), and
`circumstances view`. Install from the default branch until the next release if
you need them.

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

## Next

Run your first pack in the [Quickstart](quickstart.md).
