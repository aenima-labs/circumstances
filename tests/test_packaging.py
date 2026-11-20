"""The `circs` alias on PyPI must stay in lockstep with `circumstances`."""

import sys
import tomllib
from pathlib import Path

import pytest

import circumstances
from circumstances import cli

ROOT = Path(__file__).resolve().parents[1]


def _project(path: Path) -> dict[str, object]:
    project: dict[str, object] = tomllib.loads(path.read_text())["project"]
    return project


def test_circs_alias_pins_the_current_version() -> None:
    main = _project(ROOT / "pyproject.toml")
    alias = _project(ROOT / "packaging" / "circs" / "pyproject.toml")
    version = circumstances.__version__
    assert alias["version"] == version
    assert alias["dependencies"] == [f"circumstances=={version}"]
    extras = main["optional-dependencies"]
    assert isinstance(extras, dict)
    for extra in ("http", "server"):
        assert extra in extras
    assert alias["optional-dependencies"] == {
        extra: [f"circumstances[{extra}]=={version}"] for extra in ("http", "server")
    }
    assert alias["requires-python"] == main["requires-python"]


def test_both_packages_ship_the_same_commands() -> None:
    main = _project(ROOT / "pyproject.toml")
    alias = _project(ROOT / "packaging" / "circs" / "pyproject.toml")
    assert main["scripts"] == {
        "circumstances": "circumstances.cli:main",
        "circs": "circumstances.cli:main",
    }
    assert alias["scripts"] == {"circs": "circumstances.cli:main"}


@pytest.mark.parametrize(
    ("argv0", "prog"),
    [
        ("/usr/local/bin/circs", "circs"),
        ("circs.exe", "circs"),
        ("/usr/local/bin/circumstances", "circumstances"),
        ("-m", "circumstances"),
    ],
)
def test_help_names_the_command_as_typed(
    monkeypatch: pytest.MonkeyPatch, argv0: str, prog: str
) -> None:
    monkeypatch.setattr(sys, "argv", [argv0])
    assert cli._parser().prog == prog


def test_version_comes_from_the_package(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert capsys.readouterr().out.strip() == f"circumstances {circumstances.__version__}"
