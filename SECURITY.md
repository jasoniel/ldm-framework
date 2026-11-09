# Security and data boundaries

Use only synthetic data in this reference implementation.

The local reports, CSVs and logs have no application-level authentication or encryption. File permissions and environment protection are the operator's responsibility. Names supplied through the review CLI are self-declared. The single-writer lock is local, not a distributed concurrency mechanism.

Source/manifests and ledger hashes help detect accidental changes. A writer who can modify both the artifacts and their references can recompute the hashes. No immutability, non-repudiation or external anchoring is claimed.

HTML report values are escaped. Model output is treated as advisory data, never code. The model has no execution tools. The only network request in the codebase is the explicitly invoked OpenAI adapter, with a fixed HTTPS endpoint, default certificate verification and a timeout.

Never commit `.env`, API keys, real customer data, confidential business rules or production outputs. The `.env.example` file is documentation only and is not loaded automatically. The code does not search for or retrieve credentials.

The synthetic marker in configuration is a workflow declaration, not a data-loss-prevention system. Substituting real records would require a separate access, privacy and provider-processing assessment.

If this project is published, configure a private security-reporting channel before accepting sensitive reports. Do not paste secrets into public issues.
