# Controls, evidence and regulatory boundaries

This is a technical teaching example, not legal advice, a compliance assessment or a certification.

SUSEP-related insurance obligations, HIPAA applicability and GDPR applicability require separate assessments. Using a common data framework does not make them interchangeable. This repository does not encode a legal requirements register for any organization.

## Demonstrated engineering controls

| Objective | Implemented evidence | Important limit |
| --- | --- | --- |
| Explain transformations | Source keys, input hashes, code hash and rule version | No full production record-level DAG or external source attestation |
| Prevent silent financial changes | Exact proposal plus reviewer event before overlay | Reviewer name is self-declared; no enterprise identity or dual approval |
| Reconcile outputs | Per-installment expected values and per-policy/product totals | One simplified BRL product rule; no tax/pro-rata engine |
| Hold incomplete outputs | Critical issue gate and absence of `published/` on blocked runs | Downstream delivery and acknowledgements are not implemented |
| Support investigation | Quarantine, review snapshots, correction history | Retention and access must be governed outside this local demo |
| Recover and replay | Preserved raw CSVs and deterministic content-addressed snapshots | No distributed transaction across systems or bitemporal source history |
| Bound AI authority | Separate advisory outputs and explicit API invocation | Output validation does not prove factual accuracy |
| Transfer knowledge | Operator runbook, tests and explicit limitations | Staff training must be demonstrated in practice |

## Before any real deployment

An organization would need to establish permitted purpose, applicable obligations, authoritative owners and acceptable evidence. Implementation work would include authenticated access, secrets management, environment separation, protected logs, retention/deletion procedures, tested backup/restore and operational incident handling.

A useful organization-specific register would contain:

```text
obligation_or_policy | scope | affected_data | control_owner |
control_implementation | evidence | review_date | exceptions
```

Do not populate it by assuming that every pharmaceutical dataset is HIPAA-regulated or that an approved technical close proves regulatory compliance. Those determinations belong to the appropriate organizational specialists.

## Claims supported by this repository

- An executable synthetic insurance demonstration with five critical inserted scenarios.
- An R$80 endorsement discrepancy identified by deterministic validation.
- A corrected technical close following explicitly simulated review decisions in `demo`.
- An optional real API adapter with locally tested request/response and failure paths.

The repository does not support claims of production deployment, external adoption, certified compliance, reduced regulatory penalties, real insurer close-time reductions or independently validated AI performance.
