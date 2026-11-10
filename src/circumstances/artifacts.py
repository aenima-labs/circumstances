"""Immutable filesystem run bundles."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from circumstances.models import RunSummary


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class FileArtifactStore:
    """Write a self-contained run bundle and seal it with file digests."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def persist(self, summary: RunSummary, *, pack_files: dict[str, bytes] | None = None) -> Path:
        final_dir = self.root / summary.run_id
        pending = self.root / f".{summary.run_id}.pending"
        if final_dir.exists() or pending.exists():
            raise FileExistsError(f"run bundle already exists: {summary.run_id}")
        pending.mkdir(parents=True)
        try:
            self._write_json(pending / "run.json", summary.model_dump(mode="json"))
            trials_dir = pending / "trials"
            trials_dir.mkdir()
            for result in summary.results:
                self._write_json(
                    trials_dir / f"{_safe(result.trial_id)}.json",
                    result.model_dump(mode="json"),
                )
            if pack_files:
                snapshot = pending / "pack"
                for relative, content in sorted(pack_files.items()):
                    target = (snapshot / relative).resolve()
                    if not target.is_relative_to(snapshot.resolve()):
                        raise ValueError(f"pack snapshot path escapes root: {relative}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
            seal = {
                "schema": "circumstances.run-bundle.v1",
                "run_id": summary.run_id,
                "files": _file_digests(pending),
            }
            self._write_json(pending / "seal.json", seal)
            os.replace(pending, final_dir)
        except BaseException:
            _remove_tree(pending)
            raise
        return final_dir

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_bytes(_canonical(value) + b"\n")


def verify_bundle(path: Path) -> list[str]:
    path = path.resolve()
    seal_path = path / "seal.json"
    seal = json.loads(seal_path.read_text())
    failures: list[str] = []
    expected = seal.get("files", {})
    for relative, digest in expected.items():
        target = (path / relative).resolve()
        if not target.is_relative_to(path) or not target.is_file():
            failures.append(f"missing or unsafe artifact: {relative}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            failures.append(f"digest mismatch: {relative}")
    extra = set(_file_digests(path)) - set(expected) - {"seal.json"}
    failures.extend(f"unsealed artifact: {name}" for name in sorted(extra))
    return failures


def _file_digests(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "seal.json":
            relative = path.relative_to(root).as_posix()
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _safe(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in value
    )


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()

