from pathlib import Path

import pytest

from circumstances.evaluators import builtin_evaluators
from circumstances.pack import lint_pack, load_pack
from circumstances.registry import EvaluatorRegistry
from circumstances.selftest import run_pack_selftests


PACKS_ROOT = Path(__file__).resolve().parents[1] / "packs"


@pytest.mark.asyncio
async def test_all_public_packs_lint_and_selftest() -> None:
    packs = sorted(path for path in PACKS_ROOT.iterdir() if path.is_dir())
    assert packs, "expected public packs"
    registry = EvaluatorRegistry()
    for evaluator in builtin_evaluators():
        registry.register(evaluator)
    for pack_dir in packs:
        pack = load_pack(pack_dir)
        warnings = lint_pack(pack)
        assert isinstance(warnings, list)
        failures = await run_pack_selftests(pack, registry)
        assert not failures, failures
