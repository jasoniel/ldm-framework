# Operator runbook

## Before processing

1. Confirm you are using only the supplied synthetic format and understand the business rule in `BUSINESS_RULES.md`.
2. Choose a new workspace for generation. Keep raw sources and prior runs.
3. Run the automated tests after changing code.

## Blocked close

Read `summary.json`, then `issues.json` and `quarantine.json`. Never hand the provisional `reconciliation.csv` to consumers as an approved close. Only files under a run's `published/` directory passed the technical release gate.

| Incident | Investigation |
| --- | --- |
| Endorsement mismatch | Compare delta, effective boundary, previous premium, individual expected amounts, schedule version and total. Confirm the rule before reviewing each correction. |
| Missing amount | Establish the contractual amount from appropriate evidence. The proposed allocation is not proof by itself. |
| Invalid date | Check the source and expected monthly schedule. If the real product has another schedule rule, change the rule deliberately instead of approving an inappropriate value. |
| Duplicate receipt | Compare bank reference and business fields. Identical receipts can be reviewed for exclusion; conflicting ones require investigation of both. |
| Orphan receipt | Find the missing installment or establish the appropriate treatment. The demo's exclusion represents a reviewed synthetic fixture, not a blanket write-off policy. |
| Unknown relationship or incomplete schedule | Correct the input through an approved source process. There is no generic auto-fix command. A changed input creates a new evidence snapshot. |

Use `review` with a name and reason, then re-run. Financial exceptions remain blocking when a correction is rejected or deferred.

## Optional AI unavailable

The default workflow does not require AI. If `assist` returns code 3, inspect model compatibility, credentials, network and quota. No model proposal should be treated as a successful investigation when its status is `unavailable`.

Do not disable deterministic rules, raise tolerances or invent an AI response to work around an API failure. Investigate using the evidence package. The adapter makes no automatic retries.

## Correction or association needs reversal

Record a `revoke` decision for the original item and run again. Verify the new applied-corrections list/crosswalk. Old run files remain historical snapshots. If an output was already used elsewhere, an external correction/supersession procedure is needed; this local lab does not implement distribution or recall.

## Evidence or ledger check fails

Stop using the altered run. Preserve a copy for investigation and compare with trusted backups/source controls. Local hashes cannot distinguish a legitimate administrator from an attacker who can rewrite both data and manifests.

Do not delete evidence or rewrite hash values merely to make a test pass. If a process crashed while writing a review, confirm no reviewer process is active before removing a stale `.review.lock` file and retrying.

## Reprocessing

Run `python3 -m ldm run --workspace ...`. Unchanged inputs/review decisions reuse a verified run. Changed input hashes invalidate all approvals for the previous snapshot. Review the new proposals; do not copy approvals blindly.

## Knowledge-transfer exercise

A second engineer should be able to:

1. Generate and diagnose the synthetic dataset without consulting the original author.
2. Explain why the endorsement has an R$80 difference.
3. Find a payment exclusion and trace it to a review event.
4. Approve one correction and confirm that unrelated failures still block publication.
5. Revoke the correction and observe its effect in a new run.
6. Explain which identity scores are heuristic and where optional AI is involved.
7. Locate source hashes, code hash, rule version and the published output.

Record exercise findings as improvement work; documentation alone does not demonstrate operational proficiency.
