"""Stage 1: inventory.

Reads an RVTools vInfo export (CSV or XLSX), maps version-specific column
names to the inventory schema, normalizes sizes to GiB, flags edge cases
and validates the result against schemas/inventory.schema.json.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from exitplaybook.paths import CONFIG_DIR, SCHEMAS_DIR

DEFAULT_COLUMNS = CONFIG_DIR / "rvtools_columns.yaml"
DEFAULT_EXTRA_SHEETS = CONFIG_DIR / "rvtools_extra_sheets.yaml"
DEFAULT_SCHEMA = SCHEMAS_DIR / "inventory.schema.json"

# Size units: factor that converts a value in that unit to GiB.
# RVTools labels some columns "MB" although the values are MiB, so both map the same way.
UNIT_TO_GIB = {"mib": 1 / 1024, "mb": 1 / 1024, "gib": 1.0, "gb": 1.0}
SIZE_FIELDS = ("memory", "provisioned", "in_use")

POWER_STATES = {
    "poweredon": "poweredOn", "on": "poweredOn",
    "poweredoff": "poweredOff", "off": "poweredOff",
    "suspended": "suspended",
}
TRUE_VALUES = {"true", "yes", "1", "y"}


class InventoryError(ValueError):
    """Raised when the source file cannot be turned into a valid inventory."""


# ---------- reading ----------

def read_table(path: Path, sheet: str = "vInfo") -> tuple[str, list[str], list[dict[str, Any]]]:
    """Return (format, header, rows) for a CSV file or one sheet of an XLSX file.

    For XLSX, the named sheet is used if present; for vInfo, the first sheet is the fallback.
    """
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return "csv", list(reader.fieldnames or []), rows
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        if sheet in wb.sheetnames:
            ws = wb[sheet]
        elif sheet == "vInfo":
            ws = wb.active
        else:
            return "xlsx", [], []
        it = ws.iter_rows(values_only=True)
        header = [str(c).strip() if c is not None else "" for c in next(it, [])]
        rows = [dict(zip(header, r, strict=False)) for r in it if any(v is not None for v in r)]
        return "xlsx", header, rows
    raise InventoryError(f"Unsupported file type '{suffix}'. Use .csv or .xlsx.")


# ---------- column mapping ----------

def _key(name: str) -> str:
    return re.sub(r"\s+", " ", str(name)).strip().lower()


def load_column_config(path: Path = DEFAULT_COLUMNS) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_columns(header: list[str], config: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Map each schema field to the first matching source column."""
    available = {_key(h): h for h in header if h}
    column_map, missing = {}, []
    for field, spec in config.items():
        match = next((available[_key(a)] for a in spec["aliases"] if _key(a) in available), None)
        if match:
            column_map[field] = match
        elif spec.get("required"):
            missing.append(f"{field} (tried: {', '.join(spec['aliases'])})")
    if missing:
        raise InventoryError("Missing required columns: " + "; ".join(missing))
    return column_map


def unit_factor(column: str, default_unit: str | None) -> float:
    """Read the size unit from a column name such as 'Provisioned MiB'."""
    m = re.search(r"\b(MiB|MB|GiB|GB)\b", column, re.IGNORECASE)
    unit = (m.group(1) if m else default_unit or "").lower()
    if unit not in UNIT_TO_GIB:
        raise InventoryError(f"Cannot determine size unit for column '{column}'.")
    return UNIT_TO_GIB[unit]


# ---------- value parsing ----------

def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _number(value: Any, field: str, row: int) -> float | None:
    s = _text(value)
    if s is None:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError as exc:
        raise InventoryError(f"Row {row}: '{field}' is not a number: {s!r}") from exc


def _power_state(value: Any) -> str:
    return POWER_STATES.get((_text(value) or "").replace(" ", "").lower(), "unknown")


def _generated_id(name: str, datacenter: str | None, cluster: str | None) -> str:
    digest = hashlib.sha1(f"{name}|{datacenter}|{cluster}".encode()).hexdigest()[:12]
    return f"gen-{digest}"


# ---------- extra sheets (snapshots, mounted media) ----------

def _first_column(header: list[str], aliases: list[str]) -> str | None:
    available = {_key(h): h for h in header if h}
    return next((available[_key(a)] for a in aliases if _key(a) in available), None)


def read_extra_sheet(
    path: Path | None, sheet: str, spec: dict[str, list[str]]
) -> tuple[list[dict[str, Any]], int]:
    """Read one extra RVTools sheet into simple records: vm_name, vm_id and the sheet's fields.

    Returns (records, row_count). A missing file or sheet gives no records.
    """
    if path is None:
        return [], 0
    _, header, rows = read_table(Path(path), sheet)
    if not rows:
        return [], 0
    cols = {field: _first_column(header, aliases) for field, aliases in spec.items()}
    if cols.get("vm_name") is None:
        raise InventoryError(f"{sheet}: no VM name column (tried: {', '.join(spec['vm_name'])}).")
    records = []
    for row in rows:
        name = _text(row.get(cols["vm_name"]))
        if name is None:
            continue
        rec = {field: _text(row.get(col)) if col else None for field, col in cols.items()}
        rec["vm_name"] = name
        records.append(rec)
    return records, len(records)


def _index_by_vm(records: list[dict[str, Any]], keep) -> tuple[set[str], set[str]]:
    """Return the VM ids and names for which at least one record passes `keep`."""
    ids, names = set(), set()
    for rec in records:
        if keep(rec):
            if rec.get("vm_id"):
                ids.add(rec["vm_id"])
            names.add(rec["vm_name"])
    return ids, names


def _matches(vm_id: str, vm_name: str, ids: set[str], names: set[str], use_ids: bool) -> bool:
    return vm_id in ids if use_ids else vm_name in names


# ---------- building ----------

def build_inventory(
    source: Path,
    columns_path: Path = DEFAULT_COLUMNS,
    generated_at: datetime | None = None,
    snapshots: Path | None = None,
    cd: Path | None = None,
    extra_sheets_path: Path = DEFAULT_EXTRA_SHEETS,
) -> dict[str, Any]:
    """Turn an RVTools export into an inventory dictionary (not yet validated).

    For an .xlsx export, the vSnapshot and vCD sheets are read automatically unless
    separate files are given. For CSV exports, pass those sheets as `snapshots` and `cd`.
    """
    source = Path(source)
    fmt, header, rows = read_table(source)
    config = load_column_config(columns_path)
    column_map = resolve_columns(header, config)
    factors = {
        f: unit_factor(column_map[f], config[f].get("default_unit"))
        for f in SIZE_FIELDS if f in column_map
    }

    with Path(extra_sheets_path).open(encoding="utf-8") as f:
        extra_spec = yaml.safe_load(f)
    snap_src = snapshots if snapshots is not None else (source if fmt == "xlsx" else None)
    cd_src = cd if cd is not None else (source if fmt == "xlsx" else None)
    snap_records, snap_rows = read_extra_sheet(snap_src, "vSnapshot", extra_spec["vSnapshot"])
    cd_records, cd_rows = read_extra_sheet(cd_src, "vCD", extra_spec["vCD"])
    snap_ids, snap_names = _index_by_vm(snap_records, lambda r: True)
    cd_ids, cd_names = _index_by_vm(
        cd_records, lambda r: (r.get("connected") or "").lower() in TRUE_VALUES
    )

    def get(row: dict[str, Any], field: str) -> Any:
        col = column_map.get(field)
        return row.get(col) if col else None

    vms, seen_ids = [], {}
    for index, row in enumerate(rows):
        row_no = index + 2  # row 1 is the header
        name = _text(get(row, "vm_name"))
        if name is None:
            continue  # blank line or footer
        dc, cluster = _text(get(row, "datacenter")), _text(get(row, "cluster"))
        flags = []

        vm_id = _text(get(row, "vm_id"))
        if vm_id is None:
            vm_id = _generated_id(name, dc, cluster)
            flags.append("generated_id")
        if vm_id in seen_ids:
            raise InventoryError(
                f"Duplicate VM id '{vm_id}' in rows {seen_ids[vm_id]} and {row_no}."
            )
        seen_ids[vm_id] = row_no

        def size(field: str, row: dict[str, Any] = row, row_no: int = row_no) -> float | None:
            raw = _number(get(row, field), field, row_no)
            return None if raw is None else round(raw * factors[field], 2)

        cpus = int(_number(get(row, "cpus"), "cpus", row_no) or 0)
        memory = size("memory") or 0.0
        provisioned = size("provisioned") or 0.0
        in_use = size("in_use") if "in_use" in factors else None
        power = _power_state(get(row, "power_state"))
        is_template = (_text(get(row, "is_template")) or "").lower() in TRUE_VALUES
        os_name = _text(get(row, "os"))

        if is_template:
            flags.append("template")
        if power == "poweredOff":
            flags.append("powered_off")
        if power == "suspended":
            flags.append("suspended")
        if os_name is None:
            flags.append("missing_os")
        if provisioned == 0:
            flags.append("zero_disk")
        if cpus == 0:
            flags.append("zero_cpu")
        # Match extra sheets by UUID when the VM has a real one, otherwise by name.
        use_ids = "generated_id" not in flags
        if _matches(vm_id, name, snap_ids, snap_names, use_ids and bool(snap_ids)):
            flags.append("snapshot")
        if _matches(vm_id, name, cd_ids, cd_names, use_ids and bool(cd_ids)):
            flags.append("connected_media")

        vms.append({
            "vm_id": vm_id,
            "vm_name": name,
            "power_state": power,
            "is_template": is_template,
            "cpus": cpus,
            "memory_gib": memory,
            "provisioned_gib": provisioned,
            "in_use_gib": in_use,
            "os": os_name,
            "datacenter": dc,
            "cluster": cluster,
            "host": _text(get(row, "host")),
            "folder": _text(get(row, "folder")),
            "flags": flags,
            "source_row": row_no,
        })

    def matched(records: list[dict[str, Any]]) -> int:
        ids = {v["vm_id"] for v in vms}
        names = {v["vm_name"] for v in vms}
        return sum(1 for r in records if r.get("vm_id") in ids or r["vm_name"] in names)

    extra_sheets = {}
    if snap_src is not None:
        extra_sheets["vSnapshot"] = {"rows": snap_rows, "matched": matched(snap_records)}
    if cd_src is not None:
        extra_sheets["vCD"] = {"rows": cd_rows, "matched": matched(cd_records)}

    when = (generated_at or datetime.now(timezone.utc)).replace(microsecond=0)
    return {
        "schema_version": "1.1",
        "generated_at": when.isoformat().replace("+00:00", "Z"),
        "source": {
            "file": source.name,
            "format": fmt,
            "column_map": column_map,
            "extra_sheets": extra_sheets,
        },
        "summary": _summarize(vms),
        "vms": vms,
    }


def _summarize(vms: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_vms": len(vms),
        "powered_on": sum(v["power_state"] == "poweredOn" for v in vms),
        "powered_off": sum(v["power_state"] == "poweredOff" for v in vms),
        "templates": sum(v["is_template"] for v in vms),
        "flagged": sum(bool(v["flags"]) for v in vms),
        "total_vcpus": sum(v["cpus"] for v in vms),
        "total_memory_gib": round(sum(v["memory_gib"] for v in vms), 2),
        "total_provisioned_gib": round(sum(v["provisioned_gib"] for v in vms), 2),
    }


# ---------- validation and output ----------

def validate_inventory(inventory: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA) -> None:
    """Raise InventoryError listing every schema violation."""
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(inventory), key=lambda e: list(e.path))
    if errors:
        lines = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:20]]
        raise InventoryError("Inventory failed schema validation:\n  " + "\n  ".join(lines))


def write_inventory(inventory: dict[str, Any], output: Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return output
