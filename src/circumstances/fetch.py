"""Safe, reproducible pack resolution."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import shutil
import socket
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlparse

from circumstances.errors import PackError
from circumstances.models import TrustLevel


@dataclass(frozen=True)
class ResolverPolicy:
    cache_root: Path = field(
        default_factory=lambda: Path.home() / ".cache" / "circumstances" / "packs"
    )
    max_download_bytes: int = 100 * 1024 * 1024
    max_unpacked_bytes: int = 250 * 1024 * 1024
    max_files: int = 5_000
    max_redirects: int = 3
    allow_private_hosts: bool = False


@dataclass(frozen=True)
class ResolvedPack:
    path: Path
    source: str
    digest: str
    revision: str | None
    trust: TrustLevel


def resolve_pack(
    ref: str,
    *,
    trust: TrustLevel = "local",
    expected_digest: str | None = None,
    refresh: bool = False,
    headers: dict[str, str] | None = None,
    policy: ResolverPolicy | None = None,
) -> ResolvedPack:
    policy = policy or ResolverPolicy()
    if ref.startswith("git+"):
        if trust == "untrusted" and not expected_digest:
            raise PackError("untrusted git packs require an expected SHA-256 digest")
        return _resolve_git(
            ref[4:],
            trust=trust,
            expected_digest=expected_digest,
            refresh=refresh,
            policy=policy,
        )
    parsed = urlparse(ref)
    if parsed.scheme in {"http", "https"}:
        if parsed.scheme != "https":
            raise PackError("remote packs require HTTPS")
        if trust == "untrusted" and not expected_digest:
            raise PackError("untrusted remote packs require an expected SHA-256 digest")
        return _resolve_archive(
            ref,
            trust=trust,
            expected_digest=expected_digest,
            refresh=refresh,
            headers=headers or {},
            policy=policy,
        )
    path = Path(ref).expanduser().resolve()
    if not path.is_dir() or not (path / "pack.yaml").is_file():
        raise PackError(f"local pack not found: {ref}")
    digest = hash_directory(path)
    _check_digest(digest, expected_digest)
    return ResolvedPack(path, str(path), digest, None, trust)


def hash_directory(path: Path) -> str:
    root = path.resolve()
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*")):
        relative = item.relative_to(root)
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if item.is_symlink():
            raise PackError(f"pack contains a symbolic link: {relative}")
        if item.is_file():
            digest.update(relative.as_posix().encode())
            digest.update(b"\0")
            digest.update(item.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def confined_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise PackError(f"pack path escapes root: {relative}")
    return candidate


def _resolve_archive(
    url: str,
    *,
    trust: TrustLevel,
    expected_digest: str | None,
    refresh: bool,
    headers: dict[str, str],
    policy: ResolverPolicy,
) -> ResolvedPack:
    cache_dir = policy.cache_root / hashlib.sha256(url.encode()).hexdigest()
    metadata = cache_dir / "resolved.json"
    if not refresh and metadata.is_file():
        pack_dir, saved = _cached_pack(cache_dir, metadata)
        _check_digest(saved["digest"], expected_digest)
        return ResolvedPack(pack_dir, url, saved["digest"], None, trust)

    _remove(cache_dir)
    policy.cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=policy.cache_root) as temporary:
        staging = Path(temporary)
        blob = _download(url, headers=headers, policy=policy)
        archive = staging / "pack.archive"
        archive.write_bytes(blob)
        unpacked = staging / "unpacked"
        unpacked.mkdir()
        if zipfile.is_zipfile(archive):
            _extract_zip(archive, unpacked, policy)
        else:
            _extract_tar(archive, unpacked, policy)
        pack_root = _find_pack_root(unpacked)
        digest = hash_directory(pack_root)
        _check_digest(digest, expected_digest)
        cache_dir.mkdir()
        shutil.copytree(pack_root, cache_dir / "pack")
        metadata.write_text(
            json.dumps({"source": url, "digest": digest}, sort_keys=True) + "\n"
        )
    return ResolvedPack(cache_dir / "pack", url, digest, None, trust)


def _resolve_git(
    url: str,
    *,
    trust: TrustLevel,
    expected_digest: str | None,
    refresh: bool,
    policy: ResolverPolicy,
) -> ResolvedPack:
    repository, separator, requested_ref = url.partition("#ref=")
    ref = requested_ref if separator else "HEAD"
    parsed = urlparse(repository)
    if parsed.scheme != "https":
        raise PackError("git pack sources require git+https")
    _validate_public_host(parsed.hostname or "", policy)
    source = f"git+{repository}#ref={ref}"
    cache_dir = policy.cache_root / hashlib.sha256(source.encode()).hexdigest()
    metadata = cache_dir / "resolved.json"
    if not refresh and metadata.is_file():
        pack_dir, saved = _cached_pack(cache_dir, metadata)
        _check_digest(saved["digest"], expected_digest)
        return ResolvedPack(
            pack_dir,
            source,
            saved["digest"],
            saved.get("revision"),
            trust,
        )

    _remove(cache_dir)
    policy.cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=policy.cache_root) as temporary:
        checkout = Path(temporary) / "checkout"
        command = ["git", "clone", "--depth", "1"]
        if ref != "HEAD":
            command.extend(["--branch", ref])
        command.extend(["--", repository, str(checkout)])
        subprocess.run(command, check=True, capture_output=True, text=True)
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        pack_root = _find_pack_root(checkout)
        digest = hash_directory(pack_root)
        _check_digest(digest, expected_digest)
        cache_dir.mkdir()
        shutil.copytree(pack_root, cache_dir / "pack", ignore=shutil.ignore_patterns(".git"))
        metadata.write_text(
            json.dumps(
                {"source": source, "digest": digest, "revision": revision},
                sort_keys=True,
            )
            + "\n"
        )
    return ResolvedPack(cache_dir / "pack", source, digest, revision, trust)


def _download(url: str, *, headers: dict[str, str], policy: ResolverPolicy) -> bytes:
    try:
        import httpx
    except ImportError as exc:
        raise PackError("install circumstances[http] to resolve remote packs") from exc
    current = url
    with httpx.Client(timeout=60, follow_redirects=False) as client:
        for redirect in range(policy.max_redirects + 1):
            parsed = urlparse(current)
            _validate_public_host(parsed.hostname or "", policy)
            response = client.get(current, headers=headers)
            if response.is_redirect:
                if redirect == policy.max_redirects:
                    raise PackError("remote pack exceeded redirect limit")
                location = response.headers.get("location")
                if not location:
                    raise PackError("remote pack redirect has no location")
                current = urljoin(current, location)
                if urlparse(current).scheme != "https":
                    raise PackError("remote pack redirect left HTTPS")
                continue
            response.raise_for_status()
            if len(response.content) > policy.max_download_bytes:
                raise PackError("remote pack exceeds maximum download size")
            return bytes(response.content)
    raise PackError("remote pack download failed")


def _extract_zip(archive: Path, destination: Path, policy: ResolverPolicy) -> None:
    with zipfile.ZipFile(archive) as handle:
        entries = handle.infolist()
        if len(entries) > policy.max_files:
            raise PackError("archive contains too many files")
        total = sum(entry.file_size for entry in entries)
        if total > policy.max_unpacked_bytes:
            raise PackError("archive exceeds maximum unpacked size")
        for entry in entries:
            target = _archive_target(destination, entry.filename)
            mode = entry.external_attr >> 16
            if mode & 0o170000 == 0o120000:
                raise PackError(f"archive contains symbolic link: {entry.filename}")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with handle.open(entry) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def _extract_tar(archive: Path, destination: Path, policy: ResolverPolicy) -> None:
    try:
        with tarfile.open(archive) as handle:
            _extract_tar_members(handle, destination, policy)
    except tarfile.TarError as exc:
        raise PackError("remote pack is not a supported zip or tar archive") from exc


def _extract_tar_members(
    handle: tarfile.TarFile, destination: Path, policy: ResolverPolicy
) -> None:
    entries = handle.getmembers()
    if len(entries) > policy.max_files:
        raise PackError("archive contains too many files")
    total = sum(entry.size for entry in entries if entry.isfile())
    if total > policy.max_unpacked_bytes:
        raise PackError("archive exceeds maximum unpacked size")
    for entry in entries:
        target = _archive_target(destination, entry.name)
        if entry.issym() or entry.islnk() or entry.isdev():
            raise PackError(f"archive contains unsupported special file: {entry.name}")
        if entry.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif entry.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(entry)
            if source is None:
                raise PackError(f"could not read archive member: {entry.name}")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def _archive_target(destination: Path, name: str) -> Path:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or "\\" in name:
        raise PackError(f"archive path escapes destination: {name}")
    target = (destination / Path(*pure.parts)).resolve()
    if not target.is_relative_to(destination.resolve()):
        raise PackError(f"archive path escapes destination: {name}")
    return target


def _find_pack_root(root: Path) -> Path:
    direct = root / "pack.yaml"
    if direct.is_file():
        return root
    candidates = sorted(path.parent for path in root.rglob("pack.yaml"))
    candidates = [
        path for path in candidates if ".git" not in path.relative_to(root).parts
    ]
    if len(candidates) != 1:
        raise PackError(f"archive must contain exactly one pack, found {len(candidates)}")
    return candidates[0]


def _cached_pack(cache_dir: Path, metadata: Path) -> tuple[Path, dict[str, str]]:
    try:
        saved = json.loads(metadata.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"invalid pack cache metadata: {metadata}") from exc
    pack_dir = cache_dir / "pack"
    if not pack_dir.is_dir():
        raise PackError(f"cached pack is incomplete: {cache_dir}")
    actual = hash_directory(pack_dir)
    if actual != saved.get("digest"):
        raise PackError(f"cached pack digest changed: {cache_dir}")
    return pack_dir, saved


def _check_digest(actual: str, expected: str | None) -> None:
    if expected and actual != expected:
        raise PackError(f"pack digest mismatch: expected {expected}, got {actual}")


def _validate_public_host(host: str, policy: ResolverPolicy) -> None:
    if not host:
        raise PackError("remote pack URL has no host")
    if policy.allow_private_hosts:
        return
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443)}
    except OSError as exc:
        raise PackError(f"could not resolve remote pack host {host!r}") from exc
    for address in addresses:
        parsed = ipaddress.ip_address(address)
        if not parsed.is_global:
            raise PackError(f"remote pack host resolves to non-public address: {address}")


def _remove(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

