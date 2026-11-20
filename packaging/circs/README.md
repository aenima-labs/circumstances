# circs

`circs` is the short name of
[Circumstances](https://circumstances.aenimalabs.com/), an open-source
framework for testing whole agent systems inside versioned, multi-step
situations.

This package holds no code. It installs
[`circumstances`](https://pypi.org/project/circumstances/) at the same version,
which gives you two names for one command line: `circumstances` and `circs`.

```bash
uv tool install "circumstances[http]"   # recommended
pip install "circs[http]"               # same thing, shorter
circs --version
```

Documentation, packs, and source:
[github.com/aenima-labs/circumstances](https://github.com/aenima-labs/circumstances).
