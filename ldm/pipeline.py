"""Five-stage orchestration, content-addressed runs and release gate."""
from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from . import __version__
from .common import digest, load_tables, manifest, now, read_json, write_csv, write_json
from .diagnosis import profile
from .integration import candidates, crosswalk, lineage
from .reporting import render_report
from .review import apply_corrections, decisions, ledger
from .validation import validate


def code_hash():
    return digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))})


def verify_artifacts(run_dir):
    integrity = read_json(run_dir / "artifact_manifest.json")
    for name, expected in integrity.items():
        file = run_dir / name
        if file.resolve().parent != run_dir.resolve() and run_dir.resolve() not in file.resolve().parents:
            raise ValueError("Invalid artifact manifest path")
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Existing run artifact changed: {name}; preserve it and investigate")


def run(workspace: Path):
    started = time.perf_counter()
    config = read_json(workspace / "config.json")
    if config.get("dataset_kind") != "synthetic":
        raise ValueError("Only synthetic workspaces are supported by this reference implementation")
    if config.get("rule_version") != "insurance-equal-remaining-v1" or config.get("payment_status") != "SETTLED":
        raise ValueError("Unsupported business rule configuration")
    sources = manifest(workspace)
    input_hash = digest(sources)
    tables = load_tables(workspace)
    if manifest(workspace) != sources:
        raise ValueError("Inputs changed during ingestion; retry against a stable snapshot")
    review_events = ledger(workspace)
    review_head = review_events[-1]["hash"] if review_events else "GENESIS"
    implementation = code_hash()
    run_id = "run-" + digest([input_hash, review_head, implementation, __version__])[:16]
    target = workspace / "runs" / run_id
    if target.exists():
        verify_artifacts(target)
        return {"run_dir": target, "summary": read_json(target / "summary.json"), "cached": True}
    profiles = profile(tables)
    latest = decisions(workspace, input_hash)
    matching = candidates(tables["customers"], config["entity_threshold"])
    crosswalk_rows, annotated = crosswalk(tables["customers"], matching, latest)
    changes = apply_corrections(tables, latest)
    result = validate(tables, config)
    critical = sum(i["severity"] == "critical" for i in result["issues"])
    approved = critical == 0
    summary = {"run_id": run_id, "created_at": now(), "software_version": __version__, "code_hash": implementation, "rule_version": config["rule_version"], "as_of": config["as_of"], "dataset_kind": "synthetic", "release_status": "APPROVED" if approved else "BLOCKED", "critical_count": critical, "policy_count": len(tables["policies"]), "raw_row_count": sum(p["rows"] for p in profiles), "accepted_payment_count": len(result["accepted_payments"]), "deferred_payment_count": len(result["deferred_payments"]), "quarantined_row_count": len(result["quarantine"]), "applied_correction_count": len(changes), "pending_entity_candidates": sum(c["status"] in {"pending", "defer", "revoke"} for c in annotated), "simulated_review_count": sum(e["simulated"] for e in latest.values()), "ai_status": "not_requested", "elapsed_seconds": round(time.perf_counter() - started, 6), "input_hash": input_hash, "review_head": review_head}
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=target.parent))
    try:
        write_json(staging / "summary.json", summary)
        write_json(staging / "evidence.json", {"dataset_kind": "synthetic", "input_hash": input_hash, "sources": sources, "code_hash": implementation, "rule_version": config["rule_version"], "as_of": config["as_of"], "review_head": review_head, "notice": "Local hashes support reproducibility; they are not tamper-proof external attestation."})
        write_json(staging / "source_inventory.json", profiles)
        write_json(staging / "review_snapshot.json", review_events)
        write_json(staging / "entity_candidates.json", matching)
        write_json(staging / "entity_decisions.json", annotated)
        write_json(staging / "applied_corrections.json", changes)
        write_csv(staging / "customer_crosswalk.csv", crosswalk_rows)
        for name in ("issues", "correction_requests", "quarantine", "reconciliations", "ai_incidents"):
            write_json(staging / f"{name}.json", result[name])
        write_csv(staging / "reconciliation.csv", result["reconciliations"])
        write_csv(staging / "normalized_installments.csv", result["standardized_installments"])
        write_csv(staging / "accepted_payments.csv", result["accepted_payments"])
        write_json(staging / "lineage.json", lineage(tables, input_hash))
        # A blocked run never contains an official close file, including on replay.
        if approved:
            write_csv(staging / "published" / "accounting_close.csv", result["reconciliations"])
            totals = defaultdict(lambda: {"expected_premium_cents": 0, "paid_cents": 0, "remaining_cents": 0})
            for row in result["reconciliations"]:
                for field in ("expected_premium_cents", "paid_cents", "remaining_cents"):
                    totals[row["product"]][field] += row[field]
            write_csv(staging / "published" / "product_totals.csv", [{"product": product, **amounts} for product, amounts in sorted(totals.items())])
        render_report(staging / "report.html", summary, profiles, result, annotated, changes)
        hashes = {str(p.relative_to(staging)): hashlib.sha256(p.read_bytes()).hexdigest() for p in staging.rglob("*") if p.is_file()}
        write_json(staging / "artifact_manifest.json", hashes)
        current_reviews = ledger(workspace)
        current_head = current_reviews[-1]["hash"] if current_reviews else "GENESIS"
        if manifest(workspace) != sources or current_head != review_head:
            raise ValueError("Sources or review decisions changed during processing; rerun against a stable snapshot")
        try:
            staging.rename(target)
        except OSError:
            if not target.exists():
                raise
            # Concurrent equal runs: discard staging and verify the winner on retry.
            shutil.rmtree(staging)
            return run(workspace)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"run_dir": target, "summary": summary, "cached": False}
