# Delivery validation — 2026-11-09

Executed locally on Python 3.14.6. The code targets Python 3.11+; the included GitHub Actions matrix for 3.11/3.12 has not yet run on GitHub.

- **29 automated tests passed** using `python3 -m unittest discover -s tests -v`.
- Default end-to-end demo: **40 policies, 480 installments, 162 payment rows**.
- Initial release **BLOCKED**, with **5 critical inserted scenarios detected**.
- Endorsement evidence: updated premium **144000 cents**, observed schedule **136000 cents**, discrepancy **8000 cents**.
- After **12 simulated correction approvals** and **3 simulated identity decisions**, release **APPROVED**, with **0 critical failures**.
- Corrected P0001 remaining balance: **104000 cents**; eight future installments at **13000 cents** each.
- Replaying the same final snapshot reused the verified run without duplicating payments.
- Raw-source hashes remained unchanged across correction and reprocessing.
- Before/after HTML reports were opened and visually checked in a browser, including incident expansion and navigation.
- Relative documentation links and the macOS launcher shell syntax were checked.

The optional AI adapter was tested with explicit local test transports, including malformed output, wrong policy, unknown evidence, refusal, timeout and HTTP-error paths. **No live model request was made and no API key is included.** Live explanation quality, API latency and real-world detection performance are not claimed.

These results concern the supplied synthetic fixtures only. The automated demo's review decisions are simulated and clearly labeled. No real insurer deployment, regulatory certification or production time saving was measured.

## English-language update (0.1.1)

Reports, interface labels, the quick-start guide, model instructions and model test fixtures are now in English. The optional model is explicitly instructed to respond in English. BRL amounts and business rules are unchanged. The English before/after demo was regenerated, and a report-language regression test was added.
