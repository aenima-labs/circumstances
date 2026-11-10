"""Stable plugin protocols for subjects and evaluators."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from circumstances.models import (
    Action,
    EvaluatorSpec,
    Event,
    Grade,
    PluginDescriptor,
    Trajectory,
    TrialSpec,
)


class TrialSession(Protocol):
    """One isolated subject session."""

    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]:
        """Execute one authored action and return newly observed events."""

    async def close(self) -> None:
        """Release resources according to the trial retention policy."""


class SubjectPlugin(Protocol):
    """Adapter for a system under evaluation."""

    @property
    def descriptor(self) -> PluginDescriptor:
        """Stable plugin identity and capabilities."""

    async def prepare(self, trial: TrialSpec) -> TrialSession:
        """Create an isolated trial session."""


class EvaluatorPlugin(Protocol):
    """Evaluator over an immutable trajectory."""

    @property
    def type(self) -> str:
        """Namespaced evaluator type."""

    @property
    def version(self) -> str:
        """Evaluator implementation version."""

    async def evaluate(self, spec: EvaluatorSpec, trajectory: Trajectory) -> Grade:
        """Evaluate one spec and return evidence-bound grade."""


EvaluatorFunction = Callable[[EvaluatorSpec, Trajectory], Awaitable[Grade]]

