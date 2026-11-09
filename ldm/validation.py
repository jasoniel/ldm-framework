"""Business validation; money and release decisions never depend on an LLM."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .common import allocate, decimal_money, digest, money
from .synthetic import month_date


def iso(value):
    return date.fromisoformat(value)


def validate(tables, config):
    issues, requests, quarantine, reconciliations, ai_incidents = [], [], [], [], []
    as_of = iso(config["as_of"])

    def issue(rule, entity, message, evidence=None, severity="critical"):
        item = {"id": "ISS-" + digest([rule, entity])[:12], "rule": rule, "entity": entity, "severity": severity, "message": message, "evidence": evidence or {}}
        issues.append(item)
        return item

    def request(table, row, field, after, reason):
        from .common import PRIMARY_KEYS
        item = {"table": table, "key": row[PRIMARY_KEYS[table]], "field": field, "before": "present" if field == "__exclude__" else row[field], "after": str(after), "reason": reason}
        item["id"] = "FIX-" + digest(item)[:12]
        requests.append(item)

    customers = {r["customer_id"] for r in tables["customers"]}
    policies = {r["policy_id"]: r for r in tables["policies"]}
    installments = {r["installment_id"]: r for r in tables["installments"]}
    if not policies:
        issue("EMPTY_POLICIES", "portfolio", "Cannot approve an empty policy portfolio")
    for row in tables["installments"]:
        if row["policy_id"] not in policies:
            issue("ORPHAN_INSTALLMENT", row["installment_id"], "Installment references an unknown policy")
            quarantine.append({"table": "installments", "key": row["installment_id"], "reason": "ORPHAN_INSTALLMENT"})
    for row in tables["endorsements"]:
        if row["policy_id"] not in policies:
            issue("ORPHAN_ENDORSEMENT", row["endorsement_id"], "Endorsement references an unknown policy")

    accepted_payments, deferred_payments = [], []
    references = defaultdict(list)
    for row in tables["payments"]:
        references[row["external_reference"]].append(row)
    duplicated_ids = set()
    for reference, group in references.items():
        if not reference:
            continue
        if len(group) > 1:
            def business_key(row):
                try:
                    amount = money(row["amount"])
                except ValueError:
                    amount = row["amount"]
                return (row["installment_id"], row["paid_on"], amount, row["status"])
            ordered = sorted(group, key=lambda row: row["payment_id"])
            identical = len({business_key(row) for row in ordered}) == 1
            excluded = ordered[1:] if identical else ordered
            for row in excluded:
                duplicated_ids.add(row["payment_id"])
                issue("DUPLICATE_PAYMENT", row["payment_id"], "Repeated external payment reference; excluded from provisional totals pending review", {"external_reference": reference, "identical_business_fields": identical})
                if identical:
                    request("payments", row, "__exclude__", "true", "Review exclusion of repeated receipt; source remains unchanged")
    for row in tables["payments"]:
        key = row["payment_id"]
        if key in duplicated_ids:
            quarantine.append({"table": "payments", "key": key, "reason": "DUPLICATE_PAYMENT"})
            continue
        if row["installment_id"] not in installments:
            issue("ORPHAN_PAYMENT", key, "Payment has no matching installment")
            request("payments", row, "__exclude__", "true", "Investigate unmatched payment; exclusion requires explicit review")
            quarantine.append({"table": "payments", "key": key, "reason": "ORPHAN_PAYMENT"})
            continue
        try:
            amount, paid_on = money(row["amount"]), iso(row["paid_on"])
            if amount < 0 or row["status"] not in {"SETTLED", "PENDING", "VOID"} or not row["external_reference"]:
                raise ValueError("Invalid payment amount, reference or status")
        except ValueError:
            issue("INVALID_PAYMENT", key, "Payment violates the supported input contract")
            quarantine.append({"table": "payments", "key": key, "reason": "INVALID_PAYMENT"})
            continue
        output = {**row, "amount_cents": amount}
        if paid_on > as_of or row["status"] != config["payment_status"]:
            deferred_payments.append(output)
        else:
            accepted_payments.append(output)
    paid_by_installment = defaultdict(int)
    for row in accepted_payments:
        paid_by_installment[row["installment_id"]] += row["amount_cents"]

    standardized_installments = []
    for policy_id, policy in policies.items():
        policy_issue_start = len(issues)
        if policy["customer_id"] not in customers:
            issue("ORPHAN_CUSTOMER", policy_id, "Policy references an unknown customer")
        try:
            premium = money(policy["original_premium"])
            count = int(policy["installments_count"])
            if not 1 <= count <= 120 or premium < 0 or policy["currency"] != config["currency"]:
                raise ValueError("Unsupported premium, installment count or currency")
            if iso(policy["start_date"]).day != 1 or iso(policy["end_date"]) < iso(policy["start_date"]):
                raise ValueError("This demo requires monthly schedules starting on day 1")
        except ValueError:
            issue("INVALID_POLICY", policy_id, "Policy violates supported monthly BRL contract")
            continue
        expected = allocate(premium, count)
        versions = ["v1"] * count
        endorsements = []
        for row in tables["endorsements"]:
            if row["policy_id"] != policy_id:
                continue
            try:
                effective = iso(row["effective_date"])
            except ValueError:
                issue("INVALID_ENDORSEMENT", row["endorsement_id"], "Invalid effective date")
                continue
            if effective <= as_of:
                endorsements.append(row)
        previous_boundary = -1
        invalid_endorsement = False
        for endorsement in sorted(endorsements, key=lambda e: (e["effective_date"], e["endorsement_id"])):
            try:
                boundary = int(endorsement["after_installment"])
                delta = money(endorsement["premium_delta"])
                if endorsement["allocation_rule"] != "equal_remaining" or not 0 <= boundary < count or boundary <= previous_boundary:
                    raise ValueError("Unsupported or unordered endorsement")
                if endorsement["effective_date"] != month_date(policy["start_date"], boundary):
                    raise ValueError("Endorsement must be effective at a schedule boundary")
                expected[boundary:] = allocate(sum(expected[boundary:]) + delta, count - boundary)
                versions[boundary:] = [endorsement["schedule_version"]] * (count - boundary)
                premium += delta
                previous_boundary = boundary
            except ValueError:
                issue("INVALID_ENDORSEMENT", endorsement["endorsement_id"], "Unsupported rule, dates, sequence or negative remaining balance")
                invalid_endorsement = True
        if invalid_endorsement:
            continue
        rows = [r for r in tables["installments"] if r["policy_id"] == policy_id]
        by_number = {}
        for row in rows:
            try:
                number = int(row["number"])
                if number < 1 or number > count or number in by_number:
                    raise ValueError("Duplicate or out-of-range installment number")
                by_number[number] = row
            except ValueError:
                issue("INVALID_SCHEDULE", row["installment_id"], "Duplicate, missing or invalid installment number")
        if set(by_number) != set(range(1, count + 1)):
            issue("INCOMPLETE_SCHEDULE", policy_id, "The complete installment schedule is required")
        actual_total, paid_total, schedule_complete = 0, 0, len(by_number) == count
        mismatches = []
        for number, row in sorted(by_number.items()):
            key = row["installment_id"]
            expected_due = month_date(policy["start_date"], number - 1)
            try:
                if iso(row["due_date"]) != iso(expected_due):
                    raise ValueError("Date differs from the approved monthly schedule")
            except ValueError:
                issue("INVALID_DATE", key, "Invalid installment date", {"actual": row["due_date"], "expected_under_monthly_rule": expected_due})
                request("installments", row, "due_date", expected_due, "Verify monthly schedule date before accepting correction")
            if row["schedule_version"] != versions[number - 1]:
                issue("STALE_SCHEDULE_VERSION", key, "Installment does not reference the expected endorsement version")
            try:
                amount = money(row["amount"])
                if amount < 0:
                    raise ValueError("Negative installment")
            except ValueError:
                issue("MISSING_AMOUNT" if not row["amount"].strip() else "INVALID_AMOUNT", key, "Installment amount is missing or invalid")
                request("installments", row, "amount", decimal_money(expected[number - 1]), "Verify amount against the explicit premium allocation rule")
                quarantine.append({"table": "installments", "key": key, "reason": "INVALID_AMOUNT"})
                schedule_complete = False
                continue
            actual_total += amount
            paid = paid_by_installment[key]
            paid_total += paid
            if paid > amount:
                issue("OVERPAYMENT", key, "Settled payments exceed the scheduled amount", {"scheduled_cents": amount, "paid_cents": paid})
            if amount != expected[number - 1]:
                mismatches.append({"installment_id": key, "number": number, "actual_cents": amount, "expected_cents": expected[number - 1]})
                request("installments", row, "amount", decimal_money(expected[number - 1]), "Review divergence from the approved premium allocation rule")
            standardized_installments.append({**row, "amount_cents": amount, "expected_cents": expected[number - 1], "paid_cents": paid, "remaining_cents": amount - paid})
        if mismatches:
            rule = "ENDORSEMENT_RECONCILIATION" if endorsements else "SCHEDULE_MISMATCH"
            variance = premium - actual_total if schedule_complete else None
            evidence = {"updated_premium_cents": premium, "scheduled_total_cents": actual_total if schedule_complete else None, "variance_cents": variance, "paid_cents": paid_total, "original_installment_count": count, "affected_installments": mismatches, "endorsements": endorsements, "rule": "equal_remaining; exact integer cents; residual to earliest unpaid schedule positions"}
            incident = issue(rule, policy_id, "Scheduled amounts diverge from the versioned business rule", evidence)
            if endorsements:
                ai_incidents.append({"incident_id": incident["id"], "policy_id": policy_id, "evidence": evidence})
        reconciliations.append({"policy_id": policy_id, "product": policy["product"], "customer_id": policy["customer_id"], "currency": policy["currency"], "expected_premium_cents": premium, "scheduled_total_cents": actual_total if schedule_complete else None, "paid_cents": paid_total, "remaining_cents": actual_total - paid_total if schedule_complete else None, "variance_cents": premium - actual_total if schedule_complete else None, "schedule_complete": schedule_complete, "status": "PASS" if len(issues) == policy_issue_start and schedule_complete else "BLOCKED"})
    return {"issues": issues, "correction_requests": requests, "quarantine": quarantine, "reconciliations": reconciliations, "ai_incidents": ai_incidents, "accepted_payments": accepted_payments, "deferred_payments": deferred_payments, "standardized_installments": standardized_installments}
