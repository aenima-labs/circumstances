"""Read, compare, and regrade sealed run bundles."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from circumstances.artifacts import verify_bundle
from circumstances.errors import CircumstancesError, PackError
from circumstances.models import Grade, RunLock, RunSummary, TrialResult
from circumstances.pack import load_pack
from circumstances.registry import EvaluatorRegistry

REGRADES_SCHEMA = "circumstances.regrade.v1"


class IncompatibleRuns(CircumstancesError):
    """Two bundles cannot be compared because their run locks disagree."""

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def pass_at_k(passed: int, total: int, k: int | None = None) -> float:
    """Unbiased pass@k. ``k`` defaults to the number of trials that ran."""
    k = total if k is None else k
    if total < 1 or k < 1 or k > total or not 0 <= passed <= total:
        raise ValueError(f"invalid pass@k inputs: passed={passed} total={total} k={k}")
    if total - passed < k:
        return 1.0
    return 1.0 - math.comb(total - passed, k) / math.comb(total, k)


def pass_hat_k(passed: int, total: int, k: int | None = None) -> float:
    """pass^k: the probability that all ``k`` trials pass."""
    k = total if k is None else k
    if total < 1 or k < 1 or k > total or not 0 <= passed <= total:
        raise ValueError(f"invalid pass^k inputs: passed={passed} total={total} k={k}")
    if passed < k:
        return 0.0
    return math.comb(passed, k) / math.comb(total, k)


def list_bundles(results: Path) -> list[dict[str, object]]:
    """Summaries of sealed bundles directly under ``results``."""
    root = results.expanduser().resolve()
    if not root.is_dir():
        return []
    found: list[dict[str, object]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / "run.json").is_file() or not (entry / "seal.json").is_file():
            continue
        summary = _read_summary(entry)
        found.append(
            {
                "run_id": summary.run_id,
                "pack_id": summary.pack_id,
                "pack_version": summary.pack_version,
                "passed": summary.passed,
                "trials": len(summary.results),
                "started_at": summary.started_at.isoformat(),
                "path": str(entry),
            }
        )
    return found


def show_bundle(bundle: Path) -> dict[str, object]:
    """Verified run detail, including per-case pass@k and transcripts."""
    summary = _verified_summary(bundle)
    return _public_summary(summary)


def compare_bundles(left: Path, right: Path) -> dict[str, object]:
    """Per-case changes. Refuses when the run locks are not compatible."""
    first = _verified_summary(left)
    second = _verified_summary(right)
    reasons = lock_differences(first.lock, second.lock)
    if reasons:
        raise IncompatibleRuns(reasons)
    cases = _case_changes(first, second)
    return {
        "basis": "pass^k",
        "a": _identity(first),
        "b": _identity(second),
        "summary": _change_counts(cases),
        "cases": cases,
    }


async def regrade_bundle(bundle: Path, evaluators: EvaluatorRegistry) -> dict[str, object]:
    """Grade stored trajectories again and write a record beside the bundle.

    The sealed directory, including trial events, is not modified.
    """
    bundle = bundle.expanduser().resolve()
    failures = verify_bundle(bundle)
    if failures:
        raise PackError("bundle failed verification: " + "; ".join(failures))
    summary = _read_summary(bundle)
    pack_dir = bundle / "pack"
    if not (pack_dir / "pack.yaml").is_file():
        raise PackError(f"bundle has no pack snapshot: {bundle}")
    pack = load_pack(
        pack_dir,
        source=summary.lock.pack_source,
        digest=summary.lock.pack_digest,
        revision=summary.lock.pack_revision,
    )
    trials: list[dict[str, object]] = []
    for result in summary.results:
        case = pack.case(result.case_id)
        grades: list[Grade] = []
        for spec in pack.evaluators_for(case):
            grades.append(await evaluators.get(spec.type).evaluate(spec, result.trajectory))
        passed = all(grade.soft or grade.status == "pass" for grade in grades)
        trials.append(
            {
                "trial_id": result.trial_id,
                "case_id": result.case_id,
                "attempt": result.attempt,
                "passed": passed,
                "grades": [grade.model_dump(mode="json") for grade in grades],
            }
        )
    seal = hashlib.sha256((bundle / "seal.json").read_bytes()).hexdigest()
    record: dict[str, object] = {
        "schema": REGRADES_SCHEMA,
        "run_id": summary.run_id,
        "bundle_seal": seal,
        "graded_at": datetime.now(UTC).isoformat(),
        "evaluator_versions": evaluators.versions(),
        "passed": all(trial["passed"] for trial in trials) if trials else False,
        "trials": trials,
    }
    destination_dir = bundle.parent / f"{bundle.name}.regrades"
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    versions = json.dumps(evaluators.versions(), sort_keys=True)
    suffix = hashlib.sha256(versions.encode()).hexdigest()[:12]
    destination = destination_dir / f"{stamp}-{suffix}.json"
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return {
        "regrade": str(destination),
        "bundle_seal": seal,
        "passed": record["passed"],
        "trials": len(trials),
        "evaluator_versions": evaluators.versions(),
    }


def resolve_bundle(token: str, results: Path) -> Path:
    """Accept a bundle directory or a run id under ``results``."""
    candidate = Path(token).expanduser()
    if candidate.is_dir() and (candidate / "run.json").is_file():
        return candidate.resolve()
    bundled = (results.expanduser() / token).resolve()
    if bundled.is_dir() and (bundled / "run.json").is_file():
        return bundled
    raise PackError(f"run bundle not found: {token}")


def lock_differences(left: RunLock, right: RunLock) -> list[str]:
    """Reasons two locks cannot be compared. An empty list means they can."""
    reasons: list[str] = []
    if left.pack_digest != right.pack_digest:
        reasons.append("pack digest differs")
    if left.subject.id != right.subject.id or left.subject.version != right.subject.version:
        reasons.append(
            "subject identity differs: "
            f"{left.subject.id}@{left.subject.version} vs "
            f"{right.subject.id}@{right.subject.version}"
        )
    if list(left.subject.capabilities) != list(right.subject.capabilities):
        reasons.append("subject capabilities differ")
    if left.evaluator_versions != right.evaluator_versions:
        reasons.append("evaluator versions differ")
    if left.models != right.models:
        reasons.append("model identities differ")
    if left.fixture_digests != right.fixture_digests:
        reasons.append("fixture digests differ")
    return reasons


def _verified_summary(bundle: Path) -> RunSummary:
    bundle = bundle.expanduser().resolve()
    failures = verify_bundle(bundle)
    if failures:
        raise PackError("bundle failed verification: " + "; ".join(failures))
    return _read_summary(bundle)


def _read_summary(bundle: Path) -> RunSummary:
    try:
        return RunSummary.model_validate_json((bundle / "run.json").read_text())
    except (OSError, ValueError) as exc:
        raise PackError(f"could not read run bundle {bundle}: {exc}") from exc


def _grouped(summary: RunSummary) -> dict[str, list[TrialResult]]:
    grouped: dict[str, list[TrialResult]] = defaultdict(list)
    for result in summary.results:
        grouped[result.case_id].append(result)
    return grouped


def _public_summary(summary: RunSummary) -> dict[str, object]:
    cases: list[dict[str, object]] = []
    for case_id, results in _grouped(summary).items():
        passed = sum(1 for result in results if result.passed)
        total = len(results)
        cases.append(
            {
                "case_id": case_id,
                "rule_id": case_id.split("/", 1)[0],
                "trials": total,
                "passed_trials": passed,
                "k": total,
                "pass_at_k": pass_at_k(passed, total),
                "pass_hat_k": pass_hat_k(passed, total),
                "passed": passed == total,
                "attempts": [_attempt(result) for result in results],
            }
        )
    return {
        "run_id": summary.run_id,
        "pack_id": summary.pack_id,
        "pack_version": summary.pack_version,
        "passed": summary.passed,
        "started_at": summary.started_at.isoformat(),
        "finished_at": summary.finished_at.isoformat(),
        "lock": summary.lock.model_dump(mode="json"),
        "cases": cases,
    }


def _attempt(result: TrialResult) -> dict[str, object]:
    return {
        "trial_id": result.trial_id,
        "attempt": result.attempt,
        "seed": result.seed,
        "passed": result.passed,
        "events": [event.model_dump(mode="json") for event in result.trajectory.events],
        "grades": [grade.model_dump(mode="json") for grade in result.grades],
    }


def _identity(summary: RunSummary) -> dict[str, object]:
    return {
        "run_id": summary.run_id,
        "pack_id": summary.pack_id,
        "pack_version": summary.pack_version,
        "passed": summary.passed,
    }


def _case_changes(left: RunSummary, right: RunSummary) -> list[dict[str, object]]:
    first = _grouped(left)
    second = _grouped(right)
    changes: list[dict[str, object]] = []
    for case_id in sorted(set(first) | set(second)):
        in_a = case_id in first
        in_b = case_id in second
        passed_a = _all_passed(first.get(case_id, []))
        passed_b = _all_passed(second.get(case_id, []))
        if in_a and not in_b:
            change = "only_a"
        elif in_b and not in_a:
            change = "only_b"
        elif not passed_a and passed_b:
            change = "fixed"
        elif passed_a and not passed_b:
            change = "regressed"
        else:
            change = "same"
        changes.append(
            {
                "case_id": case_id,
                "change": change,
                "passed_a": passed_a if in_a else None,
                "passed_b": passed_b if in_b else None,
                "a": _repetition(first.get(case_id, [])),
                "b": _repetition(second.get(case_id, [])),
            }
        )
    return changes


def _change_counts(cases: list[dict[str, object]]) -> dict[str, int]:
    counts = {"fixed": 0, "regressed": 0, "same": 0, "only_a": 0, "only_b": 0}
    for case in cases:
        change = case["change"]
        if isinstance(change, str) and change in counts:
            counts[change] += 1
    return counts


def _all_passed(results: list[TrialResult]) -> bool:
    return bool(results) and all(result.passed for result in results)


def _repetition(results: list[TrialResult]) -> dict[str, object] | None:
    if not results:
        return None
    passed = sum(1 for result in results if result.passed)
    total = len(results)
    return {
        "trials": total,
        "passed_trials": passed,
        "k": total,
        "pass_at_k": pass_at_k(passed, total),
        "pass_hat_k": pass_hat_k(passed, total),
    }
