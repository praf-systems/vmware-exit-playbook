"""Command line for stage 2.

Example:
    exitplaybook-classify --inventory runs/inventory.json --tags samples/app_tags.csv \\
        --output runs/classified.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import (
    DEFAULT_RULES,
    DEFAULT_SCHEMA,
    ClassifyError,
    classify,
    validate_classified,
    write_classified,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stage 2: inventory.json to classified.json")
    p.add_argument("--inventory", required=True, type=Path, help="output of stage 1")
    p.add_argument("--tags", type=Path, default=None, help="optional application tags CSV")
    p.add_argument("--output", default=Path("runs/classified.json"), type=Path)
    p.add_argument("--rules", default=DEFAULT_RULES, type=Path, help="rule parameters YAML")
    p.add_argument("--schema", default=DEFAULT_SCHEMA, type=Path, help="classified JSON Schema")
    args = p.parse_args(argv)

    try:
        data = classify(args.inventory, args.tags, args.rules)
        validate_classified(data, args.schema)
    except ClassifyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = write_classified(data, args.output)
    s = data["summary"]
    mix = ", ".join(f"{k} {v}" for k, v in s["by_strategy"].items())
    print(f"Wrote {out}")
    print(f"  VMs: {s['total_vms']}  ({mix})")
    print(f"  Needs review: {s['needs_review']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
