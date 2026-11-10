"""JSON Schema export for public contracts."""

import json
from pathlib import Path

from pydantic import BaseModel

from circumstances.models import (
    CaseSpec,
    Grade,
    PackManifest,
    RuleSpec,
    RunPlan,
    RunSummary,
    Trajectory,
)

SCHEMAS: dict[str, type[BaseModel]] = {
    "pack.schema.json": PackManifest,
    "rule.schema.json": RuleSpec,
    "case.schema.json": CaseSpec,
    "run-plan.schema.json": RunPlan,
    "trajectory.schema.json": Trajectory,
    "grade.schema.json": Grade,
    "run.schema.json": RunSummary,
}


def export_schemas(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, model in SCHEMAS.items():
        path = destination / filename
        path.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written

