---
title: Quick start
description: From zero to a running P-Ork pipeline — service, gateway, first webhook — in about ten minutes.
sidebar:
  order: 1
---

This guide takes you from nothing to a working pair of services — the **P-Ork
orchestration service** and the **P-Ork Gateway** — with a first pipeline
triggered by a real webhook.

## Prerequisites

- **Python 3.11+**
- An LLM provider API key (Anthropic, OpenRouter, Google, Azure OpenAI, or a
  local Ollama — the Gateway supports all of them)
- Nothing else. Local development runs on SQLite with zero infrastructure;
  PostgreSQL is recommended [for production](/docs/operations/deployment/).

## 1. Start the Gateway

The Gateway runs your AI agents: it owns the full agentic loop (LLM calls, MCP
tool execution, multi-turn conversation) and returns one clean result per
request. P-Ork never sees intermediate tool calls — it orchestrates, the
Gateway executes.

```bash
git clone <your-fork>/P-Ork-Gateway && cd P-Ork-Gateway
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Config template documents every option
cp samples/config.yaml.example config.yaml
# Edit config.yaml — set your LLM provider keys and any MCP servers

# Create a first agent
mkdir -p agents/my-agent
# Add agent.yaml and soul.md — see the Gateway docs

export ANTHROPIC_API_KEY=sk-ant-...
python -m gateway.main
```

On first run the Gateway generates an identity and an operator token:

```bash
cat ~/.pork-gateway/identity/device-auth.json
# Copy the 'operator' token — P-Ork's config needs it in the next step
```

Both `config.yaml` and `agents/` are gitignored — they hold credentials and
environment-specific agent definitions.

## 2. Start the P-Ork service

```bash
git clone <your-fork>/P-Ork && cd P-Ork/service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Service config: database, executors (paste the Gateway operator token here),
# notification channels, calibration defaults
cp ../samples/config.yaml.example config.yaml

uvicorn src.main:app --reload --port 8000
```

## 3. Add a pipeline

Pipelines are YAML files in `service/pipelines/`. Copy a sample to start:

```bash
cp ../samples/pipelines/otel-triage-verified.yaml pipelines/
cp ../samples/steps/first-line-triage.yaml steps/
```

A minimal pipeline looks like this:

```yaml
name: alert-triage
description: First-line triage for critical alerts
trigger:
  source: alertmanager
  match: { severity: critical }

steps:
  - name: triage
    use: first-line-triage        # reusable step from your step library
    executor: gateway
    executor_config:
      agent: my-agent
    confidence_threshold: 0.75
    on_low_confidence: escalate   # below the bar, a human sees it instead
```

Reload without restarting:

```bash
curl -X POST http://localhost:8000/reload
# → {"status": "reloaded", "pipelines_loaded": 1}
```

## 4. Trigger it

Send a test webhook using one of the bundled fixtures:

```bash
curl -X POST "http://localhost:8000/webhook?source=alertmanager" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/alertmanager_critical.json
# → {"status": "accepted", "run_id": "<uuid>"}
```

## 5. Watch it run

Open **http://localhost:8000/ui/** — the dashboard shows the run live. Click
into it for the full run log: every step's prompt, output, confidence score,
and the Trust panel explaining exactly how each gating decision was made.

You can also live-tail from the run detail page, or query the API directly:

```bash
curl http://localhost:8000/runs           # newest first
curl http://localhost:8000/runs/<run_id>  # full detail with per-step confidence
```

## Where next

- **[How confidence and calibration work](/docs/concepts/confidence/)** — the
  trust vector (S/V/G/D) and every knob that affects it. Read this before
  turning on any enforcement.
- **[Pipeline schema](/docs/pipelines/schema/)** — the full YAML reference:
  verifiers, grounding, parallel groups, fan-out, flow control.
- **[Verifiers](/docs/pipelines/verifiers/)** — adding a second opinion to a
  step, and when to use `critic` vs `independent` mode.
