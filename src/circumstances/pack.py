"""Pack-v4 loading and structural validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from circumstances.errors import PackError
from circumstances.models import (
    CaseSpec,
    EvaluatorSelfTest,
    EvaluatorSpec,
    PackManifest,
    RuleSpec,
)


@dataclass(frozen=True)
class LoadedPack:
    root: Path
    manifest: PackManifest
    rules: dict[str, RuleSpec]
    cases: dict[str, CaseSpec]
    source: str
    digest: str
    revision: str | None = None

    def case(self, case_id: str) -> CaseSpec:
        try:
            return self.cases[case_id]
        except KeyError as exc:
            known = ", ".join(sorted(self.cases))
            raise PackError(f"unknown case {case_id!r}; available: {known}") from exc

    def evaluators_for(self, case: CaseSpec) -> list[EvaluatorSpec]:
        inherited = list(self.manifest.evaluators)
        for target in case.targets:
            inherited.extend(self.rules[target].evaluators)
        inherited.extend(case.evaluators)
        seen: set[str] = set()
        for evaluator in inherited:
            if evaluator.id in seen:
                raise PackError(
                    f"case {case.id!r} inherits duplicate evaluator id {evaluator.id!r}"
                )
            seen.add(evaluator.id)
        return inherited

    def selftests_for(self, case: CaseSpec) -> list[EvaluatorSelfTest]:
        inherited = list(self.manifest.selftests)
        for target in case.targets:
            inherited.extend(self.rules[target].selftests)
        inherited.extend(case.selftests)
        return inherited


def load_pack(
    root: Path,
    *,
    source: str | None = None,
    digest: str = "",
    revision: str | None = None,
) -> LoadedPack:
    root = root.resolve()
    manifest = _validate(PackManifest, root / "pack.yaml")
    rules: dict[str, RuleSpec] = {}
    cases: dict[str, CaseSpec] = {}

    rules_root = root / "rules"
    if not rules_root.is_dir():
        raise PackError(f"missing rules directory: {rules_root}")

    for rule_file in sorted(rules_root.glob("*/rule.yaml")):
        rule = _validate(RuleSpec, rule_file)
        if rule.id in rules:
            raise PackError(f"duplicate rule id {rule.id!r}")
        rules[rule.id] = rule
        for case_file in sorted(rule_file.parent.glob("cases/*/case.yaml")):
            case = _validate(CaseSpec, case_file)
            if case.id in cases:
                raise PackError(f"duplicate case id {case.id!r}")
            cases[case.id] = case

    if not rules:
        raise PackError(f"pack {manifest.id!r} contains no rules")
    if not cases:
        raise PackError(f"pack {manifest.id!r} contains no cases")

    for case in cases.values():
        unknown = sorted(set(case.targets) - rules.keys())
        if unknown:
            raise PackError(f"case {case.id!r} targets unknown rules: {unknown}")

    pack = LoadedPack(
        root=root,
        manifest=manifest,
        rules=rules,
        cases=cases,
        source=source or str(root),
        digest=digest,
        revision=revision,
    )
    for case in cases.values():
        pack.evaluators_for(case)
    return pack


def lint_pack(pack: LoadedPack, *, subject_capabilities: set[str] | None = None) -> list[str]:
    warnings: list[str] = []
    if subject_capabilities is not None:
        missing = sorted(set(pack.manifest.required_capabilities) - subject_capabilities)
        if missing:
            raise PackError(f"subject is missing required capabilities: {missing}")
    if pack.manifest.expires_at and pack.manifest.expires_at < pack.manifest.created_at:
        raise PackError("pack expires_at must be after created_at")
    if not pack.manifest.reviewed_at:
        warnings.append("pack has no reviewed_at timestamp")
    if not any(e.tier != "smoke" for e in pack.manifest.evaluators) and all(
        all(e.tier == "smoke" for e in pack.evaluators_for(case)) for case in pack.cases.values()
    ):
        warnings.append("pack contains only smoke evaluators and cannot support semantic claims")
    for case in pack.cases.values():
        statuses: dict[str, set[str]] = {}
        for selftest in pack.selftests_for(case):
            statuses.setdefault(selftest.evaluator_id, set()).add(selftest.expected_status)
        for evaluator in pack.evaluators_for(case):
            expected = statuses.get(evaluator.id, set())
            if not {"pass", "fail"}.issubset(expected):
                warnings.append(
                    f"case {case.id} evaluator {evaluator.id} lacks known-pass/known-fail selftests"
                )
    return warnings


def _validate(model: type[Any], path: Path) -> Any:
    if not path.is_file():
        raise PackError(f"missing pack file: {path}")
    try:
        raw = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise PackError(f"could not read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PackError(f"{path} must contain a YAML mapping")
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise PackError(f"invalid {path}:\n{exc}") from exc

