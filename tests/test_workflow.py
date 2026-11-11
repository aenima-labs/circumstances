import hashlib
import json
import threading
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from urllib.request import urlopen

import pytest
import yaml

from circumstances.artifacts import FileArtifactStore, verify_bundle
from circumstances.bundles import pass_at_k, pass_hat_k
from circumstances.cli import main
from circumstances.fetch import ResolverPolicy, _find_pack_root, hash_directory, split_git_fragment
from circumstances.models import RunSummary
from circumstances.sources import cached_packs, load_index
from circumstances.view import make_server

PACKS = Path(__file__).resolve().parents[1] / "packs"
PINNED_REVISION = "8fa1ff808135b2c598828040a0a8b0eb17a8dad0"


def test_pass_estimators() -> None:
    assert pass_at_k(1, 1) == 1
    assert pass_at_k(0, 1) == 0
    assert pass_hat_k(0, 1) == 0
    assert pass_at_k(1, 3, 2) == pytest.approx(2 / 3)
    assert pass_hat_k(2, 3, 2) == pytest.approx(1 / 3)


def test_index_pins_match_the_public_packs() -> None:
    index = load_index()
    assert set(index) == {
        "aenima/action-integrity",
        "aenima/ai-risk",
        "aenima/grounding",
        "aenima/human-agency",
        "aenima/privacy-security",
        "aenima/reliability",
        "aenima/transparency",
    }
    for name, source in index.items():
        directory = PACKS / name.split("/", 1)[1]
        assert source.trust == "verified"
        assert source.revision == PINNED_REVISION
        assert source.digest == hash_directory(directory)
        assert f"path=packs/{directory.name}" in source.ref


def test_git_fragment_rejects_escape_and_selects_one_pack(tmp_path: Path) -> None:
    repository, ref, subpath = split_git_fragment(
        "https://example.com/repo.git#ref=abc123&path=packs/grounding"
    )
    assert repository == "https://example.com/repo.git"
    assert ref == "abc123"
    assert subpath == "packs/grounding"
    with pytest.raises(Exception, match="escapes"):
        split_git_fragment("https://example.com/repo.git#ref=abc&path=../secret")

    _write_pack(tmp_path / "packs" / "grounding", "one")
    _write_pack(tmp_path / "packs" / "other", "two")
    assert _find_pack_root(tmp_path, "packs/grounding").name == "grounding"
    with pytest.raises(Exception, match="exactly one pack"):
        _find_pack_root(tmp_path)


def test_template_lints_runs_and_can_grow(tmp_path: Path) -> None:
    pack = tmp_path / "example-pack"
    results = tmp_path / "results"
    assert _invoke(["pack", "init", str(pack)])[0] == 0
    assert "format v4" in (pack / "pack.yaml").read_text()
    code, output, _ = _invoke(["pack", "lint", str(pack)])
    assert code == 0
    assert "warning:" not in output
    assert _invoke(["pack", "add", "rule", str(pack), "second-rule"])[0] == 0
    assert (
        _invoke(
            ["pack", "add", "case", str(pack), "second-rule", "normal-use", "--polarity", "normal"]
        )[0]
        == 0
    )
    assert _invoke(["pack", "lint", str(pack)])[0] == 0
    code, output, _ = _invoke(["run", str(pack), "--subject", "toy", "--results", str(results)])
    assert code == 0
    summary = json.loads(output)
    assert summary["passed"] is True
    bundle = Path(summary["bundle"])
    assert verify_bundle(bundle) == []


def test_run_compare_refuses_incompatible_locks(tmp_path: Path) -> None:
    pack = tmp_path / "example-pack"
    results = tmp_path / "results"
    assert _invoke(["pack", "init", str(pack)])[0] == 0
    code, output, _ = _invoke(
        ["run", str(pack), "--subject", "toy", "--results", str(results), "--repetitions", "1"]
    )
    assert code == 0
    bundle = Path(json.loads(output)["bundle"])
    summary = RunSummary.model_validate_json((bundle / "run.json").read_text())
    changed = summary.model_copy(
        update={
            "run_id": "other-run",
            "lock": summary.lock.model_copy(
                update={"subject": summary.lock.subject.model_copy(update={"version": "9"})}
            ),
        }
    )
    other = FileArtifactStore(results).persist(changed)
    code, _, error = _invoke(["run", "compare", bundle.name, other.name, "--results", str(results)])
    assert code == 2
    assert "subject identity differs" in error
    code, output, _ = _invoke(["run", "show", bundle.name, "--results", str(results)])
    assert code == 0
    shown = json.loads(output)
    assert shown["cases"][0]["pass_at_k"] == 1
    assert shown["cases"][0]["trials"] == 1


def test_score_writes_beside_the_sealed_bundle(tmp_path: Path) -> None:
    pack = tmp_path / "example-pack"
    results = tmp_path / "results"
    assert _invoke(["pack", "init", str(pack)])[0] == 0
    code, output, _ = _invoke(["run", str(pack), "--subject", "toy", "--results", str(results)])
    assert code == 0
    bundle = Path(json.loads(output)["bundle"])
    trial = next((bundle / "trials").iterdir())
    before = trial.read_bytes()
    seal = (bundle / "seal.json").read_bytes()
    code, output, _ = _invoke(["run", "score", bundle.name, "--results", str(results)])
    assert code == 0
    report = json.loads(output)
    assert report["passed"] is True
    assert Path(report["regrade"]).is_file()
    assert not str(report["regrade"]).startswith(str(bundle) + "/")
    assert trial.read_bytes() == before
    assert (bundle / "seal.json").read_bytes() == seal
    assert verify_bundle(bundle) == []
    regrade = json.loads(Path(report["regrade"]).read_text())
    assert regrade["schema"] == "circumstances.regrade.v1"
    assert regrade["evaluator_versions"]["outcome.state"] == "1"
    assert regrade["bundle_seal"] == hashlib.sha256(seal).hexdigest()


def test_untrusted_ref_requires_a_digest(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["pack", "add", "https://example.com/pack.tar.gz"]) == 2
    assert "require --digest" in capsys.readouterr().err


def test_project_source_adds_a_local_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pack = tmp_path / "demo"
    assert main(["pack", "init", str(pack)]) == 0
    capsys.readouterr()
    (tmp_path / "circumstances.yaml").write_text(
        yaml.safe_dump({"sources": [{"name": "partner/demo", "ref": "demo", "trust": "local"}]})
    )
    monkeypatch.chdir(tmp_path)
    assert main(["pack", "add", "partner/demo"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["digest"] == hash_directory(pack)
    assert added["trust"] == "local"


def test_pack_list_reads_the_cache_and_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    entry = cache / "abc"
    (entry / "pack").mkdir(parents=True)
    (entry / "resolved.json").write_text(
        json.dumps(
            {
                "source": "https://example.com/pack.tar.gz",
                "digest": "a" * 64,
                "revision": "rev",
            }
        )
    )
    monkeypatch.setattr(
        "circumstances.cli._policy",
        lambda: ResolverPolicy(cache_root=cache),
    )
    assert cached_packs(ResolverPolicy(cache_root=cache))[0]["revision"] == "rev"
    assert main(["pack", "list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["cached"][0]["source"] == "https://example.com/pack.tar.gz"
    assert any(item["name"] == "aenima/grounding" for item in listed["known"])


def test_subjects_come_from_the_registry(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["subjects"]) == 0
    payload = json.loads(capsys.readouterr().out)
    ids = {item["id"] for item in payload["subjects"]}
    assert {"toy", "openai-compatible"} <= ids


def test_view_serves_bundles_and_refuses_a_bad_lock(tmp_path: Path) -> None:
    pack = tmp_path / "example-pack"
    results = tmp_path / "results"
    assert _invoke(["pack", "init", str(pack)])[0] == 0
    code, output, _ = _invoke(["run", str(pack), "--subject", "toy", "--results", str(results)])
    assert code == 0
    bundle = Path(json.loads(output)["bundle"])
    summary = RunSummary.model_validate_json((bundle / "run.json").read_text())
    changed = summary.model_copy(
        update={
            "run_id": "second-run",
            "lock": summary.lock.model_copy(
                update={"models": {"subject": "other-model"}},
            ),
        }
    )
    FileArtifactStore(results).persist(changed)
    server = make_server(results, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/") as page:
            assert b"Circumstances" in page.read()
        with urlopen(f"http://127.0.0.1:{port}/api/runs") as listed:
            body = json.loads(listed.read())
        assert {item["run_id"] for item in body["runs"]} == {summary.run_id, "second-run"}
        with urlopen(f"http://127.0.0.1:{port}/api/runs/{summary.run_id}") as detail:
            shown = json.loads(detail.read())
        assert shown["cases"][0]["attempts"][0]["grades"]
        try:
            urlopen(f"http://127.0.0.1:{port}/api/compare?a={summary.run_id}&b=second-run")
        except Exception as exc:
            assert getattr(exc, "code", None) == 409
        else:
            raise AssertionError("incompatible compare was accepted")
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_view_refuses_a_public_host(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["view", "--host", "0.0.0.0", str(tmp_path)]) == 2
    assert "loopback" in capsys.readouterr().err


def _invoke(argv: list[str]) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _write_pack(path: Path, pack_id: str) -> None:
    path.mkdir(parents=True)
    (path / "pack.yaml").write_text(f"id: {pack_id}\n")
