"""Circumstances command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from circumstances.artifacts import FileArtifactStore, verify_bundle
from circumstances.bundles import (
    compare_bundles,
    list_bundles,
    regrade_bundle,
    resolve_bundle,
    show_bundle,
)
from circumstances.errors import CircumstancesError
from circumstances.evaluators import builtin_evaluators
from circumstances.fetch import ResolvedPack, ResolverPolicy, resolve_pack
from circumstances.migration import migrate_gears_v3
from circumstances.models import RunPlan, TrustLevel
from circumstances.pack import lint_pack, load_pack
from circumstances.registry import EvaluatorRegistry, RegistryError, SubjectRegistry
from circumstances.runner import run_loaded_pack
from circumstances.scaffold import add_case, add_rule, init_pack
from circumstances.schema import export_schemas
from circumstances.selftest import run_pack_selftests
from circumstances.sources import PackSource, cached_packs, load_index, load_project_sources
from circumstances.view import serve

_RUN_ADMIN = {"list", "show", "compare", "score"}
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(argv) >= 2 and argv[0] == "run" and argv[1] in _RUN_ADMIN:
            return _run_admin(argv[1:])
        parser = _parser()
        args = parser.parse_args(argv)
        if args.command == "lint-pack":
            return _lint(args.pack, args.trust, args.digest)
        if args.command == "run":
            return asyncio.run(_execute(args))
        if args.command == "migrate-pack":
            migrate_gears_v3(Path(args.source), Path(args.destination))
            print(Path(args.destination).resolve())
            return 0
        if args.command == "export-schema":
            for path in export_schemas(Path(args.destination)):
                print(path)
            return 0
        if args.command == "verify-bundle":
            return _verify(Path(args.bundle))
        if args.command == "pack":
            return _pack(args)
        if args.command == "subjects":
            _print(_subject_listing())
            return 0
        if args.command == "view":
            if args.host not in _LOOPBACK:
                raise CircumstancesError(
                    "circumstances view listens on the loopback interface only"
                )
            serve(Path(args.results), host=args.host, port=args.port)
            return 0
        parser.error("a command is required")
    except (CircumstancesError, RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="circumstances")
    parser.add_argument("--version", action="version", version="circumstances 0.1.0")
    subparsers = parser.add_subparsers(dest="command")

    lint = subparsers.add_parser("lint-pack", help="validate a pack without running it")
    lint.add_argument("pack")
    _resolution_options(lint)

    run = subparsers.add_parser(
        "run",
        help="run a pack against a subject",
        epilog="Inspections: circumstances run {list,show,compare,score} --help",
    )
    run.add_argument("pack")
    run.add_argument("--subject", default="toy")
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

    pack = subparsers.add_parser("pack", help="create, check, and install packs")
    pack_commands = pack.add_subparsers(dest="pack_command", required=True)
    init = pack_commands.add_parser("init", help="write a format-v4 pack template")
    init.add_argument("directory")
    init.add_argument("--id")
    init.add_argument("--title")
    pack_lint = pack_commands.add_parser("lint", help="validate a pack without running it")
    pack_lint.add_argument("pack")
    _resolution_options(pack_lint)
    pack_commands.add_parser("list", help="list cached and known packs")
    add = pack_commands.add_parser(
        "add",
        help="install a pack, or scaffold a rule or case",
    )
    add.add_argument("target", help="ref, index name, 'rule', or 'case'")
    add.add_argument("extra", nargs="*")
    add.add_argument("--title")
    add.add_argument(
        "--polarity",
        choices=["positive", "negative", "attack", "recovery", "normal"],
        default="positive",
    )
    add.add_argument("--digest")
    add.add_argument("--trust", choices=["local", "verified", "untrusted"])

    subparsers.add_parser("subjects", help="list installed subject plugins")

    view = subparsers.add_parser("view", help="open a read-only local results viewer")
    view.add_argument("results", nargs="?", default="results")
    view.add_argument("--host", default="127.0.0.1")
    view.add_argument("--port", type=int, default=8765)
    return parser


def _resolution_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--digest")
    parser.add_argument(
        "--trust",
        choices=["local", "verified", "untrusted"],
        default="local",
    )


def _run_admin(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="circumstances run")
    commands = parser.add_subparsers(dest="command", required=True)
    listed = commands.add_parser("list", help="list sealed bundles")
    listed.add_argument("--results", default="results")
    show = commands.add_parser("show", help="show one sealed bundle")
    show.add_argument("run")
    show.add_argument("--results", default="results")
    compare = commands.add_parser("compare", help="compare two compatible bundles")
    compare.add_argument("a")
    compare.add_argument("b")
    compare.add_argument("--results", default="results")
    score = commands.add_parser("score", help="regrade a sealed bundle without calling the subject")
    score.add_argument("bundle")
    score.add_argument("--results", default="results")
    args = parser.parse_args(argv)
    results = Path(args.results)
    if args.command == "list":
        _print({"runs": list_bundles(results)})
        return 0
    if args.command == "show":
        _print(show_bundle(resolve_bundle(args.run, results)))
        return 0
    if args.command == "compare":
        _print(
            compare_bundles(
                resolve_bundle(args.a, results),
                resolve_bundle(args.b, results),
            )
        )
        return 0
    report = asyncio.run(
        regrade_bundle(resolve_bundle(args.bundle, results), _evaluator_registry())
    )
    _print(report)
    return 0 if report["passed"] else 1


def _pack(args: argparse.Namespace) -> int:
    if args.pack_command == "init":
        path = init_pack(Path(args.directory), pack_id=args.id, title=args.title)
        print(path.resolve())
        return 0
    if args.pack_command == "lint":
        return _lint(args.pack, args.trust, args.digest)
    if args.pack_command == "list":
        _print(_pack_listing())
        return 0
    if args.pack_command == "add":
        return _pack_add(args)
    raise CircumstancesError(f"unknown pack command: {args.pack_command}")


def _pack_add(args: argparse.Namespace) -> int:
    if args.target == "rule":
        if len(args.extra) != 2:
            raise CircumstancesError("usage: circumstances pack add rule <pack> <rule-id>")
        path = add_rule(Path(args.extra[0]), args.extra[1], title=args.title)
        print(path)
        return 0
    if args.target == "case":
        if len(args.extra) != 3:
            raise CircumstancesError(
                "usage: circumstances pack add case <pack> <rule-id> <case-id>"
            )
        path = add_case(
            Path(args.extra[0]),
            args.extra[1],
            args.extra[2],
            polarity=args.polarity,
            title=args.title,
        )
        print(path)
        return 0
    if args.extra:
        raise CircumstancesError("pack add takes one ref or name")
    resolved = _resolve_addition(args.target, trust=args.trust, digest=args.digest)
    _print(
        {
            "source": resolved.source,
            "digest": resolved.digest,
            "revision": resolved.revision,
            "path": str(resolved.path),
            "trust": resolved.trust,
        }
    )
    return 0


def _resolve_addition(target: str, *, trust: TrustLevel | None, digest: str | None) -> ResolvedPack:
    if _is_direct(target):
        level: TrustLevel = trust or ("local" if _is_local(target) else "untrusted")
        if level == "untrusted" and not digest:
            raise CircumstancesError("untrusted refs require --digest")
        return resolve_pack(target, trust=level, expected_digest=digest, policy=_policy())
    chosen = _named_source(target)
    if digest and chosen.digest and digest != chosen.digest:
        raise CircumstancesError("digest does not match the pinned source")
    expected = digest or chosen.digest
    level = trust or chosen.trust
    if level == "untrusted" and not expected:
        raise CircumstancesError("untrusted refs require --digest")
    return resolve_pack(
        chosen.ref,
        trust=level,
        expected_digest=expected,
        policy=_policy(),
    )


def _named_source(name: str) -> PackSource:
    index = load_index()
    if name in index:
        return index[name]
    project = load_project_sources()
    if name in project:
        return project[name]
    known = ", ".join(sorted(set(index) | set(project))) or "none"
    raise CircumstancesError(f"unknown pack {name!r}; known: {known}")


def _pack_listing() -> dict[str, object]:
    index = load_index()
    project = load_project_sources()
    known = [
        {
            "name": source.name,
            "ref": source.ref,
            "trust": source.trust,
            "digest": source.digest or "",
            "revision": source.revision or "",
            "kind": source.kind,
        }
        for source in [*index.values(), *project.values()]
    ]
    return {"cached": cached_packs(_policy()), "known": known}


def _is_direct(target: str) -> bool:
    if target.startswith(("git+", "https://", "http://")):
        return True
    return _is_local(target)


def _is_local(target: str) -> bool:
    path = Path(target).expanduser()
    return path.is_dir() and (path / "pack.yaml").is_file()


def _policy() -> ResolverPolicy:
    return ResolverPolicy()


def _lint(ref: str, trust: TrustLevel, digest: str | None) -> int:
    resolved = resolve_pack(ref, trust=trust, expected_digest=digest, policy=_policy())
    pack = load_pack(
        resolved.path,
        source=resolved.source,
        digest=resolved.digest,
        revision=resolved.revision,
    )
    warnings = lint_pack(pack)
    failures = asyncio.run(run_pack_selftests(pack, _evaluator_registry()))
    print(f"{pack.manifest.id}@{pack.manifest.version}: {len(pack.cases)} cases")
    for warning in warnings:
        print(f"warning: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


async def _execute(args: argparse.Namespace) -> int:
    resolved = resolve_pack(
        args.pack,
        trust=args.trust,
        expected_digest=args.digest,
        policy=_policy(),
    )
    pack = load_pack(
        resolved.path,
        source=resolved.source,
        digest=resolved.digest,
        revision=resolved.revision,
    )
    subject = _subject_registry().create(args.subject, model=args.model)
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
    _print(
        {
            "run_id": summary.run_id,
            "passed": summary.passed,
            "trials_passed": passed,
            "trials": len(summary.results),
            "bundle": str(bundle),
        }
    )
    return 0 if summary.passed else 1


def _verify(bundle: Path) -> int:
    failures = verify_bundle(bundle)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("bundle verified")
    return 0


def _subject_registry() -> SubjectRegistry:
    registry = SubjectRegistry()
    registry.load_entry_points()
    return registry


def _subject_listing() -> dict[str, object]:
    registry = _subject_registry()
    subjects: list[dict[str, object]] = []
    for name in registry.names():
        descriptor = registry.create(name).descriptor
        subjects.append(
            {
                "id": descriptor.id,
                "version": descriptor.version,
                "capabilities": list(descriptor.capabilities),
            }
        )
    return {"subjects": subjects}


def _evaluator_registry() -> EvaluatorRegistry:
    registry = EvaluatorRegistry()
    for evaluator in builtin_evaluators():
        registry.register(evaluator)
    registry.load_entry_points()
    return registry


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
