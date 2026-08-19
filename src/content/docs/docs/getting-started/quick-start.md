---
title: Quick start
description: From zero to a running VectorStep pipeline — service, gateway, first webhook — in about ten minutes.
sidebar:
  order: 1
---

This guide takes you from nothing to a working pair of services — the **VectorStep
orchestration service** and the **VectorStep Gateway** — with a first pipeline
triggered by a real webhook.

## Prerequisites

- **macOS or Linux** (or **Windows via [WSL2](/docs/installation/windows/)**
  — the commands below are bash scripts, so there's no native Windows path
  yet)
- **Python 3.11+**, `git`
- An LLM provider API key (Anthropic, OpenRouter, Google, Azure OpenAI, or a
  local Ollama — the Gateway supports all of them)
- Nothing else. Local development runs on SQLite with zero infrastructure;
  PostgreSQL is recommended [for production](/docs/operations/deployment/).

## 1. Start the Gateway

The Gateway runs your AI agents: it owns the full agentic loop (LLM calls, MCP
tool execution, multi-turn conversation) and returns one clean result per
request. VectorStep never sees intermediate tool calls — it orchestrates, the
Gateway executes.

```bash
curl -sSL https://raw.githubusercontent.com/bantex01/VectorStep-Gateway/main/install-gateway.sh | bash
```

This clones the Gateway into `~/.vectorstep-gateway/`, creates a virtualenv,
installs dependencies, and copies the config template. Safe to run again
later — it never overwrites an existing `config.yaml` or `agents/`.

```bash
cd ~/.vectorstep-gateway
# Edit config.yaml — set your LLM provider keys and any MCP servers

# Create a first agent
mkdir -p agents/my-agent
# Add agent.yaml and soul.md — see the Gateway docs

export ANTHROPIC_API_KEY=sk-ant-...
source .venv/bin/activate && python -m gateway.main
```

On first run the Gateway generates an identity and an operator token:

```bash
cat ~/.vectorstep-gateway/identity/device-auth.json
# Copy the 'operator' token — VectorStep's config needs it in the next step
```

Both `config.yaml` and `agents/` are gitignored — they hold credentials and
environment-specific agent definitions.

## 2. Start the VectorStep service

```bash
curl -sSL https://raw.githubusercontent.com/bantex01/VectorStep/main/install-service.sh | bash
```

This clones VectorStep into `~/.vectorstep/`, with the venv and config set up
inside `~/.vectorstep/service/` (SQLite by default — no Postgres prompt).
Safe to run again later — it never overwrites an existing `config.yaml`.

```bash
cd ~/.vectorstep/service
# Service config: database, executors (paste the Gateway operator token here),
# notification channels, calibration defaults — edit config.yaml

source .venv/bin/activate && uvicorn src.main:app --reload --port 8000
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

If any of this — the Gateway, agents, MCP tools, confidence gating — is new
to you, **don't jump straight to the reference docs below.** Go to
[**Tutorials**](/docs/tutorials/build-your-first-agent/) next: it builds a
real agent from scratch, wires it to two MCP servers, and then turns on
gating one signal at a time, hands-on. It builds directly on the pipeline
you just triggered.

Once you're comfortable with the mechanics:

- **[How confidence and calibration work](/docs/concepts/confidence/)** — the
  trust vector (S/V/G/D) and every knob that affects it. Read this before
  turning on any enforcement.
- **[Pipeline schema](/docs/pipelines/schema/)** — the full YAML reference:
  verifiers, grounding, parallel groups, fan-out, flow control.
- **[Verifiers](/docs/pipelines/verifiers/)** — adding a second opinion to a
  step, and when to use `critic` vs `independent` mode.
