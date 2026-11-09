# Contributing

1. Describe the business behavior or failure being addressed.
2. Use fictional data only, with a clear expected result.
3. Keep financial release decisions independent from optional model output.
4. Add a meaningful failure or business-invariant test for changed behavior.
5. Run `python3 -m unittest discover -s tests -v` and a fresh `demo`.
6. Update business rules and operational documentation when contracts change.

Preserve original grains and integer-cent arithmetic. Do not make the pipeline read the evaluation oracle. Mark simulations and test model responses explicitly. Do not add unsupported regulatory or production-performance claims.
