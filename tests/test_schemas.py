"""Checks that apply to every schema in schemas/."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMAS = sorted((Path(__file__).resolve().parents[1] / "schemas").glob("*.schema.json"))


def test_schemas_exist():
    assert SCHEMAS, "no schemas found"


@pytest.mark.parametrize("path", SCHEMAS, ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("path", SCHEMAS, ids=lambda p: p.name)
def test_schema_declares_version_and_id(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("/2020-12/schema")
    assert schema["$id"].endswith(path.name)
    assert schema["properties"]["schema_version"]["const"]
