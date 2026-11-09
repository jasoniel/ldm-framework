"""Preserve source grain; add lineage and reviewed customer associations."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from .common import PRIMARY_KEYS, digest


def normalized(value):
    return re.sub(r"[^a-z0-9 ]", "", unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()).strip()


def candidates(customers, threshold=0.70):
    """Transparent heuristic baseline, NOT AI and NOT a probability."""
    blocks = {}
    for customer in customers:
        address = normalized(customer["address"])
        if address:
            blocks.setdefault(address, []).append(customer)
    result = []
    for block in blocks.values():
        block = sorted(block, key=lambda r: r["customer_id"])
        for index, left in enumerate(block):
            for right in block[index + 1:]:
                name_score = SequenceMatcher(None, normalized(left["name"]), normalized(right["name"])).ratio()
                score = round(0.7 * name_score + 0.3, 4)
                if score >= threshold:
                    pair = {"left": left["customer_id"], "right": right["customer_id"]}
                    result.append({"id": "MATCH-" + digest(pair)[:12], **pair, "score": score, "method": "heuristic_name_similarity_shared_address_v1", "is_ai": False, "score_is_probability": False, "evidence": {"left_name": left["name"], "right_name": right["name"], "shared_address": left["address"]}, "permitted_purpose": "synthetic_customer_reporting", "status": "pending"})
    return result


def crosswalk(customers, matching_candidates, latest):
    # Only accepted, still-current, purpose-specific associations affect grouping.
    parent = {r["customer_id"]: r["customer_id"] for r in customers}

    def root(key):
        while parent[key] != key:
            key = parent[key]
        return key

    annotated = []
    for candidate in matching_candidates:
        event = latest.get(("entity", candidate["id"]))
        copy = candidate.copy()
        if event and event["item_hash"] == digest(candidate):
            copy.update(status=event["decision"], reviewer=event["reviewer"], simulated=event["simulated"])
            if event["decision"] == "approve":
                a, b = root(candidate["left"]), root(candidate["right"])
                parent[max(a, b)] = min(a, b)
        annotated.append(copy)
    return [{"source_customer_id": c, "reporting_customer_id": root(c), "purpose": "synthetic_customer_reporting"} for c in parent], annotated


def lineage(tables, input_hash):
    return {name: [{**row, "_source_table": name, "_source_key": row[PRIMARY_KEYS[name]], "_input_hash": input_hash} for row in rows] for name, rows in tables.items()}
