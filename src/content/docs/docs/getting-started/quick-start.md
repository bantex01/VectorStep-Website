---
title: Quick start
description: From zero to a running VectorStep pipeline — service, gateway, first webhook — in about ten minutes.
sidebar:
  order: 1
---

This guide takes you from nothing to a working pair of services, with a
first pipeline triggered by a real webhook. **VectorStep** orchestrates: it
receives webhooks, resolves the matching pipeline, and gates each step's
result before continuing. **The Gateway** executes: it owns the full
agentic loop for a step (LLM calls, MCP tool execution, multi-turn
conversation) and hands VectorStep back one clean result — never the
intermediate tool calls. Start the Gateway first, since VectorStep calls
out to it.

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

```bash
curl -sSL https://raw.githubusercontent.com/bantex01/VectorStep-Gateway/main/install-gateway.sh | bash
```

This clones the Gateway into `~/.vectorstep-gateway/`, creates a virtualenv,
installs dependencies, and copies the config template. Safe to run again
later — it never overwrites an existing `config.yaml` or `agents/`.

```bash
cd ~/.vectorstep-gateway
# Edit config.yaml — set your LLM provider keys and any MCP servers
```

For a first agent, copy the bundled sample rather than writing one from
scratch — it needs no MCP tools, just a model, so it runs with nothing more
than an API key. Once you're past this guide, [Tutorials](/docs/tutorials/build-your-first-agent/)
walks through writing a real one.

```bash
cp -r samples/agents/generic-pipeline-step agents/my-agent
```

The sample agent defaults to an Anthropic model, which is why that's the
key exported below. The Gateway also supports OpenRouter, Google, Azure
OpenAI, and Ollama — see [Providers](/docs/gateway/providers/) for every
model string format.

```bash
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

Pipelines are YAML files in `service/pipelines/`; reusable steps live in
`service/steps/`. Create both of these — a complete pipeline built for the
agent you just made, with no MCP tools required, since
`generic-pipeline-step` reasons from the alert payload alone. (The samples
bundled in `samples/pipelines/` and `samples/steps/` are real production
examples wired to OpenClaw and external tools like Jira and Confluence —
worth exploring later, but not a fit for this walkthrough.)

`steps/first-line-triage.yaml`:

```yaml
name: first-line-triage
description: First-line triage for a critical alert — no MCP tools required.
executor: gateway
executor_config:
  agent: my-agent
  session_key: "agent:my-agent:{{pipeline_run_id}}:{{current_step}}"
confidence_threshold: 0.60
on_low_confidence: escalate
prompt_template: |
  A {{severity}} alert fired for {{labels.service}} in {{labels.environment}}.
  Summary: {{summary}}

  Summarise what's happening. Set confidence based on how clearly the alert
  data explains the problem — not on how serious it is.

  Return JSON only, no other text:
  {
    "confidence": 0.0,
    "summary": "One sentence: what's happening and how serious",
    "next_step_context": "Focused brief for whatever handles this next",
    "reasoning": {
      "supports": "Evidence that makes this alert credible",
      "contradicts": "Evidence that suggests noise or a false positive",
      "assumptions": "What you're assuming in the absence of data"
    }
  }
```

`pipelines/alert-triage.yaml`:

```yaml
name: alert-triage
description: First-line triage for critical alerts
trigger:
  match: { source: alertmanager, severity: critical }

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
curl -X POST "http://localhost:8000/webhook?source=alertmanager&allow_testing=true" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/alertmanager_critical.json
# → {"status": "accepted", "run_id": "<uuid>"}
```

New pipelines default to `stage: testing` — fully executable, but inert to
real ingestion traffic until you deliberately opt in with
`allow_testing=true` (or promote the pipeline itself to `stage: production`
later). See [Pipeline stages](/docs/concepts/stages/) for what each stage
actually gates.

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
