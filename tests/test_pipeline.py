import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from ldm.cli import demo, main
from ldm.common import TABLES, allocate, digest, load_tables, manifest, money, read_json, write_csv, write_json
from ldm.evaluation import evaluate
from ldm.integration import candidates, crosswalk
from ldm.pipeline import run
from ldm.review import decisions, ledger, record
from ldm.synthetic import generate
from ldm.validation import validate


class InsuranceWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "lab"
        generate(self.workspace, policies=6)

    def run_quiet_demo(self):
        other = Path(self.temp.name) / "demo"
        with contextlib.redirect_stdout(io.StringIO()):
            before, after = demo(other, policies=6)
        return other, before, after

    def test_endorsement_evidence_and_publication_gate(self):
        result = run(self.workspace)
        self.assertEqual(result["summary"]["critical_count"], 5)
        self.assertFalse((result["run_dir"] / "published").exists())
        incidents = read_json(result["run_dir"] / "ai_incidents.json")
        evidence = incidents[0]["evidence"]
        self.assertEqual(evidence["updated_premium_cents"], 144000)
        self.assertEqual(evidence["paid_cents"], 40000)
        self.assertEqual(evidence["scheduled_total_cents"], 136000)
        self.assertEqual(evidence["variance_cents"], 8000)
        self.assertEqual(len(evidence["affected_installments"]), 8)
        self.assertTrue(all(r["expected_cents"] == 13000 for r in evidence["affected_installments"]))

    def test_full_correction_preserves_sources_and_reconciles(self):
        workspace, before, after = self.run_quiet_demo()
        self.assertEqual(after["summary"]["release_status"], "APPROVED")
        self.assertEqual(after["summary"]["applied_correction_count"], 12)
        self.assertEqual(after["summary"]["input_hash"], before["summary"]["input_hash"])
        self.assertEqual(digest(manifest(workspace)), before["summary"]["input_hash"])
        self.assertTrue((after["run_dir"] / "published" / "accounting_close.csv").exists())
        rows = read_json(after["run_dir"] / "reconciliations.json")
        row = next(r for r in rows if r["policy_id"] == "P0001")
        self.assertEqual(row["remaining_cents"], 104000)
        self.assertEqual(row["variance_cents"], 0)
        metrics = evaluate(workspace, before["run_dir"], after["run_dir"])
        self.assertEqual(metrics["defect_detection"]["detected"], 5)
        self.assertEqual(metrics["defect_detection"]["unexpected"], [])
        self.assertEqual(metrics["matching"]["reviewed_precision"], 1)
        self.assertEqual(metrics["matching"]["reviewed_recall"], 1)

    def test_replay_is_idempotent(self):
        first = run(self.workspace)
        second = run(self.workspace)
        self.assertTrue(second["cached"])
        self.assertEqual(first["run_dir"], second["run_dir"])
        self.assertEqual(first["summary"]["accepted_payment_count"], 24)
        self.assertEqual(len(list((self.workspace / "runs").glob("run-*"))), 1)

    def test_generated_reports_use_english(self):
        workspace, before, after = self.run_quiet_demo()
        reports = [workspace / "report.html", before["run_dir"] / "report.html", after["run_dir"] / "report.html"]
        for report in reports:
            text = report.read_text()
            self.assertIn('lang="en"', text)
            self.assertIn("synthetic", text.lower())
            self.assertIn("review", text.lower())
        self.assertIn("From error to evidence", reports[0].read_text())
        self.assertIn("Reconciliation by policy", reports[1].read_text())
        self.assertIn("Release blocked", reports[1].read_text())
        self.assertIn("Deterministic checks passed", reports[2].read_text())

    def test_revoke_correction_blocks_again(self):
        workspace, before, after = self.run_quiet_demo()
        item = next(x for x in read_json(before["run_dir"] / "correction_requests.json") if x["key"] == "P0001-I05")
        record(workspace, before["run_dir"], "correction", item["id"], "revoke", "test-reviewer", "Incorrect approval revoked")
        repeated = run(workspace)
        self.assertEqual(repeated["summary"]["release_status"], "BLOCKED")
        self.assertFalse((repeated["run_dir"] / "published").exists())
        incident = read_json(repeated["run_dir"] / "ai_incidents.json")[0]
        self.assertEqual(incident["evidence"]["variance_cents"], 1000)
        self.assertTrue((after["run_dir"] / "published" / "accounting_close.csv").exists())

    def test_entity_revoke_removes_crosswalk_association(self):
        workspace, before, after = self.run_quiet_demo()
        item = next(x for x in read_json(before["run_dir"] / "entity_candidates.json") if {x["left"], x["right"]} == {"C0001", "C-DUP-001"})
        record(workspace, before["run_dir"], "entity", item["id"], "revoke", "test-reviewer", "Need further identity evidence")
        repeated = run(workspace)
        tables = load_tables(workspace)
        latest = decisions(workspace, repeated["summary"]["input_hash"])
        rows, _ = crosswalk(tables["customers"], candidates(tables["customers"]), latest)
        mapping = {r["source_customer_id"]: r["reporting_customer_id"] for r in rows}
        self.assertNotEqual(mapping["C0001"], mapping["C-DUP-001"])
        self.assertEqual(repeated["summary"]["release_status"], "APPROVED")

    def test_stale_approval_cannot_apply_to_changed_inputs(self):
        first = run(self.workspace)
        item = read_json(first["run_dir"] / "correction_requests.json")[0]
        record(self.workspace, first["run_dir"], "correction", item["id"], "approve", "reviewer", "Verified")
        tables = load_tables(self.workspace)
        tables["policies"][0]["product"] = "CHANGED"
        write_csv(self.workspace / "raw" / "policies.csv", tables["policies"], TABLES["policies"])
        with self.assertRaisesRegex(ValueError, "Inputs changed"):
            record(self.workspace, first["run_dir"], "correction", item["id"], "approve", "reviewer", "Again")
        repeated = run(self.workspace)
        self.assertEqual(repeated["summary"]["applied_correction_count"], 0)

    def test_corrupt_review_chain_fails_closed(self):
        first = run(self.workspace)
        item = read_json(first["run_dir"] / "correction_requests.json")[0]
        record(self.workspace, first["run_dir"], "correction", item["id"], "approve", "reviewer", "Verified")
        path = self.workspace / "reviews.jsonl"
        event = json.loads(path.read_text())
        event["decision"] = "reject"
        path.write_text(json.dumps(event) + "\n")
        with self.assertRaisesRegex(ValueError, "integrity"):
            run(self.workspace)

    def test_corrupt_run_is_not_silently_reused_or_reviewed(self):
        first = run(self.workspace)
        item = read_json(first["run_dir"] / "correction_requests.json")[0]
        (first["run_dir"] / "report.html").write_text("modified")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            run(self.workspace)
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            record(self.workspace, first["run_dir"], "correction", item["id"], "approve", "reviewer", "Verified")

    def test_pipeline_never_needs_ground_truth(self):
        (self.workspace / "evaluation" / "ground_truth.json").unlink()
        self.assertEqual(run(self.workspace)["summary"]["critical_count"], 5)

    def test_future_receipts_do_not_reduce_current_balance(self):
        tables = load_tables(self.workspace)
        row = copy.deepcopy(tables["payments"][0])
        row.update(payment_id="FUTURE", external_reference="BANK-FUTURE", installment_id="P0005-I05", paid_on="2026-12-01")
        tables["payments"].append(row)
        result = validate(tables, read_json(self.workspace / "config.json"))
        self.assertEqual(len(result["deferred_payments"]), 1)
        self.assertFalse(any(r["payment_id"] == "FUTURE" for r in result["accepted_payments"]))

    def test_conflicting_duplicate_quarantines_both(self):
        tables = load_tables(self.workspace)
        tables["payments"][-2]["amount"] = "999.00"
        result = validate(tables, read_json(self.workspace / "config.json"))
        keys = {r["key"] for r in result["quarantine"]}
        self.assertTrue({"PAY-0004-01", "PAY-DUPLICATE"}.issubset(keys))
        self.assertFalse(any(r["key"] == "PAY-DUPLICATE" for r in result["correction_requests"]))

    def test_empty_portfolio_never_publishes(self):
        result = validate({name: [] for name in TABLES}, read_json(self.workspace / "config.json"))
        self.assertTrue(any(i["rule"] == "EMPTY_POLICIES" for i in result["issues"]))

    def test_offsetting_errors_cannot_hide_behind_matching_total(self):
        tables = load_tables(self.workspace)
        # Two changes cancel at portfolio/policy level but violate the line contract.
        a = next(r for r in tables["installments"] if r["installment_id"] == "P0005-I05")
        b = next(r for r in tables["installments"] if r["installment_id"] == "P0005-I06")
        from ldm.common import decimal_money
        a["amount"] = decimal_money(money(a["amount"]) + 100)
        b["amount"] = decimal_money(money(b["amount"]) - 100)
        result = validate(tables, read_json(self.workspace / "config.json"))
        incident = next(i for i in result["issues"] if i["entity"] == "P0005" and i["rule"] == "SCHEDULE_MISMATCH")
        self.assertEqual(incident["evidence"]["variance_cents"], 0)
        self.assertEqual(len(incident["evidence"]["affected_installments"]), 2)
        self.assertEqual(next(r for r in result["reconciliations"] if r["policy_id"] == "P0005")["status"], "BLOCKED")

    def test_rounding_endorsement_reconciles_to_the_last_cent(self):
        tables = load_tables(self.workspace)
        tables["endorsements"][0]["premium_delta"] = "240.01"
        for row in tables["installments"]:
            if row["policy_id"] == "P0001" and int(row["number"]) > 4:
                row["amount"] = "130.01" if row["number"] == "5" else "130.00"
        result = validate(tables, read_json(self.workspace / "config.json"))
        policy = next(r for r in result["reconciliations"] if r["policy_id"] == "P0001")
        self.assertEqual(policy["variance_cents"], 0)
        self.assertEqual(policy["remaining_cents"], 104001)
        self.assertFalse(any(i["entity"] == "P0001" for i in result["issues"]))

    def test_rejected_or_deferred_correction_never_changes_amounts(self):
        first = run(self.workspace)
        item = next(x for x in read_json(first["run_dir"] / "correction_requests.json") if x["key"] == "P0001-I05")
        for decision in ("reject", "defer"):
            record(self.workspace, first["run_dir"], "correction", item["id"], decision, "reviewer", "Evidence not accepted")
            result = run(self.workspace)
            self.assertEqual(result["summary"]["applied_correction_count"], 0)
            self.assertEqual(read_json(result["run_dir"] / "ai_incidents.json")[0]["evidence"]["variance_cents"], 8000)

    def test_wrong_but_calendar_valid_date_still_blocks(self):
        tables = load_tables(self.workspace)
        row = next(r for r in tables["installments"] if r["installment_id"] == "P0005-I06")
        row["due_date"] = "2026-12-02"
        result = validate(tables, read_json(self.workspace / "config.json"))
        self.assertTrue(any(i["entity"] == "P0005-I06" and i["rule"] == "INVALID_DATE" for i in result["issues"]))

    def test_duplicate_primary_key_rejected(self):
        tables = load_tables(self.workspace)
        tables["policies"].append(tables["policies"][0])
        write_csv(self.workspace / "raw" / "policies.csv", tables["policies"], TABLES["policies"])
        with self.assertRaisesRegex(ValueError, "primary keys"):
            run(self.workspace)

    def test_seed_reproducible_and_generation_never_overwrites(self):
        other = Path(self.temp.name) / "other"
        generate(other, policies=6)
        self.assertEqual(manifest(other), manifest(self.workspace))
        with self.assertRaisesRegex(ValueError, "not empty"):
            generate(self.workspace, policies=6)

    def test_cli_exit_code_distinguishes_blocked_release(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["run", "--workspace", str(self.workspace), "--fail-on-blocked"]), 2)


class MoneyAndBusinessRules(unittest.TestCase):
    def test_exact_cents_and_legacy_comma(self):
        self.assertEqual(money("130,00"), 13000)
        self.assertEqual(money("0.01"), 1)
        for bad in ("NaN", "Infinity", "1.001", "", "1,200.00"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                money(bad)

    def test_rounding_conserves_all_cents(self):
        self.assertEqual(allocate(100, 3), [34, 33, 33])
        self.assertEqual(sum(allocate(104001, 8)), 104001)
        with self.assertRaises(ValueError):
            allocate(-1, 8)


if __name__ == "__main__":
    unittest.main()
