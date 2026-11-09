# Getting started

## Requirements

Python 3.11+ and a terminal. The standard-library implementation is intended for a small local synthetic portfolio. No cloud subscription is needed.

Check Python and run tests from the project root:

```bash
python3 --version
python3 -m unittest discover -s tests -v
```

## Automated walkthrough

```bash
python3 -m ldm demo --workspace workspace/demo-01 --seed 42 --policies 40
```

Open `workspace/demo-01/report.html` directly in a browser. No web server or build step is needed. The default report has 5 critical scenarios before correction, 12 simulated corrections and zero critical issues afterward. All three identity-review decisions are also simulated.

For another seed choose another folder:

```bash
python3 -m ldm demo --workspace workspace/demo-02 --seed 7 --policies 100
```

## Manual operation

```bash
python3 -m ldm generate --workspace workspace/manual-01
python3 -m ldm run --workspace workspace/manual-01 --fail-on-blocked
```

The blocked exit code **2** is expected. The printed path contains `run-...`; use that real value below.

Inspect:

```bash
python3 -m json.tool workspace/manual-01/runs/RUN_ID/correction_requests.json
python3 -m json.tool workspace/manual-01/runs/RUN_ID/ai_incidents.json
python3 -m json.tool workspace/manual-01/runs/RUN_ID/entity_candidates.json
```

For the endorsement, check updated premium **144000 cents**, paid **40000 cents**, eight expected installments of **13000 cents**, and observed total **136000 cents**. Each of the eight amount changes has a separate request ID.

Approve one checked proposal:

```bash
python3 -m ldm review --workspace workspace/manual-01 \
  --run workspace/manual-01/runs/RUN_ID \
  --kind correction --id FIX_ID --decision approve \
  --reviewer "Accounting reviewer" \
  --reason "Verified the endorsement delta and the remaining installment rule"
```

Approval applies only the exact proposed change, not arbitrary edits. Run again to materialize the overlay. Other unresolved issues still block release.

For an identity candidate, use `--kind entity --id MATCH_ID`. A shared address and similar name are insufficient by themselves to establish identity. Use the synthetic reference only when practicing the laboratory; it would not exist in production. Pending identity candidates do not block this financial close because the close is keyed by policy, not by resolved person.

To reverse a decision, repeat the review command with `--decision revoke` and a reason. Re-run afterward. Previously published runs remain historical outputs, so operational users must explicitly supersede them; the demo does not send downstream recall notifications.

## Optional AI investigation

Use a blocked run containing an endorsement incident. Export `OPENAI_API_KEY` and `OPENAI_MODEL`, then invoke `assist` as shown in the README. The operator selects a model supporting structured outputs. The API request uses a fixed OpenAI HTTPS endpoint and a 45-second timeout; no automatic retry is made, to avoid hidden duplicate charges.

Read the resulting `runs/RUN_ID/ai/investigation-001.json`. An output with status `proposal` still needs human review. Status `unavailable` means there is no usable suggestion; proceed with the deterministic evidence.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Command completed; plain `run` can be blocked, so read its status |
| 1 | Invalid input, missing configuration, or operational failure |
| 2 | `run --fail-on-blocked` detected a blocked close; also used by argparse for invalid CLI syntax |
| 3 | `assist` could not produce a usable model proposal |

## Evaluation

```bash
python3 -m ldm evaluate --workspace workspace/demo-01 \
  --before workspace/demo-01/runs/BEFORE_RUN_ID \
  --after workspace/demo-01/runs/AFTER_RUN_ID
```

`demo_runs.json` supplies the two run IDs. Fixture recall and reviewed identity precision are calculations over the small synthetic reference, not estimates of real-world accuracy.
