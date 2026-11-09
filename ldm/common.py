"""Strict data contracts, money, manifests and portable file operations."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

TABLES = {
    "customers": ["customer_id", "name", "address"],
    "policies": ["policy_id", "customer_id", "product", "start_date", "end_date", "original_premium", "installments_count", "currency"],
    "installments": ["installment_id", "policy_id", "number", "due_date", "amount", "schedule_version"],
    "payments": ["payment_id", "installment_id", "external_reference", "paid_on", "amount", "status"],
    "endorsements": ["endorsement_id", "policy_id", "effective_date", "after_installment", "premium_delta", "schedule_version", "allocation_rule"],
}
PRIMARY_KEYS = {t: fields[0] for t, fields in TABLES.items()}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def money(value: str) -> int:
    """Money in integer cents; accept a decimal comma, never silently round."""
    value = str(value).strip()
    if not value or ("," in value and "." in value):
        raise ValueError(f"Invalid monetary value: {value!r}")
    try:
        amount = Decimal(value.replace(",", "."))
        if not amount.is_finite() or amount * 100 != (amount * 100).to_integral_value():
            raise ValueError("Money must be finite and have at most two decimal places")
        return int(amount * 100)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def decimal_money(cents):
    return f"{Decimal(cents) / 100:.2f}"


def allocate(cents: int, count: int) -> list[int]:
    """Exact cent allocation; residual cents go to earliest installments."""
    if count <= 0 or cents < 0:
        raise ValueError("Allocation requires a positive count and non-negative balance")
    base, residual = divmod(cents, count)
    return [base + (i < residual) for i in range(count)]


def atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ldm-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value):
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows, fields=None):
    import io
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else [])
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, stream.getvalue())


def load_tables(workspace: Path):
    result = {}
    for table, fields in TABLES.items():
        path = workspace / "raw" / f"{table}.csv"
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != fields:
                raise ValueError(f"Schema mismatch: {path.name}; expected {fields}")
            rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError(f"Malformed CSV row in {path.name}")
        keys = [r[fields[0]] for r in rows]
        if len(keys) != len(set(keys)) or any(not x for x in keys):
            raise ValueError(f"Missing or duplicated primary keys in {path.name}")
        result[table] = rows
    return result


def manifest(workspace: Path):
    paths = [workspace / "raw" / f"{name}.csv" for name in TABLES]
    paths += [workspace / "config.json"]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
