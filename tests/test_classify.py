"""Tests for stage 2 (classify)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exitplaybook.classify import ClassifyError, classify, load_tags, validate_classified
from exitplaybook.classify.cli import main
from exitplaybook.inventory import build_inventory, write_inventory

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
TAGS = SAMPLES / "app_tags.csv"
FIXED_TIME = datetime(2026, 10, 17, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def inventory_path(tmp_path):
    inv = build_inventory(SAMPLES / "rvtools_vinfo_sample.csv", generated_at=FIXED_TIME)
    return write_inventory(inv, tmp_path / "inventory.json")


@pytest.fixture
def legacy_inventory_path(tmp_path):
    inv = build_inventory(SAMPLES / "rvtools_vinfo_legacy.csv", generated_at=FIXED_TIME)
    return write_inventory(inv, tmp_path / "legacy_inventory.json")


@pytest.fixture
def result(inventory_path):
    return classify(inventory_path, TAGS, generated_at=FIXED_TIME)


def vm(result, name):
    return next(v for v in result["vms"] if v["vm_name"] == name)


# ---------- each rule ----------

def test_owner_decision_wins_over_everything(result):
    v = vm(result, "erp-app01")
    assert (v["strategy"], v["rule"], v["confidence"]) == ("repurchase", "owner-decision", "high")
    assert "SaaS ERP" in v["reasons"][0]


def test_owner_can_choose_to_retain(result):
    assert vm(result, "infra-ad01")["strategy"] == "retain"


def test_incomplete_data_is_retained_for_review(result):
    v = vm(result, "infra-appliance01")
    assert (v["strategy"], v["rule"], v["needs_review"]) == ("retain", "incomplete-data", True)


def test_template_is_retired_and_rebuilt(result):
    v = vm(result, "tpl-rhel8-golden")
    assert (v["strategy"], v["rule"], v["needs_review"]) == ("retire", "template", False)


def test_powered_off_and_suspended_are_retire_candidates(result):
    for name in ("rpt-legacy01", "erp-dev01"):
        v = vm(result, name)
        assert (v["strategy"], v["rule"], v["needs_review"]) == ("retire", "not-running", True)


def test_unknown_os_is_retained_for_review(result):
    v = vm(result, "infra-fs01")
    assert (v["strategy"], v["rule"], v["confidence"]) == ("retain", "unknown-os", "low")


def test_end_of_life_os_is_replatformed(legacy_inventory_path):
    r = classify(legacy_inventory_path, generated_at=FIXED_TIME)
    v = vm(r, "img-archive01")
    assert (v["strategy"], v["rule"]) == ("replatform", "end-of-life-os")
    assert "Red Hat Enterprise Linux 7" in v["reasons"][0]


def test_database_name_is_replatformed(result):
    v = vm(result, "pay-db01")
    assert (v["strategy"], v["rule"]) == ("replatform", "database")


def test_default_is_rehost(result):
    v = vm(result, "web-portal01")
    assert (v["strategy"], v["rule"], v["confidence"], v["needs_review"]) == \
        ("rehost", "default", "high", False)


def test_rule_order_not_running_beats_end_of_life(result):
    # rpt-legacy01 is powered off AND on Windows Server 2012 R2:
    # the earlier rule (not-running) must decide.
    assert vm(result, "rpt-legacy01")["rule"] == "not-running"


# ---------- environment and tags ----------

def test_environment_from_tag(result):
    v = vm(result, "pay-api01")
    assert (v["environment"], v["environment_source"]) == ("prod", "tag")


def test_environment_inferred_from_folder(result):
    v = vm(result, "pay-api01-stg")
    assert (v["environment"], v["environment_source"]) == ("stage", "folder")


def test_environment_unknown_when_nothing_matches(result):
    v = vm(result, "infra-fs01")
    assert (v["environment"], v["environment_source"]) == ("unknown", "none")


def test_tags_fill_application_owner_and_criticality(result):
    v = vm(result, "pay-db01")
    assert v["application"] == "Payments API"
    assert v["criticality"] == "tier1"
    assert v["owner"] == "Payments Team"


def test_runs_without_tags(inventory_path):
    r = classify(inventory_path, generated_at=FIXED_TIME)
    assert r["inputs"]["tags"] is None
    assert vm(r, "erp-app01")["strategy"] == "rehost"
    validate_classified(r)


def test_invalid_tag_value_is_rejected(tmp_path):
    bad = tmp_path / "tags.csv"
    bad.write_text("vm_name,decision\nvm1,move-it\n", encoding="utf-8")
    with pytest.raises(ClassifyError, match="decision 'move-it' is not one of"):
        load_tags(bad)


def test_tags_for_unknown_vms_are_rejected(inventory_path, tmp_path):
    bad = tmp_path / "tags.csv"
    bad.write_text("vm_name,environment\nghost-vm,prod\n", encoding="utf-8")
    with pytest.raises(ClassifyError, match="not in the inventory: ghost-vm"):
        classify(inventory_path, bad)


# ---------- contract ----------

def test_invalid_inventory_is_rejected(tmp_path):
    bad = tmp_path / "inventory.json"
    bad.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
    with pytest.raises(ClassifyError, match="Input inventory is not valid"):
        classify(bad)


def test_output_matches_schema(result):
    validate_classified(result)


def test_every_vm_is_classified_once(result):
    assert result["summary"]["total_vms"] == 12
    assert sum(result["summary"]["by_strategy"].values()) == 12
    assert len({v["vm_id"] for v in result["vms"]}) == 12


def test_summary_counts(result):
    assert result["summary"]["by_strategy"] == {
        "retire": 3, "retain": 3, "rehost": 4, "replatform": 1, "repurchase": 1,
    }
    assert result["summary"]["needs_review"] == 4


def test_same_input_gives_same_output(inventory_path):
    a = classify(inventory_path, TAGS, generated_at=FIXED_TIME)
    b = classify(inventory_path, TAGS, generated_at=FIXED_TIME)
    assert a == b


# ---------- CLI ----------

def test_cli_end_to_end(inventory_path, tmp_path, capsys):
    out = tmp_path / "classified.json"
    code = main(["--inventory", str(inventory_path), "--tags", str(TAGS), "--output", str(out)])
    assert code == 0 and out.exists()
    assert "Needs review: 4" in capsys.readouterr().out


def test_cli_reports_errors_without_traceback(tmp_path, capsys):
    assert main(["--inventory", str(tmp_path / "missing.json")]) == 1
    assert "ERROR: Input inventory is not valid" in capsys.readouterr().err
