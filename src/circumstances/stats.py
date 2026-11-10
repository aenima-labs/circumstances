"""Repeated-trial statistics without hiding incompatible or missing trials."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from circumstances.models import TrialResult


@dataclass(frozen=True)
class CaseStatistics:
    case_id: str
    trials: int
    passed: int
    pass_rate: float
    pass_at_k: float
    pass_power_k: float
    wilson_low: float
    wilson_high: float


def aggregate_cases(results: list[TrialResult]) -> list[CaseStatistics]:
    grouped: dict[str, list[TrialResult]] = defaultdict(list)
    for result in results:
        grouped[result.case_id].append(result)
    return [
        _case_statistics(case_id, trials)
        for case_id, trials in sorted(grouped.items())
    ]


def _case_statistics(case_id: str, trials: list[TrialResult]) -> CaseStatistics:
    count = len(trials)
    passed = sum(result.passed for result in trials)
    rate = passed / count if count else 0
    # Empirical forms for a batch of k trials. pass@k asks whether at least one
    # succeeds; pass^k asks whether every trial succeeds.
    pass_at_k = 1.0 - (1.0 - rate) ** count if count else 0
    pass_power_k = rate**count if count else 0
    low, high = _wilson(passed, count)
    return CaseStatistics(
        case_id=case_id,
        trials=count,
        passed=passed,
        pass_rate=rate,
        pass_at_k=pass_at_k,
        pass_power_k=pass_power_k,
        wilson_low=low,
        wilson_high=high,
    )


def _wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials == 0:
        return 0.0, 1.0
    rate = successes / trials
    denominator = 1 + z * z / trials
    center = (rate + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) + z * z / (4 * trials)) / trials)
    margin /= denominator
    return max(0.0, center - margin), min(1.0, center + margin)

