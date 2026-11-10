from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from circumstances.adapters.toy import ToySubjectPlugin
from circumstances.artifacts import FileArtifactStore, verify_bundle
from circumstances.evaluators import builtin_evaluators
from circumstances.fetch import hash_directory, resolve_pack
from circumstances.models import EvaluatorSpec, RunPlan
from circumstances.pack import load_pack
from circumstances.registry import EvaluatorRegistry
from circumstances.runner import run_loaded_pack


def make_pack(root: Path) -> Path:
    now = datetime.now(UTC).isoformat()
    write_yaml(
        root / "pack.yaml",
        {
            "format_version": 4,
            "id": "test/neutral",
            "version": "1.0.0",
            "title": "Neutral",
            "description": "A neutral test pack.",
            "license": "Apache-2.0",
            "publisher": {"name": "Tests"},
            "created_at": now,
            "reviewed_at": now,
            "required_capabilities": ["message.text"],
            "evaluators": [],
        },
    )
    write_yaml(
        root / "rules" / "echo" / "rule.yaml",
        {
            "id": "echo",
            "title": "Echo",
            "description": "The subject responds.",
            "evaluators": [],
        },
    )
    write_yaml(
        root / "rules" / "echo" / "cases" / "basic" / "case.yaml",
        {
            "id": "echo/basic",
            "title": "Basic",
            "targets": ["echo"],
            "polarity": "normal",
            "fixture": {"type": "builtin.empty"},
            "actions": [{"kind": "message", "content": "hello"}],
            "evaluators": [
                {
                    "id": "reply",
                    "type": "smoke.text",
                    "tier": "smoke",
                    "config": {"contains_all": ["Observed: hello"]},
                }
            ],
        },
    )
    return root


async def test_neutral_pack_runs_without_product_code(tmp_path: Path) -> None:
    pack_root = make_pack(tmp_path / "pack")
    resolved = resolve_pack(str(pack_root))
    pack = load_pack(resolved.path, source=resolved.source, digest=resolved.digest)
    evaluators = EvaluatorRegistry()
    for evaluator in builtin_evaluators():
        evaluators.register(evaluator)

    summary = await run_loaded_pack(
        pack,
        RunPlan(pack_ref=str(pack_root), subject="toy"),
        subject=ToySubjectPlugin(),
        evaluators=evaluators,
        run_id="neutral-run",
    )

    assert summary.passed
    assert summary.results[0].trajectory.subject.id == "toy"
    files = {
        path.relative_to(pack.root).as_posix(): path.read_bytes()
        for path in pack.root.rglob("*")
        if path.is_file()
    }
    bundle = FileArtifactStore(tmp_path / "results").persist(summary, pack_files=files)
    assert verify_bundle(bundle) == []


def test_smoke_name_cannot_masquerade_as_semantic() -> None:
    with pytest.raises(ValueError, match="must declare tier: smoke"):
        EvaluatorSpec(
            id="bad",
            type="smoke.text",
            tier="semantic",
        )


def test_pack_digest_changes_with_material_file(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack")
    before = hash_directory(pack)
    case = pack / "rules" / "echo" / "cases" / "basic" / "case.yaml"
    case.write_text(case.read_text() + "\n")
    assert hash_directory(pack) != before


def write_yaml(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False))

