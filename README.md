# LDM Framework — Insurance Modernization Lab

An executable reference implementation of **Diagnosis → Integration → AI-Assisted Quality → Validation → Knowledge Transfer**, using a completely fictional insurance portfolio.

**Version 0.1.1 · Python 3.11+ · offline core · no third-party runtime dependencies.**

[Quick start](QUICKSTART.md) · [Getting started](docs/GETTING_STARTED.md) · [Architecture](docs/ARCHITECTURE.md) · [Runbook](docs/RUNBOOK.md) · [Business rules](docs/BUSINESS_RULES.md) · [Responsible AI](docs/RESPONSIBLE_AI.md)

## Run the complete demonstration

From this project's directory:

```bash
python3 -m ldm demo --workspace workspace/demo-01
```

Open `workspace/demo-01/report.html` in a browser. It links to separate **before** and **after** reports. Use a new workspace name to run another demo; generation never overwrites existing evidence.

On macOS you can also double-click `run-demo.command`. A pre-generated, inspectable example is included at [examples/insurance-demo/report.html](examples/insurance-demo/report.html).

Optional editable installation: `python3 -m pip install -e .` makes the `ldm` command available. Installation is not required for the commands above.

## The business scenario

The fictional insurer consolidates customers, policies, installments, payments and endorsements for a monthly accounting close. The default portfolio contains **40 policies, 480 installment rows, 162 payment rows and one endorsement**, plus synthetic customer variants.

| Inserted scenario | What the pipeline demonstrates |
| --- | --- |
| Incorrect endorsement allocation | Original premium R$1,200; four R$100 installments paid; +R$240 endorsement; eight future installments incorrectly set to R$120 instead of R$130. The deterministic rule detects an R$80 shortfall. |
| Missing installment amount | Quarantine the incomplete record, block release and propose a reviewed correction under the explicit allocation rule. |
| Invalid installment date | Detect an impossible date and propose the monthly contractual date for review. |
| Repeated payment | Detect a repeated bank reference; avoid double counting; require review of exclusion. Conflicting duplicates quarantine both records. |
| Payment without an installment | Quarantine and block release; exclusion is a review decision, not an automatic claim that the payment is invalid. |
| Similar customer identities | Generate heuristic candidate pairs; approve, reject, defer or revoke a purpose-specific association. Never silently merge source records. |

Amounts use exact integer cents. The example's allocation rule excludes interest, tax, pro-rata and refunds. It does **not** represent every insurance product or an insurer's actual accounting policy.

## What happens when `demo` runs

1. Generate reproducible fictional sources and an independent evaluation reference.
2. Profile and integrate the sources, record lineage and validate business rules.
3. Produce a **BLOCKED** result with five critical scenarios. No published close exists.
4. Use the evaluation reference to **simulate** 12 approved corrections and three identity-review decisions.
5. Reprocess the original sources plus reviewed overlays into an **APPROVED** technical result.
6. Publish the corrected close, product totals, before/after reports and fixture evaluation.

**Demo decisions are explicitly SIMULATED.** The command is a reproducible demonstration, not evidence of real human review. The pipeline never reads the evaluation reference; only the demo driver and evaluator do.

## Operate the human-review workflow

```bash
python3 -m ldm generate --workspace workspace/manual-01 --seed 42 --policies 40
python3 -m ldm run --workspace workspace/manual-01 --fail-on-blocked
```

The second command intentionally exits **2** while blocked. Read the printed report path and its neighboring `correction_requests.json` / `entity_candidates.json`. Review a specific proposal:

```bash
python3 -m ldm review \
  --workspace workspace/manual-01 \
  --run workspace/manual-01/runs/RUN_ID \
  --kind correction --id FIX_ID --decision approve \
  --reviewer "Your name" \
  --reason "Checked the endorsement and equal_remaining rule against source evidence"

python3 -m ldm run --workspace workspace/manual-01 --fail-on-blocked
```

Replace `RUN_ID` and `FIX_ID` with actual values. Review each proposal separately. `--kind entity` reviews identity candidates. `--decision revoke` reverses an approval on the next run; old outputs remain historical snapshots. `reject` and `defer` do not correct financial data.

## Real AI, explicitly optional

The default demo makes **no network calls** and does not claim to execute AI. Entity candidate generation is a documented heuristic baseline, not machine learning.

An optional OpenAI Responses API adapter produces **structured, advisory hypotheses** for endorsement incidents. It sends only incident evidence, numeric amounts, synthetic IDs and the explicit allocation rule—not customer names or addresses. It requires an API key and an explicitly selected model that supports structured outputs.

```bash
export OPENAI_API_KEY="your-local-key"
export OPENAI_MODEL="your-compatible-model-id"

python3 -m ldm assist \
  --run workspace/manual-01/runs/BLOCKED_RUN_ID \
  --provider openai --limit 1
```

The model and key are read from environment variables. Do not put the key in source files. `assist` is an explicit external API invocation and can incur API charges. It writes a separate file under `ai/`; it never changes the close, financial checks or review decisions. A human reviews the hypothesis and, if justified, separately approves a deterministic correction request. Reference the advisory artifact in the review reason if it informed the investigation.

Failures, refusals, malformed outputs and unsupported models do not disable validation. A schema-valid explanation can still be wrong: reviewers must check the evidence. See [Responsible AI](docs/RESPONSIBLE_AI.md).

## Outputs and evidence

Every content-addressed run includes:

- `report.html`, `summary.json`, `source_inventory.json`;
- `issues.json`, `quarantine.json`, `correction_requests.json`;
- `reconciliation.csv`, `normalized_installments.csv`, `accepted_payments.csv`;
- `customer_crosswalk.csv`, `entity_candidates.json`, `entity_decisions.json`;
- `evidence.json`, `lineage.json`, `review_snapshot.json`, `applied_corrections.json`;
- `artifact_manifest.json`, with checksums for run artifacts;
- `published/accounting_close.csv` and `published/product_totals.csv` **only when all critical checks pass**.

The run ID binds input hashes, code hashes and the review-ledger head. Repeating unchanged input and reviews reuses a verified run, without duplicating payments. Altered input invalidates old approvals. All original CSVs remain unchanged.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests exercise money conservation, the R$80 incident, release blocking, review revocation, stale approvals, reprocessing, duplicate conflicts, source preservation, point-in-time payment filtering, corrupted evidence, and AI failure/refusal paths. API behavior is tested with local test transports; no live API quality or latency result is claimed.

GitHub Actions runs the same checks and an end-to-end demo on Python 3.11 and 3.12.

## Scope and limitations

This repository is an educational insurance example inspired by general engineering experience. It contains **no Caixa/Youse source code, customer data, production architecture or verified company performance figures**.

It is not a regulatory certification or a production platform. Review identities are self-declared; local hash chains are not externally anchored; the application does not implement enterprise IAM, immutable retention, a database, distributed processing or scheduled alert delivery. Changed code/configuration creates a new run; these controls do not replace change management.

Telecom/pharma implementations and a PySpark/Databricks adapter are future extensions, not shipped modules. See [Roadmap](docs/ROADMAP.md), [control boundaries](docs/CONTROLS.md) and [security considerations](SECURITY.md).

## Technical references

- [OpenAI: Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) — API integration contract; model access must be checked in the operator's account.
- [Python: decimal](https://docs.python.org/3/library/decimal.html) — decimal parsing before conversion to integer cents.
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — background reading, not a certification of this implementation.

Licensed under MIT. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
