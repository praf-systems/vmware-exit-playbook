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

def read_table(path: Path) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Return (format, header, rows) for a CSV or XLSX file."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return "csv", list(reader.fieldnames or []), rows
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb["vInfo"] if "vInfo" in wb.sheetnames else wb.active
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


# ---------- building ----------

def build_inventory(
    source: Path,
    columns_path: Path = DEFAULT_COLUMNS,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Turn an RVTools export into an inventory dictionary (not yet validated)."""
    source = Path(source)
    fmt, header, rows = read_table(source)
    config = load_column_config(columns_path)
    column_map = resolve_columns(header, config)
    factors = {
        f: unit_factor(column_map[f], config[f].get("default_unit"))
        for f in SIZE_FIELDS if f in column_map
    }

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

    when = (generated_at or datetime.now(timezone.utc)).replace(microsecond=0)
    return {
        "schema_version": "1.0",
        "generated_at": when.isoformat().replace("+00:00", "Z"),
        "source": {"file": source.name, "format": fmt, "column_map": column_map},
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
