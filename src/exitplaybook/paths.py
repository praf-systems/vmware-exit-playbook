"""Locations of repository-level folders (schemas, config).

The package runs from a source checkout (pip install -e .), so these
folders are found relative to this file: src/exitplaybook/ -> repo root.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"
CONFIG_DIR = REPO_ROOT / "config"
