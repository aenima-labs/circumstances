"""Public Circumstances pack, trajectory, grade, and run contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

FORMAT_VERSION = 4
type JSONValue = JsonValue

GradeStatus = Literal["pass", "fail", "unknown", "error", "skipped"]
TrustLevel = Literal["local", "verified", "untrusted"]
EvaluationTier = Literal[
    "static",
    "smoke",
    "outcome",
    "semantic",
    "situational",
    "end_to_end",
    "human",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


class FixtureRef(ContractModel):
    type: str
    config: dict[str, JSONValue] = Field(default_factory=dict)
    version: str | None = None
    digest: str | None = None
    privacy: Literal["public", "internal", "confidential", "restricted"] = "public"


class MessageAction(ContractModel):
    kind: Literal["message"] = "message"
    role: Literal["user", "system", "environment"] = "user"
    content: str


class GeneratedMessageAction(ContractModel):
    kind: Literal["generated_message"] = "generated_message"
    prompt: str
    persona: str | None = None
    model: str | None = None


class WaitAction(ContractModel):
    kind: Literal["wait"] = "wait"
    duration_s: float | None = Field(default=None, ge=0)
    until: str | None = None

    @model_validator(mode="after")
    def exactly_one_wait(self) -> Self:
        if (self.duration_s is None) == (self.until is None):
            raise ValueError("wait action requires exactly one of duration_s or until")
        return self


class EnvironmentAction(ContractModel):
    kind: Literal["environment"] = "environment"
    name: str
    arguments: dict[str, JSONValue] = Field(default_factory=dict)


class ExtensionAction(ContractModel):
    kind: Literal["extension"] = "extension"
    namespace: str
    name: str
    input: dict[str, JSONValue] = Field(default_factory=dict)


Action = Annotated[
    MessageAction
    | GeneratedMessageAction
    | WaitAction
    | EnvironmentAction
    | ExtensionAction,
    Field(discriminator="kind"),
]


class EventBase(ContractModel):
    sequence: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action_index: int | None = Field(default=None, ge=0)


class MessageEvent(EventBase):
    kind: Literal["message"] = "message"
    role: Literal["user", "assistant", "system", "environment"]
    content: str
    channel: str = "delivered"


class ToolCallEvent(EventBase):
    kind: Literal["tool_call"] = "tool_call"
    call_id: str
    name: str
    arguments: dict[str, JSONValue] = Field(default_factory=dict)


class ToolResultEvent(EventBase):
    kind: Literal["tool_result"] = "tool_result"
    call_id: str
    name: str
    output: JSONValue = None
    error: str | None = None


class ObservationEvent(EventBase):
    kind: Literal["observation"] = "observation"
    name: str
    value: JSONValue = None


class ArtifactEvent(EventBase):
    kind: Literal["artifact"] = "artifact"
    name: str
    media_type: str
    uri: str
    digest: str | None = None


class StateChangeEvent(EventBase):
    kind: Literal["state_change"] = "state_change"
    path: str
    before: JSONValue = None
    after: JSONValue = None


class ContextSnapshotEvent(EventBase):
    kind: Literal["context_snapshot"] = "context_snapshot"
    components: dict[str, JSONValue] = Field(default_factory=dict)


class PolicyDecisionEvent(EventBase):
    kind: Literal["policy_decision"] = "policy_decision"
    policy: str
    decision: str
    reason: str = ""


class MetricEvent(EventBase):
    kind: Literal["metric"] = "metric"
    name: str
    value: float
    unit: str = ""


class TerminalEvent(EventBase):
    kind: Literal["terminal"] = "terminal"
    status: Literal["completed", "failed", "canceled", "timed_out"]
    reason: str = ""


class ExtensionEvent(EventBase):
    kind: Literal["extension"] = "extension"
    namespace: str
    name: str
    payload: dict[str, JSONValue] = Field(default_factory=dict)


Event = Annotated[
    MessageEvent
    | ToolCallEvent
    | ToolResultEvent
    | ObservationEvent
    | ArtifactEvent
    | StateChangeEvent
    | ContextSnapshotEvent
    | PolicyDecisionEvent
    | MetricEvent
    | TerminalEvent
    | ExtensionEvent,
    Field(discriminator="kind"),
]


class EvaluatorSpec(ContractModel):
    id: str
    type: str
    tier: EvaluationTier
    scope: Literal["action", "trajectory", "outcome"] = "trajectory"
    action_indexes: list[int] | None = None
    soft: bool = False
    config: dict[str, JSONValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def smoke_types_are_smoke(self) -> Self:
        if self.type.startswith("smoke.") and self.tier != "smoke":
            raise ValueError(f"{self.type} evaluators must declare tier: smoke")
        if self.tier == "smoke" and not self.type.startswith("smoke."):
            raise ValueError("smoke tier is reserved for smoke.* evaluator types")
        return self


class EvaluatorSelfTest(ContractModel):
    evaluator_id: str
    expected_status: GradeStatus
    events: list[Event]
    note: str = ""


class RuleSpec(ContractModel):
    id: str
    title: str
    description: str
    severity: str | list[str] = "medium"
    tags: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)
    evaluators: list[EvaluatorSpec] = Field(default_factory=list)
    selftests: list[EvaluatorSelfTest] = Field(default_factory=list)


class CaseSpec(ContractModel):
    id: str
    title: str
    description: str = ""
    targets: Annotated[list[str], Field(min_length=1)]
    polarity: Literal["positive", "negative", "attack", "recovery", "normal"]
    actors: dict[str, str] = Field(default_factory=dict)
    fixture: FixtureRef
    actions: Annotated[list[Action], Field(min_length=1)]
    expected_outcomes: list[str] = Field(default_factory=list)
    evaluators: list[EvaluatorSpec] = Field(default_factory=list)
    selftests: list[EvaluatorSelfTest] = Field(default_factory=list)
    trials: int = Field(default=1, ge=1)
    timeout_s: float = Field(default=120, gt=0)
    holdout: bool = False
    tags: list[str] = Field(default_factory=list)


class Publisher(ContractModel):
    name: str
    url: str | None = None


class PackManifest(ContractModel):
    format_version: int
    id: str
    version: str
    title: str
    description: str
    license: str
    publisher: Publisher
    repository: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evaluators: list[EvaluatorSpec] = Field(default_factory=list)
    selftests: list[EvaluatorSelfTest] = Field(default_factory=list)

    @field_validator("format_version")
    @classmethod
    def current_format(cls, value: int) -> int:
        if value != FORMAT_VERSION:
            raise ValueError(f"format_version must be {FORMAT_VERSION}, got {value}")
        return value


class PluginDescriptor(ContractModel):
    id: str
    version: str
    capabilities: list[str] = Field(default_factory=list)
    models: dict[str, str] = Field(default_factory=dict)


class TrialSpec(ContractModel):
    run_id: str
    trial_id: str
    pack_id: str
    pack_version: str
    case: CaseSpec
    attempt: int = Field(ge=1)
    seed: int
    retention: Literal["purge", "artifacts", "preserve"] = "artifacts"


class Trajectory(ContractModel):
    trial_id: str
    subject: PluginDescriptor
    events: list[Event] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
    error: str | None = None


class EvidenceRef(ContractModel):
    event_sequences: list[int] = Field(default_factory=list)
    artifact: str | None = None
    note: str = ""


class Grade(ContractModel):
    evaluator_id: str
    evaluator_type: str
    evaluator_version: str = "builtin"
    tier: EvaluationTier
    status: GradeStatus
    score: float | None = None
    reasoning: str = ""
    evidence: list[EvidenceRef] = Field(default_factory=list)
    soft: bool = False
    model: str | None = None
    cost: float | None = None

    @property
    def passed(self) -> bool:
        return self.status == "pass"


class TrialResult(ContractModel):
    trial_id: str
    case_id: str
    attempt: int
    seed: int
    trajectory: Trajectory
    grades: list[Grade] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(grade.soft or grade.status == "pass" for grade in self.grades)


class RunPlan(ContractModel):
    pack_ref: str
    case_ids: list[str] | None = None
    subject: str
    repetitions: int = Field(default=1, ge=1)
    seeds: list[int] = Field(default_factory=list)
    concurrency: int = Field(default=1, ge=1)
    timeout_s: float = Field(default=120, gt=0)
    retention: Literal["purge", "artifacts", "preserve"] = "artifacts"
    trust: TrustLevel = "local"


class RunLock(ContractModel):
    pack_digest: str
    pack_source: str
    pack_revision: str | None = None
    subject: PluginDescriptor
    evaluator_versions: dict[str, str] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)
    fixture_digests: dict[str, str] = Field(default_factory=dict)


class RunSummary(ContractModel):
    run_id: str
    pack_id: str
    pack_version: str
    started_at: datetime
    finished_at: datetime
    results: list[TrialResult]
    lock: RunLock

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(result.passed for result in self.results)

