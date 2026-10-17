"""Command line for stage 1.

Example:
    exitplaybook-inventory --input samples/rvtools_vinfo_sample.csv --output runs/inventory.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import (
    DEFAULT_COLUMNS,
    DEFAULT_SCHEMA,
    InventoryError,
    build_inventory,
    validate_inventory,
    write_inventory,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 1: RVTools export to inventory.json")
    p.add_argument("--input", required=True, type=Path, help="RVTools vInfo export (.csv or .xlsx)")
    p.add_argument("--output", default=Path("runs/inventory.json"), type=Path)
    p.add_argument("--columns", default=DEFAULT_COLUMNS, type=Path, help="column mapping YAML")
    p.add_argument("--schema", default=DEFAULT_SCHEMA, type=Path, help="inventory JSON Schema")
    args = p.parse_args(argv)

    try:
        inventory = build_inventory(args.input, args.columns)
        validate_inventory(inventory, args.schema)
    except InventoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = write_inventory(inventory, args.output)
    s = inventory["summary"]
    print(f"Wrote {out}")
    print(f"  VMs: {s['total_vms']}  (on {s['powered_on']}, off {s['powered_off']}, "
          f"templates {s['templates']}, flagged {s['flagged']})")
    print(f"  vCPUs: {s['total_vcpus']}  memory: {s['total_memory_gib']} GiB  "
          f"provisioned: {s['total_provisioned_gib']} GiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
