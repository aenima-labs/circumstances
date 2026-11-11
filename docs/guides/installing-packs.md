# Share and install packs

A pack is a directory. Sharing one means publishing that directory somewhere
others can fetch it; installing one means resolving a reference to an exact,
digest-checked copy in a local cache. Nothing in a pack is ever executed.

## Ways to refer to a pack

| Reference | Example |
|---|---|
| Local directory | `packs/grounding`, `~/work/inbox` |
| HTTPS archive (`.zip`, `.tar.gz`) | `https://example.com/packs/inbox-0.3.0.tar.gz` |
| Git repository at a ref | `git+https://github.com/acme/packs.git#ref=v0.3.0` |
| Git repository, one folder | `git+https://github.com/acme/packs.git#ref=v0.3.0&path=packs/inbox` |
| Name in the first-party index | `aenima/grounding` |
| Name in your project's `circumstances.yaml` | `partner/example` |

Every command that takes a pack (`run`, `pack lint`, `pack add`) accepts the
first four forms. Names work with `pack add`.

## Install from the first-party index

The package ships an index of the seven Aenima Labs packs, each pinned to one
git revision and the SHA-256 of its directory.

```bash
circumstances pack list
circumstances pack add aenima/privacy-security
```

```json
{
  "digest": "5ff8c6ed7755b37d012cfdd0e49452d83a22104a1757baa047e1389433a46537",
  "path": "/home/you/.cache/circumstances/packs/…/pack",
  "revision": "8fa1ff808135b2c598828040a0a8b0eb17a8dad0",
  "source": "git+https://github.com/aenima-labs/circumstances.git#ref=8fa1…&path=packs/privacy-security",
  "trust": "verified"
}
```

Index entries are `verified` because their digest is already pinned. There is
no registry service: the index is a file inside the package, and Circumstances
never phones home for a pack list.

## Install from a URL or repository

A raw remote reference is `untrusted` until you say what it must hash to:

```bash
circumstances pack add "git+https://github.com/acme/packs.git#ref=v0.3.0&path=packs/inbox" \
  --digest 3b1f…e9
```

Without `--digest`, the command refuses:

```text
error: untrusted refs require --digest
```

Get the digest from the pack's publisher, from a release note, or by resolving
it once yourself and reviewing the files. The digest covers every material file
in the pack directory and excludes transport metadata such as `.git`.

You can run a remote pack directly too:

```bash
circumstances run "https://example.com/packs/inbox-0.3.0.tar.gz" \
  --subject acme-inbox --trust untrusted --digest 3b1f…e9
```

## Name your sources in `circumstances.yaml`

To give remote packs short names in a project, add `circumstances.yaml` at the
project root:

```yaml
sources:
  - name: acme/inbox
    ref: git+https://github.com/acme/packs.git#ref=v0.3.0&path=packs/inbox
    trust: untrusted
    digest: "3b1f…e9"
  - name: team/local-drafts
    ref: ./evals/drafts
    trust: local
```

Circumstances looks for this file in the working directory and its parents,
stopping at the repository root. Relative `ref` paths are resolved against the
file's directory. An `untrusted` source without a `digest` is rejected when the
file is read.

```bash
circumstances pack add acme/inbox
circumstances pack list
```

If you also pass `--digest` for a named source that already pins one, the two
must match.

## Where packs are cached

Resolved remote packs live in `~/.cache/circumstances/packs/`. `pack list`
shows what is cached and every name it knows from the index and the project
file. Delete the directory to clear the cache.

## What the resolver refuses

Fetching a pack from a stranger is safe because the resolver is strict:

- Remote packs need HTTPS. `http://` is refused.
- Hosts that resolve to private, loopback, or link-local addresses are refused.
- Downloads are capped at 100 MiB, unpacked content at 250 MiB and 5,000 files,
  with at most 3 redirects.
- Archives may not contain path traversal, links, or special files.
- Git refs resolve to an immutable commit, and that commit is recorded.
- A digest mismatch stops resolution.

Then the loader applies pack rules: no executable code, no access to the
process environment, and paths confined to the pack directory. See
[Security and trust model](../background/security.md).

## Publish a pack

1. Put the pack in a git repository, one directory per pack.
2. Lint it in CI: `circumstances pack lint path/to/pack`.
3. Tag a release.
4. Compute the digest your users should pin:

   ```bash
   circumstances pack add "git+https://github.com/you/packs.git#ref=v1.0.0&path=packs/inbox" \
     --trust verified
   ```

   The printed `digest` is the value to publish alongside the tag.
5. Document the capabilities your pack requires, so users know which subjects
   can run it.

Bump the pack `version` whenever a rule, case, fixture, or evaluator changes.
Results are only comparable across identical pack digests.
