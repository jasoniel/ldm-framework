"""Inventory and deterministic profiling of original source tables."""
from collections import Counter

from .common import TABLES


def profile(tables):
    return [{"table": name, "rows": len(rows), "grain": TABLES[name][0], "columns": TABLES[name], "missing_by_column": dict(Counter(field for row in rows for field, value in row.items() if not value.strip()))} for name, rows in tables.items()]
