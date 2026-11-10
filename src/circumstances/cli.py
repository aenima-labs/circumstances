"""Circumstances command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from circumstances.adapters.openai_compatible import OpenAICompatibleSubjectPlugin
from circumstances.adapters.toy import ToySubjectPlugin
from circumstances.artifacts import FileArtifactStore, verify_bundle
from circumstances.evaluators import builtin_evaluators
from circumstances.fetch import resolve_pack
from circumstances.migration import migrate_gears_v3
from circumstances.models import RunPlan
from circumstances.pack import lint_pack, load_pack
from circumstances.registry import EvaluatorRegistry
from circumstances.runner import run_loaded_pack
from circumstances.schema import export_schemas
from circumstances.selftest import run_pack_selftests


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "lint-pack":
        resolved = resolve_pack(
            args.pack,
            trust=args.trust,
            expected_digest=args.digest,
        )
        pack = load_pack(
            resolved.path,
            source=resolved.source,
            digest=resolved.digest,
            revision=resolved.revision,
        )
        warnings = lint_pack(pack)
        registry = _evaluator_registry()
        failures = asyncio.run(run_pack_selftests(pack, registry))
        print(f"{pack.manifest.id}@{pack.manifest.version}: {len(pack.cases)} cases")
        for warning in warnings:
            print(f"warning: {warning}")
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1 if failures else 0
    if args.command == "run":
        return asyncio.run(_run(args))
    if args.command == "migrate-pack":
        migrate_gears_v3(Path(args.source), Path(args.destination))
        print(Path(args.destination).resolve())
        return 0
    if args.command == "export-schema":
        for path in export_schemas(Path(args.destination)):
            print(path)
        return 0
    if args.command == "verify-bundle":
        failures = verify_bundle(Path(args.bundle))
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        print("bundle verified")
        return 0
    parser.error("a command is required")
    return 2


async def _run(args: argparse.Namespace) -> int:
    resolved = resolve_pack(
        args.pack,
        trust=args.trust,
        expected_digest=args.digest,
    )
    pack = load_pack(
        resolved.path,
        source=resolved.source,
        digest=resolved.digest,
        revision=resolved.revision,
    )
    subject = (
        ToySubjectPlugin()
        if args.subject == "toy"
        else OpenAICompatibleSubjectPlugin(model=args.model)
    )
    lint_pack(pack, subject_capabilities=set(subject.descriptor.capabilities))
    registry = _evaluator_registry()
    summary = await run_loaded_pack(
        pack,
        RunPlan(
            pack_ref=args.pack,
            case_ids=args.case or None,
            subject=args.subject,
            repetitions=args.repetitions,
            concurrency=args.concurrency,
            retention=args.retention,
            trust=args.trust,
        ),
        subject=subject,
        evaluators=registry,
    )
    files = {
        path.relative_to(pack.root).as_posix(): path.read_bytes()
        for path in pack.root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(pack.root).parts
    }
    bundle = FileArtifactStore(Path(args.results)).persist(summary, pack_files=files)
    passed = sum(result.passed for result in summary.results)
    print(
        json.dumps(
            {
                "run_id": summary.run_id,
                "passed": summary.passed,
                "trials_passed": passed,
                "trials": len(summary.results),
                "bundle": str(bundle),
            },
            indent=2,
        )
    )
    return 0 if summary.passed else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="circumstances")
    parser.add_argument("--version", action="version", version="circumstances 0.1.0")
    subparsers = parser.add_subparsers(dest="command")

    lint = subparsers.add_parser("lint-pack", help="validate a pack without running it")
    lint.add_argument("pack")
    _resolution_options(lint)

    run = subparsers.add_parser("run", help="run a pack against a subject")
    run.add_argument("pack")
    run.add_argument("--subject", choices=["toy", "openai-compatible"], default="toy")
    run.add_argument("--model")
    run.add_argument("--case", action="append")
    run.add_argument("--repetitions", type=int, default=1)
    run.add_argument("--concurrency", type=int, default=1)
    run.add_argument("--retention", choices=["purge", "artifacts", "preserve"], default="artifacts")
    run.add_argument("--results", default="results")
    _resolution_options(run)

    migrate = subparsers.add_parser("migrate-pack", help="convert Gears schema v3 to v4")
    migrate.add_argument("source")
    migrate.add_argument("destination")

    schema = subparsers.add_parser("export-schema", help="write JSON Schemas")
    schema.add_argument("destination", nargs="?", default="jsonschema/v4")

    verify = subparsers.add_parser("verify-bundle", help="verify a sealed run bundle")
    verify.add_argument("bundle")
    return parser


def _resolution_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--digest")
    parser.add_argument(
        "--trust",
        choices=["local", "verified", "untrusted"],
        default="local",
    )


def _evaluator_registry() -> EvaluatorRegistry:
    registry = EvaluatorRegistry()
    for evaluator in builtin_evaluators():
        registry.register(evaluator)
    return registry


if __name__ == "__main__":
    raise SystemExit(main())

