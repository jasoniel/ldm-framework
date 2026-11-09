"""Separate synthetic oracle evaluation. Never used to release the close."""
from .common import read_json


def evaluate(workspace, before_dir, after_dir=None):
    truth = read_json(workspace / "evaluation" / "ground_truth.json")
    observed = read_json(before_dir / "issues.json")
    expected = {(d["rule"], d["entity"]) for d in truth["defects"]}
    found = {(d["rule"], d["entity"]) for d in observed}
    true_matches = {frozenset((r["left"], r["right"])) for r in truth["entity_matches"] if r["same_entity"]}
    candidates = read_json(before_dir / "entity_candidates.json")
    candidate_pairs = {frozenset((r["left"], r["right"])) for r in candidates}
    result = {"notice": "Small synthetic fixture metrics only; not a production benchmark or evidence of live AI quality.", "defect_detection": {"expected": len(expected), "detected": len(expected & found), "missing": [list(x) for x in sorted(expected - found)], "unexpected": [list(x) for x in sorted(found - expected)], "fixture_recall": len(expected & found) / len(expected) if expected else None}, "matching": {"method": "heuristic baseline + reviewed associations; not AI", "candidate_count": len(candidates), "true_duplicate_pairs": len(true_matches), "candidate_recall": len(true_matches & candidate_pairs) / len(true_matches) if true_matches else None}}
    if after_dir:
        after = read_json(after_dir / "summary.json")
        associations = read_json(after_dir / "entity_decisions.json")
        accepted = {frozenset((r["left"], r["right"])) for r in associations if r["status"] == "approve"}
        result["matching"]["reviewed_precision"] = len(accepted & true_matches) / len(accepted) if accepted else None
        result["matching"]["reviewed_recall"] = len(accepted & true_matches) / len(true_matches) if true_matches else None
        result["after"] = {"release_status": after["release_status"], "critical_count": after["critical_count"], "simulated_review_count": after["simulated_review_count"]}
    return result
