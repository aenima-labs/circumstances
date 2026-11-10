"""Framework-owned orchestration over public plugin contracts."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime

from circumstances.errors import CapabilityError
from circumstances.models import (
    CaseSpec,
    Event,
    Grade,
    RunLock,
    RunPlan,
    RunSummary,
    TerminalEvent,
    Trajectory,
    TrialResult,
    TrialSpec,
)
from circumstances.pack import LoadedPack
from circumstances.plugins import SubjectPlugin
from circumstances.registry import EvaluatorRegistry


async def run_loaded_pack(
    pack: LoadedPack,
    plan: RunPlan,
    *,
    subject: SubjectPlugin,
    evaluators: EvaluatorRegistry,
    run_id: str | None = None,
) -> RunSummary:
    missing = sorted(
        set(pack.manifest.required_capabilities) - set(subject.descriptor.capabilities)
    )
    if missing:
        raise CapabilityError(f"subject {subject.descriptor.id!r} lacks capabilities: {missing}")

    selected = (
        [pack.case(case_id) for case_id in plan.case_ids]
        if plan.case_ids
        else list(pack.cases.values())
    )
    run_id = run_id or uuid.uuid4().hex
    started_at = datetime.now(UTC)
    jobs: list[tuple[CaseSpec, int, int]] = []
    for case in selected:
        repetitions = max(plan.repetitions, case.trials)
        for attempt in range(1, repetitions + 1):
            seed = _seed(plan.seeds, len(jobs), run_id, case.id, attempt)
            jobs.append((case, attempt, seed))

    semaphore = asyncio.Semaphore(plan.concurrency)

    async def execute(job: tuple[CaseSpec, int, int]) -> TrialResult:
        case, attempt, seed = job
        async with semaphore:
            return await _run_trial(
                pack,
                run_id=run_id,
                case=case,
                attempt=attempt,
                seed=seed,
                plan=plan,
                subject=subject,
                evaluators=evaluators,
            )

    results = await asyncio.gather(*(execute(job) for job in jobs))
    return RunSummary(
        run_id=run_id,
        pack_id=pack.manifest.id,
        pack_version=pack.manifest.version,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        results=results,
        lock=RunLock(
            pack_digest=pack.digest,
            pack_source=pack.source,
            pack_revision=pack.revision,
            subject=subject.descriptor,
            evaluator_versions=evaluators.versions(),
            models=subject.descriptor.models,
            fixture_digests={
                case.id: case.fixture.digest
                for case in selected
                if case.fixture.digest is not None
            },
        ),
    )


async def _run_trial(
    pack: LoadedPack,
    *,
    run_id: str,
    case: CaseSpec,
    attempt: int,
    seed: int,
    plan: RunPlan,
    subject: SubjectPlugin,
    evaluators: EvaluatorRegistry,
) -> TrialResult:
    trial_id = f"{case.id}--{attempt}--{uuid.uuid4().hex[:10]}"
    trial = TrialSpec(
        run_id=run_id,
        trial_id=trial_id,
        pack_id=pack.manifest.id,
        pack_version=pack.manifest.version,
        case=case,
        attempt=attempt,
        seed=seed,
        retention=plan.retention,
    )
    started_at = datetime.now(UTC)
    events: list[Event] = []
    error: str | None = None
    session = None
    try:
        session = await subject.prepare(trial)
        for action_index, action in enumerate(case.actions):
            timeout_s = min(case.timeout_s, plan.timeout_s)
            async with asyncio.timeout(timeout_s):
                observed = await session.execute(action, timeout_s=timeout_s)
            for event in observed:
                events.append(
                    event.model_copy(
                        update={"sequence": len(events), "action_index": action_index}
                    )
                )
    except TimeoutError:
        error = "trial timed out"
        events.append(
            TerminalEvent(
                sequence=len(events),
                status="timed_out",
                reason=error,
            )
        )
    except asyncio.CancelledError:
        events.append(
            TerminalEvent(
                sequence=len(events),
                status="canceled",
                reason="run canceled",
            )
        )
        raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        events.append(
            TerminalEvent(
                sequence=len(events),
                status="failed",
                reason=error,
            )
        )
    finally:
        if session is not None:
            await asyncio.shield(session.close())

    if not any(isinstance(event, TerminalEvent) for event in events):
        events.append(TerminalEvent(sequence=len(events), status="completed"))
    trajectory = Trajectory(
        trial_id=trial_id,
        subject=subject.descriptor,
        events=events,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        error=error,
    )
    grades: list[Grade] = []
    for spec in pack.evaluators_for(case):
        try:
            grade = await evaluators.get(spec.type).evaluate(spec, trajectory)
        except Exception as exc:
            grade = Grade(
                evaluator_id=spec.id,
                evaluator_type=spec.type,
                tier=spec.tier,
                status="error",
                reasoning=f"{type(exc).__name__}: {exc}",
                soft=spec.soft,
            )
        grades.append(grade)
    if error and not grades:
        grades.append(
            Grade(
                evaluator_id="framework.execution",
                evaluator_type="framework.execution",
                tier="static",
                status="error",
                reasoning=error,
            )
        )
    return TrialResult(
        trial_id=trial_id,
        case_id=case.id,
        attempt=attempt,
        seed=seed,
        trajectory=trajectory,
        grades=grades,
    )


def _seed(configured: list[int], index: int, run_id: str, case_id: str, attempt: int) -> int:
    if configured:
        return configured[index % len(configured)]
    material = f"{run_id}:{case_id}:{attempt}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

