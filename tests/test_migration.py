from pathlib import Path

import yaml

from circumstances.migration import migrate_gears_v3
from circumstances.pack import load_pack


def test_gears_v3_migration_moves_product_fixture_out_of_core(tmp_path: Path) -> None:
    source = tmp_path / "gears"
    write(
        source / "pack.yaml",
        {
            "schema_version": 3,
            "id": "private",
            "version": "1.0.0",
            "family": "safety",
            "maturity": "regression",
            "description": "Private",
            "owners": ["Owner"],
            "license": "LicenseRef-Private",
        },
    )
    write(
        source / "rules" / "rule" / "rule.yaml",
        {"title": "Rule", "description": "Description"},
    )
    write(
        source / "rules" / "rule" / "cases" / "case" / "case.yaml",
        {
            "memorome": "private-fixture",
            "turns": [{"user": "hello"}],
            "graders": [
                {
                    "id": "fast",
                    "match": [{"contains_any": ["hello"]}],
                }
            ],
        },
    )
    destination = tmp_path / "circumstances"

    migrate_gears_v3(source, destination)
    pack = load_pack(destination)

    case = pack.case("rule/case")
    assert case.fixture.type == "kodama.memorome"
    assert case.fixture.config["memorome"] == "private-fixture"
    assert case.evaluators[0].tier == "smoke"


def write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False))

