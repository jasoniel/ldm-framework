# Supported insurance rules

These rules define a fictional educational product. They are not a statement of Caixa/Youse policy or regulatory requirements.

## Money and schedules

- Currency: BRL, stored as integer cents after strict decimal parsing.
- Input decimals may use `.` or `,`, without thousands separators.
- More than two decimal places, non-finite values and unsupported negative payment amounts are rejected.
- Monthly installments begin on the first day of a month, with consecutive numbers `1..N`.
- A complete schedule is required. A valid but contractually wrong due date also fails.
- Original premium is divided exactly; residual cents go to the earliest schedule positions.
- No interest, commissions, IOF, other taxes, pro-rata, refunds, cancellations or chargebacks are modeled.

## Endorsements

Only `equal_remaining` is supported. An endorsement must occur at a monthly schedule boundary and identify the last installment before that boundary. The effective date must not be later than the configured close date to affect the current calculation.

The rule freezes earlier contractual amounts and reallocates the remaining scheduled premium plus the endorsement delta across later schedule positions. A negative delta is allowed only if the resulting remaining premium is non-negative. Multiple endorsements must have strictly increasing boundaries; simultaneous, retroactive or same-boundary endorsements require a separate design and fail closed here.

The boundary is a contractual schedule boundary, not a claim that all preceding installments have actually been paid. Overdue unpaid amounts remain in the close balance. The featured scenario happens to have the first four installments paid in full.

### Featured incident

```text
Original premium                         120000 cents (R$1,200)
First four installments                   40000 cents (R$400)
Original remaining schedule               80000 cents (R$800)
Endorsement delta                         24000 cents (R$240)
New remaining schedule                   104000 cents (R$1,040)
Eight correct installments                13000 cents each
Eight flawed source installments          12000 cents each
Observed complete schedule               136000 cents
Updated premium                          144000 cents
Detected shortfall                         8000 cents (R$80)
```

The validation checks each installment, the schedule version, and the total. Offsetting errors cannot pass merely because their grand total is zero.

## Payments and close

- Payment primary keys must be unique.
- Bank `external_reference` is assumed globally unique within this synthetic ledger.
- Exact repeated business events are not double counted; a review request remains blocking until resolved.
- Conflicting repeated references quarantine every affected payment and require investigation; no automatic exclusion proposal is supplied.
- Only `SETTLED` payments on or before `as_of` reduce the balance. `PENDING`, `VOID`, and future payments are deferred.
- An unknown status, invalid amount/date/reference, orphan relationship, overpayment, missing schedule or unsupported policy blocks publication.
- Remaining balance is scheduled amounts minus accepted payments, including overdue amounts.
- A partial/incomplete schedule has `null` totals rather than a deceptively valid zero.
- Global critical issues block the entire portfolio, even if individual policy checks pass.

## Review and identity

Correction proposals do not change source CSVs. Exact approved overlays apply on the next run. Proposed exclusions are not evidence that real money can be discarded; a real operator must resolve the business event and downstream implications.

Entity matching uses a shared-address block plus name similarity, not AI. A score is a ranking heuristic, not a calibrated probability. A positive decision creates a reversible association for `synthetic_customer_reporting`; it does not alter policy/payment grain or authorize account access. This financial close can pass while identity candidates remain pending.

## Point-in-time limits

The generator supplies a current schedule and one close snapshot. It does not retain a full bitemporal contract history. Trying to reconstruct an earlier close from a future-version schedule will fail validation instead of silently assuming the schedule is historically correct. Production historical replay requires versioned source snapshots and approved effective-time semantics.
