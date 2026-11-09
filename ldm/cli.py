"""CLI: offline by default; every network call requires an explicit assist command."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .common import read_json, write_json
from .evaluation import evaluate
from .pipeline import run
from .reporting import overview
from .review import record
from .synthetic import generate


def print_run(result):
    s = result["summary"]
    print(f"{s['release_status']} | critical={s['critical_count']} | corrections={s['applied_correction_count']} | cached={result['cached']}")
    print(f"Report: {result['run_dir'] / 'report.html'}")


def demo(workspace: Path, seed=42, policies=40):
    generate(workspace, seed, policies)
    before = run(workspace)
    truth = read_json(workspace / "evaluation" / "ground_truth.json")
    requests = read_json(before["run_dir"] / "correction_requests.json")
    for item in requests:
        expected = next((t for t in truth["corrections"] if t["table"] == item["table"] and t["key"] == item["key"] and t["field"] == item["field"]), None)
        if not expected or expected["value"] != item["after"]:
            raise ValueError("Proposed correction does not match synthetic reference")
        record(workspace, before["run_dir"], "correction", item["id"], "approve", "SIMULATED_REVIEWER", "Demonstration only: compared against the synthetic oracle", simulated=True)
    for item in read_json(before["run_dir"] / "entity_candidates.json"):
        expected = next((t for t in truth["entity_matches"] if {t["left"], t["right"]} == {item["left"], item["right"]}), None)
        if not expected:
            raise ValueError("Unexpected identity candidate in demo")
        record(workspace, before["run_dir"], "entity", item["id"], "approve" if expected["same_entity"] else "reject", "SIMULATED_REVIEWER", "Demonstration only: synthetic reference decision", simulated=True)
    after = run(workspace)
    metrics = evaluate(workspace, before["run_dir"], after["run_dir"])
    if before["summary"]["release_status"] != "BLOCKED" or after["summary"]["release_status"] != "APPROVED":
        raise ValueError("Demo did not reach its expected blocked/approved states")
    write_json(workspace / "evaluation" / "metrics.json", metrics)
    overview(workspace / "report.html", before, after, metrics)
    write_json(workspace / "demo_runs.json", {"before": before["summary"]["run_id"], "after": after["summary"]["run_id"], "approvals": "SIMULATED", "ai": "NOT EXECUTED"})
    print("Synthetic demo completed. Review decisions are SIMULATED; AI was NOT executed.")
    print_run(before)
    print_run(after)
    print(f"Overview: {workspace / 'report.html'}")
    return before, after


def parser():
    p = argparse.ArgumentParser(description="LDM insurance laboratory — synthetic data only")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("generate", "demo"):
        s = sub.add_parser(name)
        s.add_argument("--workspace", type=Path, default=Path("workspace"))
        s.add_argument("--seed", type=int, default=42)
        s.add_argument("--policies", type=int, default=40)
    r = sub.add_parser("run")
    r.add_argument("--workspace", type=Path, default=Path("workspace"))
    r.add_argument("--fail-on-blocked", action="store_true", help="Exit 2 when release is blocked")
    rev = sub.add_parser("review")
    rev.add_argument("--workspace", type=Path, default=Path("workspace"))
    rev.add_argument("--run", type=Path, required=True, help="Run directory containing the reviewed evidence")
    rev.add_argument("--kind", choices=["correction", "entity"], required=True)
    rev.add_argument("--id", required=True)
    rev.add_argument("--decision", choices=["approve", "reject", "defer", "revoke"], required=True)
    rev.add_argument("--reviewer", required=True)
    rev.add_argument("--reason", required=True)
    ai = sub.add_parser("assist", help="Explicit optional external API call; never changes validation")
    ai.add_argument("--run", type=Path, required=True)
    ai.add_argument("--provider", choices=["openai"], required=True)
    ai.add_argument("--model", default=os.environ.get("OPENAI_MODEL", ""))
    ai.add_argument("--limit", type=int, default=1)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--workspace", type=Path, default=Path("workspace"))
    ev.add_argument("--before", type=Path, required=True)
    ev.add_argument("--after", type=Path)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "generate":
            print(json.dumps(generate(args.workspace, args.seed, args.policies), indent=2))
        elif args.command == "demo":
            demo(args.workspace, args.seed, args.policies)
        elif args.command == "run":
            result = run(args.workspace)
            print_run(result)
            if args.fail_on_blocked and result["summary"]["release_status"] == "BLOCKED":
                return 2
        elif args.command == "review":
            event = record(args.workspace, args.run, args.kind, args.id, args.decision, args.reviewer, args.reason)
            print(f"Recorded review event {event['event_id']}; rerun the pipeline to materialize its effect.")
        elif args.command == "assist":
            from .ai import investigate
            path, results = investigate(args.run, args.model, args.limit)
            print(path)
            if any(r["status"] == "unavailable" for r in results):
                print("AI unavailable; deterministic results remain unchanged.")
                return 3
            if not results:
                print("No endorsement incidents in this run. No API call was made.")
        elif args.command == "evaluate":
            print(json.dumps(evaluate(args.workspace, args.before, args.after), indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
