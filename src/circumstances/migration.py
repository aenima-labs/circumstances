"""Best-effort conversion of private Gears schema-v3 packs to pack format v4."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from circumstances.errors import PackError


def migrate_gears_v3(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise PackError(f"migration destination is not empty: {destination}")
    manifest = _read(source / "pack.yaml")
    if manifest.get("schema_version") != 3:
        raise PackError("migrate-pack currently accepts Gears schema_version 3 only")
    destination.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    _write(
        destination / "pack.yaml",
        {
            "format_version": 4,
            "id": manifest["id"],
            "version": manifest["version"],
            "title": manifest.get("id", "Migrated pack").replace("-", " ").title(),
            "description": manifest.get("description", ""),
            "license": manifest.get("license") or "LicenseRef-Private",
            "publisher": {"name": ", ".join(manifest.get("owners", [])) or "Private"},
            "created_at": now,
            "required_capabilities": ["message.text", "kodama.memorome"],
            "permissions": ["fixture:kodama.memorome"],
            "tags": [
                f"family:{manifest.get('family', 'unknown')}",
                f"maturity:{manifest.get('maturity', 'unknown')}",
                "migration:gears-v3",
            ],
            "evaluators": _migrate_graders(manifest.get("graders", [])),
        },
    )

    for rule_file in sorted((source / "rules").glob("*/rule.yaml")):
        rule_id = rule_file.parent.name
        rule = _read(rule_file)
        target_rule = destination / "rules" / rule_id
        _write(
            target_rule / "rule.yaml",
            {
                "id": rule_id,
                "title": rule.get("title", rule_id),
                "description": rule.get("description", ""),
                "severity": rule.get("severity", "medium"),
                "tags": ["proposed"] if rule.get("proposed") else [],
                "provenance": [],
                "evaluators": _migrate_graders(rule.get("graders", [])),
            },
        )
        for case_file in sorted(rule_file.parent.glob("cases/*/case.yaml")):
            case = _read(case_file)
            case_id = f"{rule_id}/{case_file.parent.name}"
            fixture_config: dict[str, Any] = {
                "memorome": case.get("memorome"),
                "patches": case.get("patches", []),
            }
            _write(
                target_rule / "cases" / case_file.parent.name / "case.yaml",
                {
                    "id": case_id,
                    "title": case.get("title") or case_file.parent.name.replace("-", " ").title(),
                    "description": case.get("description", ""),
                    "targets": [rule_id],
                    "polarity": "attack",
                    "actors": {"user": case.get("persona", "simulated user")},
                    "fixture": {
                        "type": "kodama.memorome",
                        "config": fixture_config,
                        "privacy": "internal",
                    },
                    "actions": [_migrate_turn(turn) for turn in case.get("turns", [])],
                    "expected_outcomes": [],
                    "evaluators": _migrate_graders(case.get("graders", [])),
                    "trials": 1,
                    "timeout_s": 120,
                    "holdout": False,
                    "tags": ["migration:gears-v3"],
                },
            )


def _migrate_turn(turn: dict[str, Any]) -> dict[str, Any]:
    user = turn.get("user")
    if isinstance(user, str):
        return {"kind": "message", "role": "user", "content": user}
    if isinstance(user, dict):
        return {
            "kind": "generated_message",
            "prompt": user.get("prompt", ""),
            "persona": user.get("persona"),
            "model": None,
        }
    raise PackError(f"unsupported Gears turn: {turn!r}")


def _migrate_graders(graders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    migrated: list[dict[str, Any]] = []
    for grader in graders:
        grader_id = grader["id"]
        if judge := grader.get("judge"):
            migrated.append(
                {
                    "id": grader_id,
                    "type": "semantic.rubric",
                    "tier": "semantic",
                    "scope": "trajectory",
                    "soft": grader.get("soft", False),
                    "config": {
                        "dimension": grader_id,
                        "rubric": judge.get("prompt", ""),
                        "calibration_version": "gears-v3-uncalibrated",
                    },
                }
            )
        for index, matcher in enumerate(grader.get("match", []), start=1):
            migrated.extend(
                _migrate_matcher(
                    grader_id,
                    index,
                    matcher,
                    soft=grader.get("soft", False),
                )
            )
    return migrated


def _migrate_matcher(
    grader_id: str, index: int, matcher: dict[str, Any], *, soft: bool
) -> list[dict[str, Any]]:
    identifier = f"{grader_id}.smoke-{index}"
    text_keys = {
        "contains_any": "contains_any",
        "contains_all": "contains_all",
        "not_contains_any": "not_contains",
        "regex_present": "regex",
        "regex_absent": "regex_absent",
    }
    for old, new in text_keys.items():
        if old in matcher:
            return [
                {
                    "id": identifier,
                    "type": "smoke.text",
                    "tier": "smoke",
                    "scope": "trajectory",
                    "soft": soft,
                    "config": {new: matcher[old]},
                }
            ]
    if "tool_called" in matcher or "tool_not_called" in matcher:
        key = "tool_called" if "tool_called" in matcher else "tool_not_called"
        value = matcher[key]
        names = value.get("name", []) if isinstance(value, dict) else []
        return [
            {
                "id": f"{identifier}-{position}",
                "type": "outcome.tool",
                "tier": "outcome",
                "scope": "trajectory",
                "soft": soft,
                "config": {"tool": name, "called": key == "tool_called"},
            }
            for position, name in enumerate(names, start=1)
        ]
    raise PackError(f"unsupported Gears matcher: {matcher!r}")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise PackError(f"could not read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackError(f"{path} must contain a mapping")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True))

