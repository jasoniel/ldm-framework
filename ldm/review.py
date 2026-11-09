"""Local review ledger with integrity checks; no authentication claim."""
from __future__ import annotations

import json
from pathlib import Path

from .common import atomic_text, digest, now, read_json


def ledger(workspace: Path):
    path = workspace / "reviews.jsonl"
    events = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            stored = event.pop("hash")
            if event.get("previous_hash") != (events[-1]["hash"] if events else "GENESIS") or digest(event) != stored:
                raise ValueError("Review ledger integrity check failed")
            events.append({**event, "hash": stored})
    return events


def decisions(workspace: Path, evidence_hash: str):
    latest = {}
    for event in ledger(workspace):
        if event["evidence_hash"] == evidence_hash:
            latest[(event["kind"], event["item_id"])] = event
    return latest


def record(workspace: Path, run_dir: Path, kind: str, item_id: str, decision: str, reviewer: str, reason: str, simulated=False):
    if decision not in {"approve", "reject", "revoke", "defer"}:
        raise ValueError("Unknown decision")
    if kind not in {"correction", "entity"} or not reviewer.strip() or not reason.strip():
        raise ValueError("A kind, named reviewer and reason are required")
    if run_dir.resolve().parent != (workspace / "runs").resolve():
        raise ValueError("Review run must belong to this workspace")
    from .pipeline import verify_artifacts
    verify_artifacts(run_dir)
    evidence = read_json(run_dir / "evidence.json")
    # Reject approvals of stale runs before writing anything.
    from .common import manifest
    if digest(manifest(workspace)) != evidence["input_hash"]:
        raise ValueError("Inputs changed; run diagnosis again before reviewing")
    collection = "correction_requests.json" if kind == "correction" else "entity_candidates.json"
    items = read_json(run_dir / collection)
    item = next((r for r in items if r["id"] == item_id), None)
    if not item:
        raise ValueError(f"Unknown {kind} item: {item_id}")
    evidence_hash = evidence["input_hash"]
    # One writer only: a second process fails cleanly instead of racing.
    lock = workspace / ".review.lock"
    owned_lock = False
    try:
        with lock.open("x"):
            owned_lock = True
            existing = ledger(workspace)
            event = {"event_id": len(existing) + 1, "timestamp": now(), "evidence_hash": evidence_hash, "kind": kind, "item_id": item_id, "item_hash": digest(item), "item": item, "decision": decision, "reviewer": reviewer.strip(), "reason": reason.strip(), "simulated": simulated, "previous_hash": existing[-1]["hash"] if existing else "GENESIS"}
            event["hash"] = digest(event)
            atomic_text(workspace / "reviews.jsonl", "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in [*existing, event]))
    except FileExistsError as exc:
        raise ValueError("Another reviewer is writing; retry when it completes") from exc
    finally:
        # Only remove the lock created by this invocation.
        if owned_lock:
            lock.unlink(missing_ok=True)
    return event


def apply_corrections(tables, latest):
    """Approved overlays only; raw CSVs are never rewritten."""
    from .common import PRIMARY_KEYS
    changes = []
    for (kind, _), event in latest.items():
        if kind != "correction" or event["decision"] != "approve":
            continue
        item = event["item"]
        if digest(item) != event["item_hash"]:
            raise ValueError("Correction payload integrity failure")
        table, key, field = item["table"], item["key"], item["field"]
        rows = tables[table]
        row = next((r for r in rows if r[PRIMARY_KEYS[table]] == key), None)
        if row is None:
            raise ValueError("Approved correction references a missing row")
        if field == "__exclude__":
            rows.remove(row)
        else:
            if row[field] != item["before"]:
                raise ValueError("Conflicting correction: original value does not match")
            row[field] = item["after"]
        changes.append({"review_event_id": event["event_id"], "request_id": item["id"], "table": table, "key": key, "field": field, "before": item["before"], "after": item["after"], "simulated": event["simulated"]})
    return changes
