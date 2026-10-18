"""Tests for stage 1 (inventory)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from exitplaybook.inventory import InventoryError, build_inventory, validate_inventory
from exitplaybook.inventory.cli import main
from exitplaybook.inventory.parser import load_column_config, resolve_columns, unit_factor

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "rvtools_vinfo_sample.csv"
LEGACY = ROOT / "samples" / "rvtools_vinfo_legacy.csv"
FIXED_TIME = datetime(2026, 10, 17, 9, 0, tzinfo=timezone.utc)


def by_name(inventory, name):
    return next(v for v in inventory["vms"] if v["vm_name"] == name)


@pytest.fixture
def inventory():
    return build_inventory(SAMPLE, generated_at=FIXED_TIME)


# ---------- column mapping ----------

def test_current_columns_are_mapped(inventory):
    cmap = inventory["source"]["column_map"]
    assert cmap["power_state"] == "Powerstate"
    assert cmap["provisioned"] == "Provisioned MiB"
    assert cmap["os"] == "OS according to the configuration file"


def test_legacy_columns_are_mapped():
    inv = build_inventory(LEGACY, generated_at=FIXED_TIME)
    cmap = inv["source"]["column_map"]
    assert cmap["power_state"] == "Power State"
    assert cmap["memory"] == "Memory MB"
    assert cmap["os"] == "OS according to the VMware Tools"
    validate_inventory(inv)


def test_missing_required_column_gives_clear_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("VM,CPUs\nvm1,2\n", encoding="utf-8")
    with pytest.raises(InventoryError, match="Missing required columns: power_state"):
        build_inventory(bad)


def test_column_matching_ignores_case_and_spacing():
    config = load_column_config()
    header = ["vm", "POWERSTATE", "cpus", "memory", "provisioned  mib"]
    cmap = resolve_columns(header, config)
    assert cmap["vm_name"] == "vm"
    assert cmap["provisioned"] == "provisioned  mib"


# ---------- unit normalization ----------

@pytest.mark.parametrize("column,expected", [
    ("Provisioned MiB", 1 / 1024), ("Provisioned MB", 1 / 1024),
    ("Provisioned GiB", 1.0), ("Provisioned GB", 1.0),
])
def test_unit_factor(column, expected):
    assert unit_factor(column, None) == expected


def test_memory_without_unit_uses_default_mib(inventory):
    assert by_name(inventory, "pay-api01")["memory_gib"] == 32.0


def test_sizes_are_converted_to_gib(inventory):
    vm = by_name(inventory, "pay-db01")
    assert vm["provisioned_gib"] == 2048.0
    assert vm["memory_gib"] == 128.0


def test_comma_formatted_numbers_are_parsed(inventory):
    assert by_name(inventory, "infra-fs01")["provisioned_gib"] == 1024.0


def test_legacy_mb_columns_convert_like_mib():
    inv = build_inventory(LEGACY, generated_at=FIXED_TIME)
    assert by_name(inv, "img-archive01")["provisioned_gib"] == 1000.0


# ---------- flags ----------

def test_template_is_flagged(inventory):
    vm = by_name(inventory, "tpl-rhel8-golden")
    assert vm["is_template"] is True
    assert {"template", "powered_off"} <= set(vm["flags"])


def test_powered_off_and_suspended_are_flagged(inventory):
    assert "powered_off" in by_name(inventory, "rpt-legacy01")["flags"]
    assert "suspended" in by_name(inventory, "erp-dev01")["flags"]


def test_missing_os_is_flagged(inventory):
    vm = by_name(inventory, "infra-fs01")
    assert vm["os"] is None
    assert "missing_os" in vm["flags"]


def test_zero_disk_is_flagged(inventory):
    assert "zero_disk" in by_name(inventory, "infra-appliance01")["flags"]


def test_clean_vm_has_no_flags(inventory):
    assert by_name(inventory, "pay-api01")["flags"] == []


# ---------- identity and traceability ----------

def test_missing_uuid_gets_stable_generated_id():
    a = build_inventory(LEGACY, generated_at=FIXED_TIME)
    b = build_inventory(LEGACY, generated_at=FIXED_TIME)
    vm = by_name(a, "crm-db01")
    assert vm["vm_id"].startswith("gen-")
    assert "generated_id" in vm["flags"]
    assert vm["vm_id"] == by_name(b, "crm-db01")["vm_id"]


def test_duplicate_ids_are_rejected(tmp_path):
    dup = tmp_path / "dup.csv"
    dup.write_text(
        "VM,Powerstate,CPUs,Memory,Provisioned MiB,VM UUID\n"
        "a,poweredOn,2,4096,1024,same-id\n"
        "b,poweredOn,2,4096,1024,same-id\n",
        encoding="utf-8",
    )
    with pytest.raises(InventoryError, match="Duplicate VM id 'same-id'"):
        build_inventory(dup)


def test_source_row_points_back_to_the_file(inventory):
    assert by_name(inventory, "pay-api01")["source_row"] == 2


# ---------- contract and determinism ----------

def test_output_matches_schema(inventory):
    validate_inventory(inventory)


def test_summary_totals(inventory):
    s = inventory["summary"]
    assert s["total_vms"] == 12
    assert s["templates"] == 1
    assert s["powered_off"] == 3
    assert s["total_vcpus"] == sum(v["cpus"] for v in inventory["vms"])


def test_same_input_gives_same_output():
    assert build_inventory(SAMPLE, generated_at=FIXED_TIME) == \
        build_inventory(SAMPLE, generated_at=FIXED_TIME)


def test_schema_rejects_broken_records(inventory):
    inventory["vms"][0]["cpus"] = -1
    with pytest.raises(InventoryError, match="schema validation"):
        validate_inventory(inventory)


# ---------- file formats and CLI ----------

def test_xlsx_with_vinfo_sheet(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "vInfo"
    ws.append(["VM", "Powerstate", "CPUs", "Memory", "Provisioned MiB", "VM UUID"])
    ws.append(["xl-vm01", "poweredOn", 2, 4096, 20480, "xl-0001"])
    path = tmp_path / "export.xlsx"
    wb.save(path)
    inv = build_inventory(path, generated_at=FIXED_TIME)
    assert inv["source"]["format"] == "xlsx"
    assert inv["vms"][0]["provisioned_gib"] == 20.0
    validate_inventory(inv)


def test_cli_writes_inventory(tmp_path, capsys):
    out = tmp_path / "inventory.json"
    assert main(["--input", str(SAMPLE), "--output", str(out)]) == 0
    assert out.exists()
    assert "VMs: 12" in capsys.readouterr().out


def test_cli_reports_errors_without_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("VM\nvm1\n", encoding="utf-8")
    assert main(["--input", str(bad), "--output", str(tmp_path / "x.json")]) == 1
    assert "ERROR: Missing required columns" in capsys.readouterr().err


# ---------- PowerCLI export ----------

def test_powercli_export_is_accepted():
    inv = build_inventory(ROOT / "samples" / "powercli_export_sample.csv", generated_at=FIXED_TIME)
    validate_inventory(inv)
    assert inv["source"]["column_map"]["provisioned"] == "Provisioned GB"
    batch = by_name(inv, "app-batch01")
    assert (batch["power_state"], batch["memory_gib"], batch["provisioned_gib"]) == \
        ("poweredOn", 16.0, 200.0)
    tpl = by_name(inv, "tpl-win2022-golden")
    assert tpl["is_template"] and tpl["datacenter"] is None


# ---------- snapshots and mounted media ----------

SNAPS = ROOT / "samples" / "rvtools_vsnapshot_sample.csv"
CDS = ROOT / "samples" / "rvtools_vcd_sample.csv"


@pytest.fixture
def with_sheets():
    return build_inventory(SAMPLE, generated_at=FIXED_TIME, snapshots=SNAPS, cd=CDS)


def test_snapshots_are_flagged(with_sheets):
    assert "snapshot" in by_name(with_sheets, "pay-api01-stg")["flags"]
    assert "snapshot" in by_name(with_sheets, "rpt-legacy01")["flags"]
    assert "snapshot" not in by_name(with_sheets, "pay-api01")["flags"]


def test_only_connected_media_is_flagged(with_sheets):
    assert "connected_media" in by_name(with_sheets, "web-portal02")["flags"]
    # pay-api01 has a CD drive, but nothing is connected to it.
    assert "connected_media" not in by_name(with_sheets, "pay-api01")["flags"]


def test_extra_sheet_rows_are_counted(with_sheets):
    sheets = with_sheets["source"]["extra_sheets"]
    assert sheets["vSnapshot"] == {"rows": 3, "matched": 2}
    assert sheets["vCD"] == {"rows": 2, "matched": 2}
    validate_inventory(with_sheets)


def test_csv_without_extra_sheets_still_works(inventory):
    assert inventory["source"]["extra_sheets"] == {}
    assert not any({"snapshot", "connected_media"} & set(v["flags"]) for v in inventory["vms"])


def test_extra_sheets_match_by_name_when_there_is_no_uuid(tmp_path):
    snaps = tmp_path / "snaps.csv"
    snaps.write_text("VM,Name\nimg-archive01,pre-patch\n", encoding="utf-8")
    inv = build_inventory(LEGACY, generated_at=FIXED_TIME, snapshots=snaps)
    assert "snapshot" in by_name(inv, "img-archive01")["flags"]
    assert "snapshot" not in by_name(inv, "crm-db01")["flags"]


def test_xlsx_reads_extra_sheets_automatically(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    info = wb.active
    info.title = "vInfo"
    info.append(["VM", "Powerstate", "CPUs", "Memory", "Provisioned MiB", "VM UUID"])
    info.append(["xl-vm01", "poweredOn", 2, 4096, 20480, "xl-0001"])
    info.append(["xl-vm02", "poweredOn", 2, 4096, 20480, "xl-0002"])
    snap = wb.create_sheet("vSnapshot")
    snap.append(["VM", "Name", "VM UUID"])
    snap.append(["xl-vm01", "snap1", "xl-0001"])
    cd = wb.create_sheet("vCD")
    cd.append(["VM", "Connected", "VM UUID"])
    cd.append(["xl-vm02", True, "xl-0002"])
    path = tmp_path / "export.xlsx"
    wb.save(path)
    inv = build_inventory(path, generated_at=FIXED_TIME)
    assert "snapshot" in by_name(inv, "xl-vm01")["flags"]
    assert "connected_media" in by_name(inv, "xl-vm02")["flags"]
    validate_inventory(inv)


def test_cli_accepts_extra_sheets(tmp_path):
    out = tmp_path / "inventory.json"
    code = main(["--input", str(SAMPLE), "--snapshots", str(SNAPS), "--cd", str(CDS),
                 "--output", str(out)])
    assert code == 0 and "connected_media" in out.read_text()
