"""Built-in evaluators with explicit evidence tiers."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

from circumstances.models import (
    EvaluatorSpec,
    EvidenceRef,
    Grade,
    GradeStatus,
    MessageEvent,
    ObservationEvent,
    ToolCallEvent,
    Trajectory,
)

JudgeFunction = Callable[
    [str, str, Trajectory],
    Awaitable[tuple[GradeStatus, float | None, str, list[int], str | None, float | None]],
]


def _strings(value: Any, key: str) -> list[str]:
    raw = value.get(key, [])
    if isinstance(raw, str):
        return [raw]
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"{key} must be a string or list of strings")
    return raw


class SmokeTextEvaluator:
    type = "smoke.text"
    version = "1"

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        messages = [
            event
            for event in trajectory.events
            if isinstance(event, MessageEvent) and event.role == "assistant"
        ]
        text = "\n".join(event.content for event in messages)
        folded = text.casefold()
        failures: list[str] = []

        for needle in _strings(spec.config, "contains_all"):
            if needle.casefold() not in folded:
                failures.append(f"missing {needle!r}")
        any_needles = _strings(spec.config, "contains_any")
        if any_needles and not any(needle.casefold() in folded for needle in any_needles):
            failures.append(f"none of {any_needles!r} present")
        for needle in _strings(spec.config, "not_contains"):
            if needle.casefold() in folded:
                failures.append(f"forbidden {needle!r} present")
        pattern = spec.config.get("regex")
        if pattern is not None:
            if not isinstance(pattern, str):
                raise ValueError("regex must be a string")
            if re.search(pattern, text, re.IGNORECASE) is None:
                failures.append(f"regex {pattern!r} did not match")
        absent_pattern = spec.config.get("regex_absent")
        if absent_pattern is not None:
            if not isinstance(absent_pattern, str):
                raise ValueError("regex_absent must be a string")
            match = re.search(absent_pattern, text, re.IGNORECASE)
            if match is not None:
                failures.append(f"regex_absent matched {match.group(0)!r}")

        return Grade(
            evaluator_id=spec.id,
            evaluator_type=self.type,
            evaluator_version=self.version,
            tier=spec.tier,
            status="fail" if failures else "pass",
            reasoning="; ".join(failures) or "fast text smoke checks passed",
            evidence=[EvidenceRef(event_sequences=[event.sequence for event in messages])],
            soft=spec.soft,
        )


class SmokeEventEvaluator:
    type = "smoke.event"
    version = "1"

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        event_kind = spec.config.get("kind")
        name = spec.config.get("name")
        minimum = spec.config.get("min_count", 1)
        if not isinstance(event_kind, str) or not isinstance(minimum, int):
            raise ValueError("smoke.event requires string kind and integer min_count")
        matched = []
        for event in trajectory.events:
            if event.kind != event_kind:
                continue
            event_name = getattr(event, "name", None)
            if name is None or event_name == name:
                matched.append(event)
        passed = len(matched) >= minimum
        return Grade(
            evaluator_id=spec.id,
            evaluator_type=self.type,
            evaluator_version=self.version,
            tier=spec.tier,
            status="pass" if passed else "fail",
            reasoning=f"observed {len(matched)} matching events; required {minimum}",
            evidence=[EvidenceRef(event_sequences=[event.sequence for event in matched])],
            soft=spec.soft,
        )


class OutcomeStateEvaluator:
    type = "outcome.state"
    version = "1"

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        observation_name = spec.config.get("observation")
        expected = spec.config.get("equals")
        if not isinstance(observation_name, str):
            raise ValueError("outcome.state requires observation")
        observed = [
            event
            for event in trajectory.events
            if isinstance(event, ObservationEvent) and event.name == observation_name
        ]
        passed = bool(observed) and observed[-1].value == expected
        actual = observed[-1].value if observed else None
        return Grade(
            evaluator_id=spec.id,
            evaluator_type=self.type,
            evaluator_version=self.version,
            tier=spec.tier,
            status="pass" if passed else "fail",
            reasoning=f"expected {expected!r}; observed {actual!r}",
            evidence=[EvidenceRef(event_sequences=[event.sequence for event in observed[-1:]])],
            soft=spec.soft,
        )


class OutcomeToolEvaluator:
    type = "outcome.tool"
    version = "1"

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        tool = spec.config.get("tool")
        called = spec.config.get("called", True)
        if not isinstance(tool, str) or not isinstance(called, bool):
            raise ValueError("outcome.tool requires string tool and boolean called")
        matches = [
            event
            for event in trajectory.events
            if isinstance(event, ToolCallEvent) and event.name == tool
        ]
        passed = bool(matches) is called
        return Grade(
            evaluator_id=spec.id,
            evaluator_type=self.type,
            evaluator_version=self.version,
            tier=spec.tier,
            status="pass" if passed else "fail",
            reasoning=f"tool {tool!r} call presence was {bool(matches)}; expected {called}",
            evidence=[EvidenceRef(event_sequences=[event.sequence for event in matches])],
            soft=spec.soft,
        )


class SemanticRubricEvaluator:
    type = "semantic.rubric"
    version = "1"

    def __init__(self, judge: JudgeFunction | None = None) -> None:
        self._judge = judge

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        dimension = spec.config.get("dimension")
        rubric = spec.config.get("rubric")
        calibration = spec.config.get("calibration_version")
        if not isinstance(dimension, str) or not dimension:
            raise ValueError("semantic.rubric requires a dimension string")
        if not isinstance(rubric, str) or not rubric:
            raise ValueError("semantic.rubric requires a rubric string")
        if not isinstance(calibration, str) or not calibration:
            raise ValueError(
                "semantic.rubric requires a calibration_version string"
            )
        if self._judge is None:
            return Grade(
                evaluator_id=spec.id,
                evaluator_type=self.type,
                evaluator_version=self.version,
                tier=spec.tier,
                status="unknown",
                reasoning="no calibrated semantic judge configured",
                soft=spec.soft,
            )
        status, score, reasoning, sequences, model, cost = await self._judge(
            dimension, rubric, trajectory
        )
        return Grade(
            evaluator_id=spec.id,
            evaluator_type=self.type,
            evaluator_version=f"{self.version}:{calibration}",
            tier=spec.tier,
            status=status,
            score=score,
            reasoning=reasoning,
            evidence=[EvidenceRef(event_sequences=sequences)],
            soft=spec.soft,
            model=model,
            cost=cost,
        )


def builtin_evaluators(
    *, judge: JudgeFunction | None = None
) -> list[
    SmokeTextEvaluator
    | SmokeEventEvaluator
    | OutcomeStateEvaluator
    | OutcomeToolEvaluator
    | SemanticRubricEvaluator
]:
    return [
        SmokeTextEvaluator(),
        SmokeEventEvaluator(),
        OutcomeStateEvaluator(),
        OutcomeToolEvaluator(),
        SemanticRubricEvaluator(judge),
    ]

