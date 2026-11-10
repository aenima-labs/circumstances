"""Execute pack-owned evaluator fixtures without running a subject."""

from datetime import UTC, datetime

from circumstances.models import PluginDescriptor, Trajectory
from circumstances.pack import LoadedPack
from circumstances.registry import EvaluatorRegistry


async def run_pack_selftests(
    pack: LoadedPack, registry: EvaluatorRegistry
) -> list[str]:
    failures: list[str] = []
    for case in pack.cases.values():
        evaluators = {spec.id: spec for spec in pack.evaluators_for(case)}
        for index, selftest in enumerate(pack.selftests_for(case), start=1):
            spec = evaluators.get(selftest.evaluator_id)
            if spec is None:
                failures.append(
                    f"{case.id} selftest {index} references unknown evaluator "
                    f"{selftest.evaluator_id}"
                )
                continue
            now = datetime.now(UTC)
            trajectory = Trajectory(
                trial_id=f"selftest:{case.id}:{index}",
                subject=PluginDescriptor(id="selftest", version="1"),
                events=selftest.events,
                started_at=now,
                finished_at=now,
            )
            grade = await registry.get(spec.type).evaluate(spec, trajectory)
            if grade.status != selftest.expected_status:
                failures.append(
                    f"{case.id} evaluator {spec.id} selftest {index}: "
                    f"expected {selftest.expected_status}, got {grade.status}"
                )
    return failures

