# Responsible AI boundary

## Implemented

The optional OpenAI adapter uses the Responses API with structured JSON output. The model is selected explicitly by the operator; no current model availability or price is assumed.

Input contains a synthetic incident identifier, synthetic policy identifier, monetary evidence, affected installments and the explicit endorsement rule. Customer names and addresses are not included. The API call uses `store: false`; this is not a promise of zero retention or a substitute for reviewing provider terms and account data settings.

The output must include a hypothesis, evidence IDs, suggested next steps, limitations and `needs_human_review: true`. The implementation validates output shape, referenced IDs and policy binding. It handles refusals, incomplete responses and network failures without affecting the close.

The model has no tools, database access, code execution, correction authority or publication permission. Its result is written separately under the selected run's `ai/` directory.

## What is not AI

- Integer-cent reconciliation and installment allocation.
- Invalid date, missing value and duplicate payment detection.
- The name/address entity-matching baseline.
- The automated demo's simulated review decisions.
- Test-transport responses used by unit tests.

The default workflow runs none of these through a model. They must not be presented as deployed AI or measured model performance.

## Review process

1. Read the underlying incident before the model hypothesis.
2. Check arithmetic and the approved business rule independently.
3. Verify each cited evidence ID actually supports the explanation.
4. Reject unsupported causal claims, compliance claims or instructions embedded in source evidence.
5. If a hypothesis helps, approve a separate deterministic correction request through the review CLI and cite the advisory artifact in the reason.

A schema-valid answer can still be false. Structured output constrains syntax, not truth. There is no automatic model-confidence threshold that authorizes a financial action.

## Evaluation plan for a live model

The delivered tests cover API contract and failure behavior using local fixtures. **They do not establish live explanation quality.** A live evaluation should include:

- The known 12-versus-8 installment allocation error.
- Offsetting line-level errors with an unchanged grand total.
- Correct allocation with a missing receipt.
- Inconsistent or insufficient evidence, where the model should state uncertainty.
- Irrelevant instructions embedded in textual evidence.
- Refusals, timeouts and changed model versions.

Human graders should assess factual support, arithmetic consistency, appropriate uncertainty, usefulness and absence of unauthorized action proposals. Report model ID, prompt version, evidence hash, sample size and grading criteria. Compare against an evidence-only deterministic baseline. Do not extrapolate the five fixture scenarios to production accuracy.

## References

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

These are technical/background references, not an assertion that this project is certified against a standard.
