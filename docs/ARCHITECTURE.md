# Architecture and evidence flow

```text
raw/*.csv + config.json
        |
        v
Diagnosis: inventory, contracts and source hashes
        |
        v
Review ledger --> exact approved overlays (raw never changes)
        |
        v
Integration: normalized records, source keys, customer crosswalk
        |
        v
Validation: amounts, dates, relationships, duplicates, endorsements
        |
        +--> BLOCKED: provisional report + quarantine + correction requests
        |                         |
        |                         +--> optional real model: advisory hypothesis
        |                         |
        |                         +--> named local reviewer --> new ledger event
        |                                                        |
        |                                                        +--> rerun
        |
        +--> APPROVED: published close + product totals

Separate evaluation/ground_truth.json --> demo driver / evaluator only
```

## Modules

| LDM stage | Modules | Boundary |
| --- | --- | --- |
| Diagnosis | `common.py`, `diagnosis.py` | Exact source contracts and inventory |
| Integration | `integration.py`, `review.py` | Preserve original grains; apply authorized overlays |
| AI-Assisted Quality | `ai.py` | Optional external proposal, never a financial decision |
| Validation & Monitoring | `validation.py`, `pipeline.py`, `evaluation.py` | Deterministic release gate and per-run measurements; evaluation oracle remains outside release logic |
| Knowledge Transfer | `reporting.py`, `docs/`, tests | Portable reports, runbook and failure exercises |

## Reproducible runs

A run ID is derived from the source/config manifest, review-ledger head, implementation hashes and software version. Output is built in a staging directory and renamed into place only when complete. The pipeline checks for changed sources/reviews before committing the run.

Replaying the same snapshot reuses the run after verifying its artifact checksums. A new source snapshot ignores approvals attached to the old input hash. A new review creates a new run; older outputs remain inspectable.

The local filesystem is the persistence layer. There is no distributed lock or database transaction spanning external systems. Review writes have a single-writer lock. This is not designed for concurrent production operators.

## Human decisions

The ledger stores exact proposal payload, item hash, input hash, decision, reviewer name, reason, timestamp, simulated flag and previous-event hash. The latest event per item determines current status. Revoking an association recomputes the crosswalk from still-approved relationships; it does not destructively rewrite source identities.

The audit chain detects accidental modifications when its surrounding reference is trusted. Anyone with full write access could rewrite the chain and its hashes. Production requires authenticated identities and externally protected evidence.

## Reporting

All amounts in machine-readable outputs are integer cents. The HTML converts them to currency strings. Blocked runs contain provisional reconciliation only. Product totals are generated solely for approved runs and partitioned by product in BRL.

Monitoring means run status, issue counts, quarantined rows, unresolved identity candidates, applied corrections and measured local runtime. External alerts, scheduling and live observability are not implemented.

## Extension points

Keep validation independent from storage and AI providers. A later Spark adapter should preserve these contracts and pass the same golden scenario tests. Telecom/pharma adapters need their own source grains, rules, access assessment and synthetic references; merely renaming insurance tables would not be sufficient.
