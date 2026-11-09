"""Seeded fictional data and a separate evaluation oracle (never read by pipeline)."""
from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from .common import TABLES, allocate, decimal_money, write_csv, write_json


def month_date(start: str, offset: int) -> str:
    d = date.fromisoformat(start)
    month = d.year * 12 + d.month - 1 + offset
    return date(month // 12, month % 12 + 1, 1).isoformat()


def generate(workspace: Path, seed=42, policies=40):
    if policies < 5:
        raise ValueError("At least five policies are required for the scenario set")
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError("Workspace is not empty; choose a new directory to preserve existing evidence")
    rng = random.Random(seed)
    workspace.mkdir(parents=True, exist_ok=True)
    data = {table: [] for table in TABLES}
    for i in range(1, policies + 1):
        customer = f"C{i:04d}"
        policy = f"P{i:04d}"
        data["customers"].append({"customer_id": customer, "name": f"Synthetic Customer {i:04d}", "address": f"{i} Fictional Avenue"})
        premium = 120000 if i == 1 else rng.randint(80, 250) * 1200
        data["policies"].append({"policy_id": policy, "customer_id": customer, "product": ["AUTO", "HOME", "LIFE"][i % 3], "start_date": "2026-07-01", "end_date": "2027-06-30", "original_premium": decimal_money(premium), "installments_count": "12", "currency": "BRL"})
        for n, amount in enumerate(allocate(premium, 12), start=1):
            # Deliberately flawed v2: +240/12 instead of +240/8.
            version = "v1"
            if i == 1 and n > 4:
                amount += 2000
                version = "v2"
            installment = f"{policy}-I{n:02d}"
            data["installments"].append({"installment_id": installment, "policy_id": policy, "number": str(n), "due_date": month_date("2026-07-01", n - 1), "amount": decimal_money(amount), "schedule_version": version})
            if n <= 4:
                data["payments"].append({"payment_id": f"PAY-{i:04d}-{n:02d}", "installment_id": installment, "external_reference": f"BANK-{i:04d}-{n:02d}", "paid_on": month_date("2026-07-01", n - 1), "amount": decimal_money(amount), "status": "SETTLED"})
    data["endorsements"].append({"endorsement_id": "END-0001", "policy_id": "P0001", "effective_date": "2026-11-01", "after_installment": "4", "premium_delta": "240.00", "schedule_version": "v2", "allocation_rule": "equal_remaining"})
    # Decimal comma is a legitimate legacy representation, not a defect.
    data["payments"][5]["amount"] = data["payments"][5]["amount"].replace(".", ",")
    original_missing = next(r for r in data["installments"] if r["installment_id"] == "P0002-I07")
    missing_value = original_missing["amount"]
    original_missing["amount"] = ""
    invalid_date = next(r for r in data["installments"] if r["installment_id"] == "P0003-I06")
    correct_date = invalid_date["due_date"]
    invalid_date["due_date"] = "2026-11-31"
    duplicate = next(r for r in data["payments"] if r["payment_id"] == "PAY-0004-01").copy()
    duplicate["payment_id"] = "PAY-DUPLICATE"
    data["payments"].append(duplicate)
    data["payments"].append({"payment_id": "PAY-ORPHAN", "installment_id": "UNKNOWN-I01", "external_reference": "BANK-ORPHAN", "paid_on": "2026-10-01", "amount": "99.00", "status": "SETTLED"})
    data["customers"][0].update(name="Maria Aparecida Example", address="120 Synthetic Street Apt 4")
    data["customers"][1].update(name="Maria Alice Example", address="120 Synthetic Street Apt 4")
    data["customers"] += [{"customer_id": "C-DUP-001", "name": "Maria A. Example", "address": "120 Synthetic Street Apt 4"}]
    # Only exact shared addresses are candidate blocks; no all-customer name matches.
    truth = {
        "notice": "Evaluation oracle only. Demo approvals are simulated, never real human review.",
        "defects": [
            {"rule": "ENDORSEMENT_RECONCILIATION", "entity": "P0001", "expected_variance_cents": 8000},
            {"rule": "MISSING_AMOUNT", "entity": "P0002-I07"},
            {"rule": "INVALID_DATE", "entity": "P0003-I06"},
            {"rule": "DUPLICATE_PAYMENT", "entity": "PAY-DUPLICATE"},
            {"rule": "ORPHAN_PAYMENT", "entity": "PAY-ORPHAN"},
        ],
        "corrections": [
            *[{"table": "installments", "key": f"P0001-I{n:02d}", "field": "amount", "value": "130.00"} for n in range(5, 13)],
            {"table": "installments", "key": "P0002-I07", "field": "amount", "value": missing_value},
            {"table": "installments", "key": "P0003-I06", "field": "due_date", "value": correct_date},
            {"table": "payments", "key": "PAY-DUPLICATE", "field": "__exclude__", "value": "true"},
            {"table": "payments", "key": "PAY-ORPHAN", "field": "__exclude__", "value": "true"},
        ],
        "entity_matches": [{"left": "C0001", "right": "C-DUP-001", "same_entity": True}, {"left": "C0001", "right": "C0002", "same_entity": False}, {"left": "C0002", "right": "C-DUP-001", "same_entity": False}],
    }
    for table, rows in data.items():
        write_csv(workspace / "raw" / f"{table}.csv", rows, TABLES[table])
    write_json(workspace / "config.json", {"dataset_kind": "synthetic", "seed": seed, "as_of": "2026-11-30", "rule_version": "insurance-equal-remaining-v1", "currency": "BRL", "entity_threshold": 0.70, "payment_status": "SETTLED"})
    write_json(workspace / "evaluation" / "ground_truth.json", truth)
    return {"policies": policies, "installments": policies * 12, "payments": len(data["payments"]), "seed": seed}
