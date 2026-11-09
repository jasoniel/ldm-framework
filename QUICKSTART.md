# Quick start

## Run the demonstration

From the project directory:

```bash
python3 -m ldm demo --workspace workspace/demo-01
```

Requires **Python 3.11 or later**. The local workflow needs no internet, cloud account, API key or third-party Python packages.

Open `workspace/demo-01/report.html` in a browser. On macOS, you can instead double-click `run-demo.command` to generate a new demonstration and open its report.

A ready-to-inspect example is included at [examples/insurance-demo/report.html](examples/insurance-demo/report.html).

## What you will see

The fictional insurance portfolio contains five critical scenarios:

1. An incorrectly allocated endorsement with an **R$80 shortfall**.
2. An installment with a missing amount.
3. An invalid installment date.
4. A duplicate payment.
5. A payment without a matching installment.

There are also similar customer records requiring identity review. Their candidate scores are heuristic, not AI probabilities.

The first run blocks the close. The automated walkthrough then **simulates** approval of 12 corrections and three identity decisions, preserves the original CSVs, and revalidates the result. The second run publishes a technically approved synthetic close.

## Perform reviews yourself

```bash
python3 -m ldm generate --workspace workspace/manual-01
python3 -m ldm run --workspace workspace/manual-01 --fail-on-blocked
python3 -m ldm review --help
```

The run command prints the report directory. Review its correction requests and record your name, decision and reason using `review`. Run the pipeline again to apply approved overlays. Decisions can be rejected, deferred or revoked.

See [Getting started](docs/GETTING_STARTED.md) for complete command examples.

## Optional real AI

The OpenAI adapter can propose an English-language investigation hypothesis for the endorsement incident. It never changes financial values or approves a close.

```bash
export OPENAI_API_KEY="your-local-key"
export OPENAI_MODEL="your-compatible-model-id"
python3 -m ldm assist --run PATH_TO_BLOCKED_RUN --provider openai
```

This is an optional external API call and may incur charges. Credentials are not included. The default demonstration calls no model. API request/response handling was tested with local test transports; a live invocation depends on your key, model access and network.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Understand the scope

This is a synthetic educational implementation, not a production deployment or regulatory certification. Automated demonstration approvals are explicitly simulated. See the [README](README.md), [business rules](docs/BUSINESS_RULES.md) and [operator runbook](docs/RUNBOOK.md).
