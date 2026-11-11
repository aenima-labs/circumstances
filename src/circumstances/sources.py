"""First-party pack index, project sources, and the download cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from circumstances.errors import PackError
from circumstances.fetch import ResolverPolicy
from circumstances.models import TrustLevel

SourceKind = Literal["index", "project", "direct"]


@dataclass(frozen=True)
class PackSource:
    """A named pack an operator can add without typing a URL."""

    name: str
    ref: str
    trust: TrustLevel
    digest: str | None
    revision: str | None
    kind: SourceKind


def index_path() -> Path:
    return Path(__file__).with_name("pack_index.yaml")


def load_index() -> dict[str, PackSource]:
    """Load the checked-in first-party index. Entries are digest-pinned."""
    document = _mapping(index_path())
    revision = _text(document.get("revision"), "revision")
    repository = _text(document.get("repository"), "repository")
    packs = document.get("packs")
    if not isinstance(packs, list) or not packs:
        raise PackError("pack index contains no packs")
    loaded: dict[str, PackSource] = {}
    for entry in packs:
        if not isinstance(entry, dict):
            raise PackError("pack index entry must be a mapping")
        name = _text(entry.get("name"), "name")
        path = _text(entry.get("path"), "path")
        digest = _digest(entry.get("digest"))
        if name in loaded:
            raise PackError(f"duplicate pack index name: {name}")
        loaded[name] = PackSource(
            name=name,
            ref=f"git+{repository}#ref={revision}&path={path}",
            trust="verified",
            digest=digest,
            revision=revision,
            kind="index",
        )
    return loaded


def load_project_sources(start: Path | None = None) -> dict[str, PackSource]:
    """Load ``circumstances.yaml`` from the working directory or a parent."""
    found = _project_file(start or Path.cwd())
    if found is None:
        return {}
    document = _mapping(found)
    raw = document.get("sources", [])
    if raw is None:
        return {}
    if not isinstance(raw, list):
        raise PackError(f"{found} sources must be a list")
    loaded: dict[str, PackSource] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackError(f"{found} source entries must be mappings")
        name = _text(entry.get("name"), "name")
        ref = _text(entry.get("ref"), "ref")
        trust = _trust(entry.get("trust", "untrusted"))
        digest = entry.get("digest")
        revision = entry.get("revision")
        if digest is not None:
            digest = _digest(digest)
        if revision is not None and not isinstance(revision, str):
            raise PackError("source revision must be a string")
        if trust == "untrusted" and not digest:
            raise PackError(f"untrusted source {name} requires a digest")
        if name in loaded:
            raise PackError(f"duplicate project source: {name}")
        loaded[name] = PackSource(
            name=name,
            ref=_resolve_project_ref(found.parent, ref),
            trust=trust,
            digest=digest,
            revision=revision,
            kind="project",
        )
    return loaded


def cached_packs(policy: ResolverPolicy | None = None) -> list[dict[str, str]]:
    """Read pack metadata already stored in the download cache."""
    root = (policy or ResolverPolicy()).cache_root
    if not root.is_dir():
        return []
    found: list[dict[str, str]] = []
    for metadata in sorted(root.glob("*/resolved.json")):
        try:
            saved = json.loads(metadata.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(saved, dict):
            continue
        source = saved.get("source")
        digest = saved.get("digest")
        if not isinstance(source, str) or not isinstance(digest, str):
            continue
        revision = saved.get("revision")
        found.append(
            {
                "source": source,
                "digest": digest,
                "revision": revision if isinstance(revision, str) else "",
                "path": str(metadata.parent / "pack"),
            }
        )
    return found


def _project_file(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / "circumstances.yaml"
        if candidate.is_file():
            return candidate
        if (current / ".git").exists() or current.parent == current:
            return None
        current = current.parent


def _resolve_project_ref(root: Path, ref: str) -> str:
    if ref.startswith(("git+", "https://", "http://")):
        return ref
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return str(path.resolve())


def _mapping(path: Path) -> dict[str, object]:
    try:
        loaded = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise PackError(f"could not read {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise PackError(f"{path} must contain a YAML mapping")
    return loaded


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackError(f"{field} must be a non-empty string")
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise PackError("pack digest must be a SHA-256 hex string")
    if any(character not in "0123456789abcdef" for character in value):
        raise PackError("pack digest must be a SHA-256 hex string")
    return value


def _trust(value: object) -> TrustLevel:
    if value not in {"local", "verified", "untrusted"}:
        raise PackError(f"unsupported trust level: {value!r}")
    return value
