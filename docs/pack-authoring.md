# Pack authoring guide

## Layout

```text
pack.yaml
rules/<rule-id>/rule.yaml
rules/<rule-id>/cases/<case-id>/case.yaml
```

`pack.yaml` carries `format_version: 4`, semver, license, publisher,
capabilities, permissions, and review timestamps.

## Quality bar

- One rule, one obligation. Cases name target rules and polarity.
- Prefer positive, negative, attack, recovery, and normal controls where they
  make sense.
- Outcome and semantic evaluators need known-pass and known-fail self-tests.
- Keep smoke/regex checks labelled as smoke. They never certify semantics.
- Fixtures must be fictional for public packs and declare privacy.

## Capabilities and permissions

Declare only the subject capabilities the pack needs. Permissions are deny-by-
default for host resources. Packs cannot read arbitrary files, environment
secrets, or undeclared network destinations.

## Validation

```bash
uv run circumstances pack init path/to/pack
uv run circumstances pack lint path/to/pack
uv run circumstances run path/to/pack --subject toy
```

`pack init` writes a format-v4 skeleton. `pack add rule` and `pack add case`
add further rules and cases. `lint-pack` remains an alias of `pack lint`.
