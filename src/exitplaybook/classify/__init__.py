"""Stage 2: classify. Assigns a 7R strategy to every VM in an inventory."""

from .engine import ClassifyError, classify, load_tags, validate_classified, write_classified

__all__ = ["ClassifyError", "classify", "load_tags", "validate_classified", "write_classified"]
