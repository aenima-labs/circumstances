"""Versioned Eval Provider API contracts used by hosting platforms."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from circumstances.models import ContractModel, JSONValue, RunPlan, RunSummary

PROVIDER_API_VERSION: Literal["circumstances.provider.v1"] = "circumstances.provider.v1"


class ProviderCapabilities(ContractModel):
    api_version: Literal["circumstances.provider.v1"] = PROVIDER_API_VERSION
    provider: str
    provider_version: str
    subjects: dict[str, list[str]]
    evaluator_types: list[str]
    supports_cancel: bool = True
    supports_artifacts: bool = True


class PackCatalogueEntry(ContractModel):
    id: str
    version: str
    digest: str
    title: str
    case_ids: list[str]
    required_capabilities: list[str]


class CallbackCapability(ContractModel):
    url: str
    token: str
    audience: str
    expires_at: datetime
    allowed_events: list[
        Literal[
            "run.started",
            "case.completed",
            "run.completed",
            "run.failed",
            "run.canceled",
        ]
    ]


class TargetCapability(ContractModel):
    adapter: str
    endpoint: str
    token: str
    audience: str
    expires_at: datetime
    fixture: dict[str, JSONValue] = Field(default_factory=dict)


class ProviderRunRequest(ContractModel):
    api_version: Literal["circumstances.provider.v1"] = PROVIDER_API_VERSION
    platform_run_id: str
    pack_id: str
    pack_version: str
    pack_digest: str
    plan: RunPlan
    target: TargetCapability
    callback: CallbackCapability
    artifact_destination: str | None = None


class RunEventBase(ContractModel):
    api_version: Literal["circumstances.provider.v1"] = PROVIDER_API_VERSION
    event_id: str
    sequence: int = Field(ge=0)
    platform_run_id: str
    provider_run_id: str
    pack_id: str
    pack_version: str
    pack_digest: str
    occurred_at: datetime


class RunStartedEvent(RunEventBase):
    type: Literal["run.started"] = "run.started"
    runner_version: str


class CaseCompletedEvent(RunEventBase):
    type: Literal["case.completed"] = "case.completed"
    case_id: str
    attempt: int
    passed: bool
    result: dict[str, JSONValue]


class RunCompletedEvent(RunEventBase):
    type: Literal["run.completed"] = "run.completed"
    summary: RunSummary
    artifact_uri: str
    artifact_digest: str


class RunFailedEvent(RunEventBase):
    type: Literal["run.failed"] = "run.failed"
    error: str


class RunCanceledEvent(RunEventBase):
    type: Literal["run.canceled"] = "run.canceled"
    reason: str


RunEvent = Annotated[
    RunStartedEvent
    | CaseCompletedEvent
    | RunCompletedEvent
    | RunFailedEvent
    | RunCanceledEvent,
    Field(discriminator="type"),
]

