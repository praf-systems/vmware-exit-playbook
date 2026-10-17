"""Stage 2: classify.

Reads a validated inventory.json, optional application tags and the rule
parameters in config/classify_rules.yaml, and assigns each VM one of the
7R strategies with its reasons, a confidence level and a review flag.

Rules are applied in a fixed order; the first rule that matches decides:

  1. owner-decision    a tag sets the strategy explicitly
  2. incomplete-data   zero disk or zero vCPU      -> retain, review
  3. template          VM template                 -> retire (rebuild as a target image)
  4. not-running       powered off or suspended    -> retire, review
  5. unknown-os        no OS reported              -> retain, review
  6. end-of-life-os    OS past vendor support      -> replatform
  7. database          name suggests a database    -> replatform
  8. default           everything else             -> rehost

Rules can only infer retire, retain, rehost and replatform. Relocate,
repurchase and refactor are business decisions and come from tags.
See docs/adr/0002-rules-infer-four-of-seven-rs.md.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from exitplaybook.inventory import InventoryError, validate_inventory
from exitplaybook.paths import CONFIG_DIR, SCHEMAS_DIR

DEFAULT_RULES = CONFIG_DIR / "classify_rules.yaml"
DEFAULT_SCHEMA = SCHEMAS_DIR / "classified.schema.json"

STRATEGIES = ("retire", "retain", "rehost", "relocate", "replatform", "repurchase", "refactor")
ENVIRONMENTS = ("prod", "stage", "dev", "test", "dr")
CRITICALITIES = ("tier1", "tier2", "tier3")


class ClassifyError(ValueError):
    """Raised when inputs are invalid or the output breaks the schema."""


@dataclass(frozen=True)
class Decision:
    strategy: str
    rule: str
    reasons: list[str]
    confidence: str
    needs_review: bool


# ---------- inputs ----------

def load_rules(path: Path = DEFAULT_RULES) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    rules["_db"] = [re.compile(p, re.IGNORECASE) for p in rules.get("database_name_patterns", [])]
    rules["_env"] = {
        env: [re.compile(p, re.IGNORECASE) for p in patterns]
        for env, patterns in rules.get("environment_patterns", {}).items()
    }
    return rules


def load_tags(path: Path | None) -> dict[str, dict[str, str | None]]:
    """Read application tags keyed by VM name. Unknown values are rejected."""
    if path is None:
        return {}
    tags: dict[str, dict[str, str | None]] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        for row_no, row in enumerate(csv.DictReader(f), start=2):
            name = (row.get("vm_name") or "").strip()
            if not name:
                continue
            clean = {k: ((v or "").strip() or None) for k, v in row.items() if k}
            for field, allowed in (("environment", ENVIRONMENTS), ("criticality", CRITICALITIES),
                                   ("decision", STRATEGIES)):
                value = clean.get(field)
                if value is not None:
                    value = value.lower()
                    if value not in allowed:
                        raise ClassifyError(
                            f"Tags row {row_no}: {field} '{value}' is not one of "
                            f"{', '.join(allowed)}."
                        )
                    clean[field] = value
            if name in tags:
                raise ClassifyError(f"Tags row {row_no}: duplicate entry for VM '{name}'.")
            tags[name] = clean
    return tags


# ---------- rules ----------

def infer_environment(vm: dict[str, Any], tag: dict[str, Any], rules: dict[str, Any]) \
        -> tuple[str, str]:
    if tag.get("environment"):
        return tag["environment"], "tag"
    for source in ("folder", "name"):
        text = vm["folder"] if source == "folder" else vm["vm_name"]
        if not text:
            continue
        for env, patterns in rules["_env"].items():
            if any(p.search(text) for p in patterns):
                return env, source
    return "unknown", "none"


def decide(vm: dict[str, Any], tag: dict[str, Any], rules: dict[str, Any]) -> Decision:
    """Apply the rules in order; the first match decides."""
    flags = set(vm["flags"])

    if tag.get("decision"):
        note = tag.get("notes")
        reason = "Strategy set by the application owner" + (f": {note}" if note else ".")
        return Decision(tag["decision"], "owner-decision", [reason], "high", False)

    if flags & {"zero_disk", "zero_cpu"}:
        return Decision("retain", "incomplete-data",
                        ["Inventory shows no disk or no vCPU; confirm the record before planning."],
                        "low", True)

    if vm["is_template"]:
        return Decision("retire", "template",
                        ["VM template; rebuild it as a native image on the target "
                         "instead of migrating it."],
                        "high", False)

    if flags & {"powered_off", "suspended"}:
        state = "powered off" if "powered_off" in flags else "suspended"
        return Decision("retire", "not-running",
                        [f"VM is {state}; confirm with the owner whether it is still needed."],
                        "medium", True)

    os_name = vm["os"]
    if not os_name:
        return Decision("retain", "unknown-os",
                        ["No operating system reported; identify it before choosing a target."],
                        "low", True)

    eol = next((o for o in rules.get("end_of_life_os", []) if o.lower() in os_name.lower()), None)
    if eol:
        return Decision("replatform", "end-of-life-os",
                        [f"{os_name} is past vendor support; upgrade the OS as part of the move."],
                        "medium", False)

    if any(p.search(vm["vm_name"]) for p in rules["_db"]):
        return Decision("replatform", "database",
                        ["Name suggests a database server; evaluate a managed database service."],
                        "medium", False)

    return Decision("rehost", "default",
                    ["Running, supported OS and no blocking flags; move it as-is."],
                    "high", False)


# ---------- building ----------

def classify(
    inventory_path: Path,
    tags_path: Path | None = None,
    rules_path: Path = DEFAULT_RULES,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Classify every VM in a validated inventory.json."""
    inventory_path = Path(inventory_path)
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        validate_inventory(inventory)
    except (OSError, json.JSONDecodeError, InventoryError) as exc:
        raise ClassifyError(f"Input inventory is not valid: {exc}") from exc

    rules = load_rules(rules_path)
    tags = load_tags(tags_path)
    known = {vm["vm_name"] for vm in inventory["vms"]}
    unknown = sorted(set(tags) - known)
    if unknown:
        raise ClassifyError("Tags refer to VMs not in the inventory: " + ", ".join(unknown))

    records = []
    for vm in inventory["vms"]:
        tag = tags.get(vm["vm_name"], {})
        environment, env_source = infer_environment(vm, tag, rules)
        d = decide(vm, tag, rules)
        records.append({
            "vm_id": vm["vm_id"],
            "vm_name": vm["vm_name"],
            "application": tag.get("application"),
            "environment": environment,
            "environment_source": env_source,
            "criticality": tag.get("criticality") or "unknown",
            "owner": tag.get("owner"),
            "strategy": d.strategy,
            "rule": d.rule,
            "reasons": d.reasons,
            "confidence": d.confidence,
            "needs_review": d.needs_review,
        })

    counts = Counter(r["strategy"] for r in records)
    when = (generated_at or datetime.now(timezone.utc)).replace(microsecond=0)
    return {
        "schema_version": "1.0",
        "generated_at": when.isoformat().replace("+00:00", "Z"),
        "inputs": {
            "inventory": inventory_path.name,
            "tags": Path(tags_path).name if tags_path else None,
        },
        "summary": {
            "total_vms": len(records),
            "by_strategy": {s: counts[s] for s in STRATEGIES if counts[s]},
            "needs_review": sum(r["needs_review"] for r in records),
        },
        "vms": records,
    }


# ---------- validation and output ----------

def validate_classified(data: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA) -> None:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:20]]
        raise ClassifyError("Classified output failed schema validation:\n  " + "\n  ".join(lines))


def write_classified(data: dict[str, Any], output: Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return output
